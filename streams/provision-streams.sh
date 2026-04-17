#!/usr/bin/env bash
# =============================================================================
# provision-streams.sh — Idempotent JetStream Stream & KV Bucket Provisioning
# =============================================================================
# Reads stream and KV bucket definitions from streams/stream-definitions.json
# and applies the check-then-create-or-update idempotency pattern for each.
#
# Safe to run multiple times: on first deploy, on reboot, and after definition changes.
#
# Environment variables:
#   NATS_URL    — NATS server URL (default: nats://localhost:4222)
#   NATS_CREDS  — Path to NATS credentials file (optional)
#
# Usage:
#   ./streams/provision-streams.sh              # Provision all streams and KV buckets
#   ./streams/provision-streams.sh --dry-run    # Preview actions without modifying
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
STREAM_DEFS_FILE="${SCRIPT_DIR}/stream-definitions.json"

# Health check settings
MAX_RETRIES=30
RETRY_INTERVAL=2

# Dry-run mode
DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
    echo "=== DRY RUN MODE — no changes will be made ==="
fi

# Summary counters — streams
created=0
updated=0
current=0
errors=0

# Summary counters — KV buckets
kv_created=0
kv_updated=0
kv_current=0
kv_errors=0

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

if [[ ! -f "$STREAM_DEFS_FILE" ]]; then
    echo "[FATAL] Stream definitions file not found: $STREAM_DEFS_FILE" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Build common nats CLI flags array
# ---------------------------------------------------------------------------
NATS_OPTS=("--server" "$NATS_URL")
if [[ -n "$NATS_CREDS" ]]; then
    NATS_OPTS+=("--creds" "$NATS_CREDS")
fi

# ---------------------------------------------------------------------------
# Wait for NATS health
# ---------------------------------------------------------------------------
wait_for_nats() {
    local attempt=1
    echo "Waiting for NATS server at ${NATS_URL}..."
    while [[ $attempt -le $MAX_RETRIES ]]; do
        # nats server check connection verifies connectivity
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
# Compare stream config to detect if update is needed
# ---------------------------------------------------------------------------
needs_update() {
    local name="$1"
    local subjects="$2"
    local retention="$3"
    local max_age="$4"
    local max_msgs="$5"
    local storage="$6"
    local replicas="$7"

    # Get current stream info as JSON
    local info
    info=$(nats stream info "$name" "${NATS_OPTS[@]}" --json 2>/dev/null) || return 0

    # Extract current values and compare with desired
    local cur_retention cur_max_age cur_max_msgs cur_storage cur_replicas
    cur_retention=$(echo "$info" | jq -r '.config.retention // empty' 2>/dev/null || echo "")
    cur_max_msgs=$(echo "$info" | jq -r '.config.max_msgs // empty' 2>/dev/null || echo "")
    cur_storage=$(echo "$info" | jq -r '.config.storage // empty' 2>/dev/null || echo "")
    cur_replicas=$(echo "$info" | jq -r '.config.num_replicas // empty' 2>/dev/null || echo "")

    # Any mismatch means update is needed
    # Note: NATS returns retention as integer (0=limits, 2=workqueue) vs our string format
    # so we do a simpler check — attempt update if in doubt
    if [[ "$cur_max_msgs" != "$max_msgs" ]] || [[ "$cur_replicas" != "$replicas" ]]; then
        return 0  # needs update
    fi

    return 1  # no update needed
}

# ---------------------------------------------------------------------------
# Provision a single stream
# ---------------------------------------------------------------------------
provision_stream() {
    local name="$1"
    local subjects="$2"
    local retention="$3"
    local max_age="$4"
    local max_msgs="$5"
    local storage="$6"
    local replicas="$7"

    # Check if stream already exists via: nats stream info <NAME>
    if nats stream info "$name" "${NATS_OPTS[@]}" --json >/dev/null 2>&1; then
        # Stream exists — determine if update is needed
        if [[ "$DRY_RUN" == "true" ]]; then
            echo "[DRY-RUN] Would check/update stream: $name"
            current=$((current + 1))
            return 0
        fi

        if needs_update "$name" "$subjects" "$retention" "$max_age" "$max_msgs" "$storage" "$replicas"; then
            # Apply update via: nats stream update <NAME> --force
            if nats stream update "$name" "${NATS_OPTS[@]}" \
                --subjects "$subjects" \
                --retention "$retention" \
                --max-age "$max_age" \
                --max-msgs "$max_msgs" \
                --storage "$storage" \
                --replicas "$replicas" \
                --force >/dev/null 2>&1; then
                echo "[UPDATE] $name"
                updated=$((updated + 1))
            else
                echo "[ERROR] $name — failed to update stream" >&2
                errors=$((errors + 1))
            fi
        else
            echo "[OK] $name"
            current=$((current + 1))
        fi
    else
        # Stream does not exist — create via: nats stream add <NAME> --defaults
        if [[ "$DRY_RUN" == "true" ]]; then
            echo "[DRY-RUN] Would create stream: $name (subjects=$subjects, retention=$retention, max_age=$max_age)"
            created=$((created + 1))
            return 0
        fi

        if nats stream add "$name" "${NATS_OPTS[@]}" \
            --subjects "$subjects" \
            --retention "$retention" \
            --max-age "$max_age" \
            --max-msgs "$max_msgs" \
            --storage "$storage" \
            --replicas "$replicas" \
            --defaults >/dev/null 2>&1; then
            echo "[CREATE] $name"
            created=$((created + 1))
        else
            echo "[ERROR] $name — failed to create stream" >&2
            errors=$((errors + 1))
        fi
    fi
}

# ---------------------------------------------------------------------------
# Provision a single KV bucket
# ---------------------------------------------------------------------------
provision_kv_bucket() {
    local name="$1"
    local ttl="$2"

    # Build TTL flags — null/empty means no TTL (persistent)
    local ttl_opts=()
    if [[ -n "$ttl" ]] && [[ "$ttl" != "null" ]]; then
        ttl_opts=("--ttl" "$ttl")
    fi

    # Check if KV bucket already exists via: nats kv info <NAME>
    if nats kv info "$name" "${NATS_OPTS[@]}" >/dev/null 2>&1; then
        # Bucket exists — check if update is needed
        if [[ "$DRY_RUN" == "true" ]]; then
            echo "[DRY-RUN] Would check/update KV bucket: $name"
            kv_current=$((kv_current + 1))
            return 0
        fi

        # Update bucket (e.g. TTL change) — nats kv update is idempotent
        if [[ ${#ttl_opts[@]} -gt 0 ]]; then
            if nats kv update "$name" "${NATS_OPTS[@]}" "${ttl_opts[@]}" >/dev/null 2>&1; then
                echo "[UPDATE] KV $name"
                kv_updated=$((kv_updated + 1))
            else
                echo "[ERROR] KV $name — failed to update bucket" >&2
                kv_errors=$((kv_errors + 1))
            fi
        else
            echo "[OK] KV $name"
            kv_current=$((kv_current + 1))
        fi
    else
        # Bucket does not exist — create via: nats kv add <NAME>
        if [[ "$DRY_RUN" == "true" ]]; then
            echo "[DRY-RUN] Would create KV bucket: $name (ttl=${ttl:-none})"
            kv_created=$((kv_created + 1))
            return 0
        fi

        # Guard expansion: bash 3.2 (macOS) errors on "${empty_arr[@]}" under set -u
        local kv_add_rc=0
        if [[ ${#ttl_opts[@]} -gt 0 ]]; then
            nats kv add "$name" "${NATS_OPTS[@]}" "${ttl_opts[@]}" >/dev/null 2>&1 || kv_add_rc=$?
        else
            nats kv add "$name" "${NATS_OPTS[@]}" >/dev/null 2>&1 || kv_add_rc=$?
        fi
        if [[ $kv_add_rc -eq 0 ]]; then
            echo "[CREATE] KV $name"
            kv_created=$((kv_created + 1))
        else
            echo "[ERROR] KV $name — failed to create bucket" >&2
            kv_errors=$((kv_errors + 1))
        fi
    fi
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
    echo "=========================================="
    echo "JetStream Stream & KV Bucket Provisioning"
    echo "=========================================="
    echo "NATS URL:    ${NATS_URL}"
    echo "Definitions: ${STREAM_DEFS_FILE}"
    echo ""

    # Wait for NATS to be healthy (skip in dry-run mode)
    if [[ "$DRY_RUN" != "true" ]]; then
        wait_for_nats
    fi

    # Count total streams from .streams[] array
    local total
    total=$(jq '.streams | length' "$STREAM_DEFS_FILE")
    echo "Processing ${total} stream definitions..."
    echo ""

    # Iterate over each stream in .streams[] and extract fields
    local i=0
    while [[ $i -lt $total ]]; do
        local name subjects retention max_age max_msgs storage replicas

        name=$(jq -r ".streams[$i].name" "$STREAM_DEFS_FILE")
        subjects=$(jq -r ".streams[$i].subjects | join(\",\")" "$STREAM_DEFS_FILE")
        retention=$(jq -r ".streams[$i].retention" "$STREAM_DEFS_FILE")
        max_age=$(jq -r ".streams[$i].max_age" "$STREAM_DEFS_FILE")
        max_msgs=$(jq -r ".streams[$i].max_msgs" "$STREAM_DEFS_FILE")
        storage=$(jq -r ".streams[$i].storage" "$STREAM_DEFS_FILE")
        replicas=$(jq -r ".streams[$i].replicas" "$STREAM_DEFS_FILE")

        provision_stream "$name" "$subjects" "$retention" "$max_age" "$max_msgs" "$storage" "$replicas"

        i=$((i + 1))
    done

    # ---------------------------------------------------------------------------
    # Provision KV buckets (after streams)
    # ---------------------------------------------------------------------------
    echo ""
    echo "=========================================="
    echo "KV Bucket Provisioning"
    echo "=========================================="

    # Count total KV buckets from .kv_buckets[] array (default to 0 if missing)
    local kv_total
    kv_total=$(jq '.kv_buckets // [] | length' "$STREAM_DEFS_FILE")
    echo "Processing ${kv_total} KV bucket definitions..."
    echo ""

    # Iterate over each KV bucket in .kv_buckets[] and extract fields
    local j=0
    while [[ $j -lt $kv_total ]]; do
        local kv_name kv_ttl

        kv_name=$(jq -r ".kv_buckets[$j].name" "$STREAM_DEFS_FILE")
        kv_ttl=$(jq -r ".kv_buckets[$j].ttl // empty" "$STREAM_DEFS_FILE")

        provision_kv_bucket "$kv_name" "$kv_ttl"

        j=$((j + 1))
    done

    # ---------------------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------------------
    echo ""
    echo "=========================================="
    echo "Streams:    ${created} created, ${updated} updated, ${current} already current, ${errors} errors"
    echo "KV Buckets: ${kv_created} created, ${kv_updated} updated, ${kv_current} already current, ${kv_errors} errors"
    echo "=========================================="

    local total_errors=$((errors + kv_errors))
    if [[ $total_errors -gt 0 ]]; then
        echo "WARNING: ${total_errors} resource(s) had errors. Check output above." >&2
    fi

    # Exit 0 even with non-fatal errors (resources are processed individually)
    # Only fatal errors (missing jq, no NATS, missing file) cause non-zero exit
    exit 0
}

main
