#!/usr/bin/env bash
# =============================================================================
# provision-kv.sh — Idempotent KV Bucket Provisioning and Reconciliation
# =============================================================================
# Reads KV bucket definitions from kv/kv-definitions.json — the ONLY source of
# truth for KV buckets (streams/provision-streams.sh does not touch them) — and
# makes the live buckets match:
#
#   - Missing bucket          → [CREATE]  nats kv add with every defined setting
#   - Bucket matches          → [OK]      nothing changed
#   - Editable setting differs → [UPDATE] nats kv edit (history, max value size,
#                                          TTL, replicas), then re-read to confirm
#   - Storage type differs    → [REFUSED] by default: storage cannot be edited,
#                                          only changed by deleting and recreating
#                                          the bucket, which loses its values.
#                                          --recreate <bucket> allows exactly that
#                                          bucket to be deleted and recreated.
#
# Live settings are read with `nats stream info KV_<bucket> --json` (the
# installed nats CLI has no `nats kv info --json`). A response with a missing
# or invalid setting is an [ERROR] for that bucket and nothing is changed —
# not even with --recreate. TTL is compared in exact nanoseconds.
#
# Safe to run multiple times: on first deploy, on reboot, and after definition changes.
#
# Environment variables:
#   NATS_URL    — NATS server URL (default: nats://localhost:4222)
#   NATS_CREDS  — Path to NATS credentials file (optional)
#   NATS_USER / NATS_PASSWORD — read by the nats CLI itself from the
#                 environment (optional); never put credentials in NATS_URL
#
# Usage:
#   ./kv/provision-kv.sh                              # Reconcile all KV buckets
#   ./kv/provision-kv.sh --dry-run                    # Print planned changes only
#   ./kv/provision-kv.sh --recreate jarvis-session    # Allow delete+recreate of one bucket
#
# Exit codes:
#   0 — every bucket matches its definition (or, with --dry-run, would)
#   1 — any bucket failed, was refused, or could not be read; or a fatal error
#   2 — bad command-line arguments
#
# Requires: jq, nats CLI
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
NATS_URL="${NATS_URL:-nats://localhost:4222}"
NATS_CREDS="${NATS_CREDS:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KV_DEFS_FILE="${SCRIPT_DIR}/kv-definitions.json"

# Health check settings
MAX_RETRIES=30
RETRY_INTERVAL=2

usage() {
    cat <<'EOF'
Usage: provision-kv.sh [--dry-run] [--recreate <bucket>]...

  --dry-run            Read the live buckets and print the planned changes.
                       Nothing is created, edited or deleted.
  --recreate <bucket>  If <bucket>'s storage type differs from its definition,
                       delete it (all its values are lost) and recreate it.
                       Repeat the flag to name more than one bucket.
  -h, --help           Show this help.
EOF
}

usage_error() {
    echo "[FATAL] $1" >&2
    usage >&2
    exit 2
}

# ---------------------------------------------------------------------------
# Arguments
# ---------------------------------------------------------------------------
DRY_RUN=false
RECREATE=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=true
            ;;
        --recreate)
            [[ $# -ge 2 && -n "$2" ]] || usage_error "--recreate needs a bucket name"
            RECREATE+=("$2")
            shift
            ;;
        --recreate=*)
            [[ -n "${1#--recreate=}" ]] || usage_error "--recreate needs a bucket name"
            RECREATE+=("${1#--recreate=}")
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            usage_error "unknown argument: $1"
            ;;
    esac
    shift
done

if [[ "$DRY_RUN" == "true" ]]; then
    echo "=== DRY RUN MODE — no changes will be made ==="
fi

# Summary counters
created=0
updated=0
recreated=0
current=0
refused=0
errors=0

# ---------------------------------------------------------------------------
# Prerequisite checks
# ---------------------------------------------------------------------------
command -v jq >/dev/null 2>&1 || {
    echo "[FATAL] jq is required but not installed. Install with: brew install jq" >&2
    exit 1
}

command -v nats >/dev/null 2>&1 || {
    echo "[FATAL] nats CLI is required but not installed. See: https://github.com/nats-io/natscli" >&2
    exit 1
}

if [[ ! -f "$KV_DEFS_FILE" ]]; then
    echo "[FATAL] KV definitions file not found: $KV_DEFS_FILE" >&2
    exit 1
fi

# Every --recreate name must be a defined bucket (guards against typos)
if [[ ${#RECREATE[@]} -gt 0 ]]; then
    for r in "${RECREATE[@]}"; do
        if ! jq -e --arg n "$r" '.kv_buckets | any(.name == $n)' "$KV_DEFS_FILE" >/dev/null; then
            usage_error "--recreate $r: no such bucket in $(basename "$KV_DEFS_FILE")"
        fi
    done
fi

# ---------------------------------------------------------------------------
# Build common nats CLI flags array
# ---------------------------------------------------------------------------
NATS_OPTS=("--server" "$NATS_URL")
if [[ -n "$NATS_CREDS" ]]; then
    NATS_OPTS+=("--creds" "$NATS_CREDS")
fi

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Hide any user:password@ embedded in a URL or in CLI error text
redact() {
    sed -E 's#//[^/@[:space:]]*@#//***@#g'
}

recreate_requested() {
    local name="$1" r
    for r in ${RECREATE[@]+"${RECREATE[@]}"}; do
        [[ "$r" == "$name" ]] && return 0
    done
    return 1
}

# "64KB" -> 65536. KB/MB/GB are 1024-based, as in the nats CLI.
size_to_bytes() {
    local s="$1" num unit mult
    if [[ ! "$s" =~ ^([0-9]+)[[:space:]]*([A-Za-z]*)$ ]]; then
        return 1
    fi
    num="${BASH_REMATCH[1]}"
    unit="$(echo "${BASH_REMATCH[2]}" | tr '[:lower:]' '[:upper:]')"
    case "$unit" in
        ""|B) mult=1 ;;
        K|KB|KIB) mult=1024 ;;
        M|MB|MIB) mult=1048576 ;;
        G|GB|GIB) mult=1073741824 ;;
        *) return 1 ;;
    esac
    echo $((num * mult))
}

# "7d" -> seconds. Empty/null means no TTL (0).
duration_to_seconds() {
    local d="$1" num
    if [[ -z "$d" || "$d" == "null" ]]; then
        echo 0
        return 0
    fi
    if [[ ! "$d" =~ ^([0-9]+)([smhdw])$ ]]; then
        return 1
    fi
    num="${BASH_REMATCH[1]}"
    case "${BASH_REMATCH[2]}" in
        s) echo "$num" ;;
        m) echo $((num * 60)) ;;
        h) echo $((num * 3600)) ;;
        d) echo $((num * 86400)) ;;
        w) echo $((num * 604800)) ;;
    esac
}

# Nanoseconds -> "604800s" / "0.5s" (exact: no rounding, so sub-second drift shows)
format_ns() {
    local ns="$1" frac
    if (( ns % 1000000000 == 0 )); then
        echo "$((ns / 1000000000))s"
        return 0
    fi
    printf -v frac '%09d' $((ns % 1000000000))
    frac="${frac%"${frac##*[!0]}"}"
    echo "$((ns / 1000000000)).${frac}s"
}

# Run a nats command quietly; on failure print its (redacted) error output
run_nats() {
    local out rc=0
    out="$(nats "$@" "${NATS_OPTS[@]}" 2>&1 >/dev/null)" || rc=$?
    if [[ $rc -ne 0 && -n "$out" ]]; then
        echo "$out" | redact | sed 's/^/        /' >&2
    fi
    return $rc
}

# Checks a `nats stream info --json` response and prints either
#   "OK <storage> <history> <max_value_size> <ttl_ns> <replicas> <messages>"
# or "INVALID <reasons>". Every setting the script compares must be present and
# well-formed: a missing or unknown value is never read as a difference (that
# could delete a bucket over a storage type nobody actually established).
# max_msg_size is the one optional field — the CLI omits it when 0, which the
# server treats as unlimited (-1). max_age is compared in exact nanoseconds.
# shellcheck disable=SC2016  # $-names below are jq variables, not shell
LIVE_JQ='
def isint: type == "number" and . == floor;
(if type == "object" then . else {} end) as $r
| ($r.config | if type == "object" then . else null end) as $c
| ($r.state | if type == "object" then . else null end) as $s
| if $c == null then "INVALID no config object"
  else
    [ (if $c.name != $stream then "config.name is \($c.name | tojson), expected \($stream | tojson)" else empty end),
      (if $c.storage == "file" or $c.storage == "memory" then empty else "config.storage is \($c.storage | tojson), expected \"file\" or \"memory\"" end),
      (if ($c.max_msgs_per_subject | isint) and $c.max_msgs_per_subject >= 1 then empty else "config.max_msgs_per_subject is \($c.max_msgs_per_subject | tojson)" end),
      (if $c.max_msg_size == null or (($c.max_msg_size | isint) and $c.max_msg_size >= -1) then empty else "config.max_msg_size is \($c.max_msg_size | tojson)" end),
      (if ($c.max_age | isint) and $c.max_age >= 0 then empty else "config.max_age is \($c.max_age | tojson)" end),
      (if ($c.num_replicas | isint) and $c.num_replicas >= 1 then empty else "config.num_replicas is \($c.num_replicas | tojson)" end),
      (if $s != null and ($s.messages | isint) and $s.messages >= 0 then empty else "state.messages is \($s.messages? | tojson)" end)
    ] as $bad
    | if ($bad | length) > 0 then "INVALID " + ($bad | join("; "))
      else "OK " + ([ $c.storage, $c.max_msgs_per_subject,
                      ($c.max_msg_size // -1 | if . == 0 then -1 else . end),
                      $c.max_age, $c.num_replicas, $s.messages ]
                    | map(tostring) | join(" "))
      end
  end'

# Live settings of a bucket as "storage history max_value_size ttl_ns replicas messages".
# Returns 1 if the bucket cannot be read, 2 if the response is not valid
# settings (reason on stderr). Callers must not change anything on either.
read_live() {
    local name="$1" info checked
    info="$(nats stream info "KV_${name}" --json "${NATS_OPTS[@]}" 2>/dev/null)" || return 1
    if ! checked="$(jq -r --arg stream "KV_${name}" "$LIVE_JQ" <<< "$info" 2>/dev/null)"; then
        echo "        response is not JSON" >&2
        return 2
    fi
    case "$checked" in
        "OK "*) checked="${checked#OK }" ;;
        "INVALID "*) echo "        ${checked#INVALID }" >&2; return 2 ;;
        *) echo "        unexpected response" >&2; return 2 ;;
    esac
    # Belt and braces: exactly six well-formed fields (e.g. no 1e+18 from an old jq)
    if [[ ! "$checked" =~ ^(file|memory)\ [0-9]+\ -?[0-9]+\ [0-9]+\ [0-9]+\ [0-9]+$ ]]; then
        echo "        unexpected settings: $checked" >&2
        return 2
    fi
    echo "$checked"
}

# Names of the buckets that exist on the server, one per line
list_buckets() {
    nats kv ls --names "${NATS_OPTS[@]}" 2>/dev/null
}

# ---------------------------------------------------------------------------
# Wait for NATS health
# ---------------------------------------------------------------------------
wait_for_nats() {
    local attempt=1
    echo "Waiting for NATS server at $(echo "$NATS_URL" | redact)..."
    while [[ $attempt -le $MAX_RETRIES ]]; do
        if nats server check connection "${NATS_OPTS[@]}" --timeout 2s >/dev/null 2>&1; then
            echo "NATS server is ready."
            return 0
        fi
        echo "  Attempt ${attempt}/${MAX_RETRIES} — NATS not ready, retrying in ${RETRY_INTERVAL}s..."
        sleep "$RETRY_INTERVAL"
        attempt=$((attempt + 1))
    done
    echo "[FATAL] NATS server not reachable after ${MAX_RETRIES} attempts." >&2
    exit 1
}

# ---------------------------------------------------------------------------
# Create a bucket with every defined setting, then confirm it
# ---------------------------------------------------------------------------
create_bucket() {
    local name="$1" storage="$2" history="$3" max_bytes="$4" ttl_s="$5" replicas="$6"

    # -1 (unlimited) is the default and would parse as a flag, so omit it
    local opts=("--storage" "$storage" "--history" "$history" "--replicas" "$replicas")
    if [[ "$max_bytes" -ge 0 ]]; then
        opts+=("--max-value-size" "$max_bytes")
    fi
    if [[ "$ttl_s" -gt 0 ]]; then
        opts+=("--ttl" "${ttl_s}s")
    fi

    run_nats kv add "$name" "${opts[@]}"
}

# ---------------------------------------------------------------------------
# Re-read a bucket and check it now matches its definition
# ---------------------------------------------------------------------------
confirm_bucket() {
    local name="$1" want="$2" live
    if ! live="$(read_live "$name")"; then
        echo "[ERROR] KV $name — could not re-read valid bucket settings to confirm the change" >&2
        return 1
    fi
    # Compare the five settings; ignore the trailing message count
    if [[ "${live% *}" != "$want" ]]; then
        echo "[ERROR] KV $name — still differs after the change (live: ${live% *}; want: $want)" >&2
        return 1
    fi
    return 0
}

# ---------------------------------------------------------------------------
# Reconcile a single KV bucket
# ---------------------------------------------------------------------------
provision_kv_bucket() {
    local name="$1"
    local ttl="$2"
    local storage="$3"
    local history="$4"
    local max_value_size="$5"
    local replicas="$6"
    local exists="$7"

    # Normalise the definition; empty/null fields take the nats defaults
    [[ -z "$storage" || "$storage" == "null" ]] && storage="file"
    [[ -z "$history" || "$history" == "null" ]] && history=1
    [[ -z "$replicas" || "$replicas" == "null" ]] && replicas=1

    local max_bytes=-1
    if [[ -n "$max_value_size" && "$max_value_size" != "null" ]]; then
        if ! max_bytes="$(size_to_bytes "$max_value_size")"; then
            echo "[ERROR] KV $name — max_value_size '$max_value_size' is not a size (e.g. 64KB)" >&2
            errors=$((errors + 1))
            return 0
        fi
    fi

    local ttl_s
    if ! ttl_s="$(duration_to_seconds "$ttl")"; then
        echo "[ERROR] KV $name — ttl '$ttl' is not a duration (e.g. 1h, 7d)" >&2
        errors=$((errors + 1))
        return 0
    fi

    # TTL is compared in nanoseconds, as the server stores it
    local ttl_ns=$((ttl_s * 1000000000))
    local want="$storage $history $max_bytes $ttl_ns $replicas"
    local add_cmd="nats kv add $name --storage $storage --history $history --replicas $replicas"
    [[ "$max_bytes" -ge 0 ]] && add_cmd+=" --max-value-size $max_bytes"
    [[ "$ttl_s" -gt 0 ]] && add_cmd+=" --ttl ${ttl_s}s"

    # ---- Missing bucket: create ------------------------------------------
    if [[ "$exists" != "true" ]]; then
        if [[ "$DRY_RUN" == "true" ]]; then
            echo "[DRY-RUN] Would create KV $name: $add_cmd"
            created=$((created + 1))
            return 0
        fi
        if create_bucket "$name" "$storage" "$history" "$max_bytes" "$ttl_s" "$replicas" \
            && confirm_bucket "$name" "$want"; then
            echo "[CREATE] KV $name"
            created=$((created + 1))
        else
            echo "[ERROR] KV $name — failed to create bucket" >&2
            errors=$((errors + 1))
        fi
        return 0
    fi

    # ---- Existing bucket: read and compare ------------------------------
    local live rc=0
    live="$(read_live "$name")" || rc=$?
    if [[ $rc -eq 2 ]]; then
        echo "[ERROR] KV $name — nats stream info KV_$name --json returned missing or invalid settings (above); nothing changed" >&2
        errors=$((errors + 1))
        return 0
    elif [[ $rc -ne 0 ]]; then
        echo "[ERROR] KV $name — could not read bucket settings (nats stream info KV_$name --json)" >&2
        errors=$((errors + 1))
        return 0
    fi

    local cur_storage cur_history cur_max_bytes cur_ttl_ns cur_replicas cur_msgs
    read -r cur_storage cur_history cur_max_bytes cur_ttl_ns cur_replicas cur_msgs <<< "$live"

    local changes=()
    [[ "$cur_history" != "$history" ]] && changes+=("history $cur_history -> $history")
    [[ "$cur_max_bytes" != "$max_bytes" ]] && changes+=("max_value_size $cur_max_bytes -> $max_bytes")
    [[ "$cur_ttl_ns" != "$ttl_ns" ]] && changes+=("ttl $(format_ns "$cur_ttl_ns") -> $(format_ns "$ttl_ns")")
    [[ "$cur_replicas" != "$replicas" ]] && changes+=("replicas $cur_replicas -> $replicas")

    # ---- Storage differs: refuse, or delete+recreate when named ---------
    if [[ "$cur_storage" != "$storage" ]]; then
        if recreate_requested "$name"; then
            if [[ "$DRY_RUN" == "true" ]]; then
                echo "[DRY-RUN] Would RECREATE KV $name: storage $cur_storage -> $storage; DELETES the bucket and its ${cur_msgs} stored value(s):"
                echo "            nats kv del $name --force"
                echo "            $add_cmd"
                recreated=$((recreated + 1))
                return 0
            fi
            echo "[RECREATE] KV $name — storage $cur_storage -> $storage: deleting the bucket (${cur_msgs} stored value(s) lost) and recreating it"
            if run_nats kv del "$name" --force \
                && create_bucket "$name" "$storage" "$history" "$max_bytes" "$ttl_s" "$replicas" \
                && confirm_bucket "$name" "$want"; then
                echo "[RECREATE] KV $name — done"
                recreated=$((recreated + 1))
            else
                echo "[ERROR] KV $name — delete+recreate failed; if the bucket is now missing, re-running this script creates it" >&2
                errors=$((errors + 1))
            fi
            return 0
        fi
        echo "[REFUSED] KV $name — storage is $cur_storage, definition wants $storage." >&2
        echo "          Storage cannot be edited; the bucket must be deleted and recreated, losing its ${cur_msgs} stored value(s)." >&2
        echo "          Re-run with --recreate $name to do that." >&2
        refused=$((refused + 1))
        errors=$((errors + 1))
        # Fall through: still correct the settings that can be edited in place
    fi

    if [[ ${#changes[@]} -eq 0 ]]; then
        if [[ "$cur_storage" == "$storage" ]]; then
            echo "[OK] KV $name"
            current=$((current + 1))
        fi
        return 0
    fi

    # ---- Editable settings differ: nats kv edit -------------------------
    # Pass every managed setting (not only the changed ones) so the result is
    # the definition however the CLI treats omitted flags; TTL only when a TTL
    # is wanted or one must be removed.
    local edit_opts=("--history" "$history" "--replicas" "$replicas")
    if [[ "$max_bytes" -ge 0 ]]; then
        edit_opts+=("--max-value-size" "$max_bytes")
    elif [[ "$cur_max_bytes" != "$max_bytes" ]]; then
        edit_opts+=("--max-value-size=-1")
    fi
    if [[ "$ttl_s" -gt 0 || "$cur_ttl_ns" != "$ttl_ns" ]]; then
        edit_opts+=("--ttl" "${ttl_s}s")
    fi

    local summary
    summary="$(printf '%s, ' "${changes[@]}")"
    summary="${summary%, }"

    if [[ "$DRY_RUN" == "true" ]]; then
        echo "[DRY-RUN] Would update KV $name: $summary"
        echo "            nats kv edit $name ${edit_opts[*]}"
        updated=$((updated + 1))
        return 0
    fi

    # After a refused storage change the confirm must ignore storage
    local want_after="$want"
    [[ "$cur_storage" != "$storage" ]] && want_after="$cur_storage ${want#* }"

    if run_nats kv edit "$name" "${edit_opts[@]}" && confirm_bucket "$name" "$want_after"; then
        echo "[UPDATE] KV $name: $summary"
        updated=$((updated + 1))
    else
        echo "[ERROR] KV $name — failed to update bucket ($summary)" >&2
        errors=$((errors + 1))
    fi
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
    echo "=========================================="
    echo "KV Bucket Provisioning"
    echo "=========================================="
    echo "NATS URL:    $(echo "$NATS_URL" | redact)"
    echo "Definitions: ${KV_DEFS_FILE}"
    echo ""

    # The dry run reads the live buckets too, so both modes need the server
    wait_for_nats

    local existing
    if ! existing="$(list_buckets)"; then
        echo "[FATAL] Could not list KV buckets (nats kv ls --names)." >&2
        exit 1
    fi

    # Count total KV buckets from .kv_buckets[] array
    local total
    total=$(jq '.kv_buckets | length' "$KV_DEFS_FILE")
    echo "Processing ${total} KV bucket definitions..."
    echo ""

    # Iterate over each KV bucket in .kv_buckets[] and extract fields
    local i=0
    while [[ $i -lt $total ]]; do
        local name ttl storage history max_value_size replicas exists

        name=$(jq -r ".kv_buckets[$i].name" "$KV_DEFS_FILE")
        ttl=$(jq -r ".kv_buckets[$i].ttl // empty" "$KV_DEFS_FILE")
        storage=$(jq -r ".kv_buckets[$i].storage // empty" "$KV_DEFS_FILE")
        history=$(jq -r ".kv_buckets[$i].history // empty" "$KV_DEFS_FILE")
        max_value_size=$(jq -r ".kv_buckets[$i].max_value_size // empty" "$KV_DEFS_FILE")
        replicas=$(jq -r ".kv_buckets[$i].replicas // empty" "$KV_DEFS_FILE")

        exists=false
        if grep -qxF -- "$name" <<< "$existing"; then
            exists=true
        fi

        provision_kv_bucket "$name" "$ttl" "$storage" "$history" "$max_value_size" "$replicas" "$exists"

        i=$((i + 1))
    done

    # ---------------------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------------------
    local mode=""
    [[ "$DRY_RUN" == "true" ]] && mode=" (planned)"
    echo ""
    echo "=========================================="
    echo "KV Buckets${mode}: ${created} created, ${updated} updated, ${recreated} recreated, ${current} already current, ${errors} errors (${refused} refused)"
    echo "=========================================="

    if [[ $errors -gt 0 ]]; then
        echo "WARNING: ${errors} bucket(s) had errors or were refused. Check output above." >&2
        exit 1
    fi

    exit 0
}

main
