#!/usr/bin/env bash
# =======================================
# rotate-nats-password.sh — per-account rotation of the eight NATS account
# passwords on the ships-computer broker, generalizing the rotate.sh gate
# grammar to the founding secrets-register entry's tested recipe.
# =======================================
#
# SPEC (binding, newest-doc-wins):
#   docs/secrets-register/PAGE-jarvis-nats-password.md §5 (the tested recipe) +
#   docs/ways-of-working/fleet-secrets-register-build-handoff.md §3C +
#   fleet-memory/deploy/nas/rotate.sh (the R0/R2a/R2/R3 gate grammar).
#
# THE DELIVERY MECHANISM (founding §5, supersedes the old docker-cp path):
#   The broker entrypoint (scripts/docker-entrypoint.sh) re-renders
#   config/accounts/accounts.conf from the environment via envsubst on EVERY
#   container START. Rotation delivery is therefore:
#       edit the env-file  ->  RECREATE the container.
#   There is NO docker cp and NO host-mount of the rendered file. A plain
#   `docker restart` does NOT re-read an env-file (compose loads env_file only
#   when the container is (re)created) — so the delivery step is a RECREATE,
#   never a restart. Drift D2 (a recreate "loses" accounts.conf) is retired:
#   a recreate REGENERATES it from the env.
#
# SECRETS HYGIENE (survives a `ps -eo args` audit):
#   Passwords travel STDIN -> shell var -> the nats CLI's NATS_USER/NATS_PASSWORD
#   ENVIRONMENT (an assignment PREFIX on the nats invocation, consumed by the
#   shell — never the process argv). We never use `env VAR=val nats ...` because
#   that form would place `val` in the argv of the `env` binary. We never pass a
#   password on any argv, never echo it, never write it to a committed file.
#   The env-file the script edits is a git-ignored runtime file (chmod 600).
#
# WHAT THIS SCRIPT DOES NOT DO:
#   - It never runs the LIVE broker recreate in the Sec build lane. The
#     compose-recreate delivery mode is the OPERATOR's attended path; the build
#     lane and its ephemeral test always use --restart-mode external.
#   - It requires an explicit --container target (no default) so a stray
#     invocation can only ever resolve to a named scratch container.
#   - Dry-run is the default. Nothing is written and no docker/nats verb runs
#     beyond `docker inspect` until --execute is given.
#
# USAGE:
#   rotate-nats-password.sh --account <NAME> --container <name> [options]
#
#   Required:
#     --account <ADMIN|RICH|JAMES|MARK|FORGE|FLEET_MEMORY|GUARDKIT|JARVIS>
#     --container <name>        target broker container (NO default)
#   Options:
#     --env-file <path>         default: the .env beside this repo root
#     --register-page <path>    consumer-checklist source
#                               default: the ai-transition PAGE-nats.md
#     --restart-mode <compose-recreate|external>   default: external
#     --skip-freeze-check       skip the JetStream restart-freeze gate (loud)
#     --compose-file <path>     compose file for compose-recreate mode
#     --poll-timeout <seconds>  how long to wait for the recreate (default 60)
#     --execute                 actually rotate (default is dry-run)
#     -h | --help
#
#   The NEW password is read from STDIN (a silent prompt on a tty, else the
#   first line piped in). The OLD password is optional (a second silent prompt,
#   or the second piped line) and enables gate R3.
#
# EXIT: 0 = all gates passed (or a clean dry-run) · non-zero = a gate failed.
# =======================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
ACCOUNT=""
CONTAINER=""
ENV_FILE="${REPO_ROOT}/.env"
REGISTER_PAGE="${SCRIPT_DIR}/../../ai-transition/docs/secrets-register/PAGE-nats.md"
RESTART_MODE="external"
COMPOSE_FILE="${REPO_ROOT}/docker-compose.yml"
SKIP_FREEZE="false"
POLL_TIMEOUT="60"
EXECUTE="false"

# A deliberately-wrong password for the gate-of-the-gate probe (R2a). It is not
# a secret: it exists only to prove the auth path actually checks passwords.
WRONG_PW="definitely-wrong-password-probe"

die() { echo "ERROR: $*" >&2; exit 1; }

usage() { sed -n '2,60p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }

# ---------------------------------------------------------------------------
# Parse arguments (no secret ever arrives on argv)
# ---------------------------------------------------------------------------
while [ "$#" -gt 0 ]; do
    case "$1" in
        --account)        ACCOUNT="${2:-}"; shift 2 ;;
        --container)      CONTAINER="${2:-}"; shift 2 ;;
        --env-file)       ENV_FILE="${2:-}"; shift 2 ;;
        --register-page)  REGISTER_PAGE="${2:-}"; shift 2 ;;
        --restart-mode)   RESTART_MODE="${2:-}"; shift 2 ;;
        --compose-file)   COMPOSE_FILE="${2:-}"; shift 2 ;;
        --poll-timeout)   POLL_TIMEOUT="${2:-}"; shift 2 ;;
        --skip-freeze-check) SKIP_FREEZE="true"; shift ;;
        --execute)        EXECUTE="true"; shift ;;
        -h|--help)        usage; exit 0 ;;
        *) die "unknown argument: $1 (see --help)" ;;
    esac
done

[ -n "${ACCOUNT}" ]   || die "--account is required (see --help)"
[ -n "${CONTAINER}" ] || die "--container is required and has no default (see --help)"

case "${RESTART_MODE}" in
    compose-recreate|external) ;;
    *) die "--restart-mode must be compose-recreate or external" ;;
esac

# ---------------------------------------------------------------------------
# Per-account map (VALUES cited from config/accounts/accounts.conf.template @
# nats-infrastructure f008c05). For each account: the NATS username, the
# password ref-name (the env-file key), and a subject the user is PERMITTED to
# publish to (so a successful publish means auth passed, not perm-denied).
# The RF (restart-freeze) column names the JetStream durable a broker recreate
# could freeze mid-ack; empty = the account has no durable, RF is N/A.
# ---------------------------------------------------------------------------
case "${ACCOUNT}" in
    ADMIN)         PROBE_USER="admin";        PROBE_SUBJECT="admin.sec.probe";          RF_STREAM="";         RF_DURABLE="" ;;
    RICH)          PROBE_USER="rich";         PROBE_SUBJECT="probe.rich";               RF_STREAM="";         RF_DURABLE="" ;;
    JAMES)         PROBE_USER="james";        PROBE_SUBJECT="probe.james";              RF_STREAM="";         RF_DURABLE="" ;;
    MARK)          PROBE_USER="mark";         PROBE_SUBJECT="finproxy.sec.probe";       RF_STREAM="";         RF_DURABLE="" ;;
    FORGE)         PROBE_USER="forge";        PROBE_SUBJECT="fleet.sec.probe";          RF_STREAM="PIPELINE"; RF_DURABLE="forge-serve" ;;
    FLEET_MEMORY)  PROBE_USER="fleet-memory"; PROBE_SUBJECT="memory.dlq.sec.probe";     RF_STREAM="MEMORY";   RF_DURABLE="fleet-memory-relay" ;;
    GUARDKIT)      PROBE_USER="guardkit";     PROBE_SUBJECT="memory.episode.sec.probe"; RF_STREAM="";         RF_DURABLE="" ;;
    JARVIS)        PROBE_USER="jarvis";       PROBE_SUBJECT="jarvis.sec.probe";         RF_STREAM="";         RF_DURABLE="" ;;
    *) die "--account must be one of ADMIN RICH JAMES MARK FORGE FLEET_MEMORY GUARDKIT JARVIS" ;;
esac
VAR_NAME="${ACCOUNT}_NATS_PASSWORD"

echo "======================================="
echo "  rotate-nats-password.sh"
echo "  account   : ${ACCOUNT}  (nats user '${PROBE_USER}', ref ${VAR_NAME})"
echo "  container : ${CONTAINER}"
echo "  env-file  : ${ENV_FILE}"
echo "  mode      : ${RESTART_MODE}  ($([ "${EXECUTE}" = "true" ] && echo EXECUTE || echo DRY-RUN))"
echo "======================================="

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
resolve_ip() {
    docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' \
        "${CONTAINER}" 2>/dev/null || true
}

container_running() {
    [ "$(docker inspect -f '{{.State.Running}}' "${CONTAINER}" 2>/dev/null || echo false)" = "true" ]
}

# Publish-probe. $1 = the password value (a function positional — internal to
# this shell, never a separate process's argv). The password reaches the nats
# CLI via the NATS_PASSWORD environment assignment PREFIX (not argv). The
# --server value is a bridge IP:port, never a secret.
probe_pub() {
    local pw="$1" ip
    ip="$(resolve_ip)"
    [ -n "${ip}" ] || return 2
    NATS_USER="${PROBE_USER}" NATS_PASSWORD="${pw}" \
        nats pub "${PROBE_SUBJECT}" "sec-rotate-probe" \
        --server "nats://${ip}:4222" --timeout 3s >/dev/null 2>&1
}

# Wait until the NEW password authenticates (i.e. the recreate has happened and
# the broker re-rendered accounts.conf from the updated env). Times out.
wait_for_new_auth() {
    local pw="$1" waited=0
    while [ "${waited}" -lt "${POLL_TIMEOUT}" ]; do
        if container_running && probe_pub "${pw}"; then
            return 0
        fi
        sleep 2
        waited=$((waited + 2))
    done
    return 1
}

# Print the consumer checklist for this account out of the register page.
print_checklist() {
    echo ""
    echo "--- Consumer checklist (from the register page) ---"
    if [ ! -f "${REGISTER_PAGE}" ]; then
        echo "register page not found at ${REGISTER_PAGE} — open it manually"
        return 0
    fi
    # Extract the account's per-user section: from its '### ...VAR' heading up to
    # the next '## '/'### ' heading. VAR_NAME is a ref-NAME (safe on argv).
    awk -v v="${VAR_NAME}" '
        found && /^#{2,3} / && $0 !~ v { exit }
        $0 ~ ("^### .*" v) { found=1 }
        found { print }
    ' "${REGISTER_PAGE}" || true
    echo "(full page: ${REGISTER_PAGE})"
}

# ---------------------------------------------------------------------------
# GATE R0 — the target container is running (inspect only, by --container name)
# ---------------------------------------------------------------------------
if container_running; then
    echo "GATE R0 PASS: container '${CONTAINER}' is running"
else
    die "GATE R0 FAIL: container '${CONTAINER}' is not running (nothing to rotate)"
fi

# ---------------------------------------------------------------------------
# GATE RF — restart-freeze gate (accounts with a JetStream durable only)
# ---------------------------------------------------------------------------
# A broker recreate briefly drops every client; if a durable pull consumer has
# an outstanding (un-acked) delivery, the recreate can freeze its queue for
# ack_wait. FORGE's PIPELINE/forge-serve is the live-proven case (post-G1
# handoff §1). We query with the account's CURRENT (old) credential, which
# still holds $JS.> until the rotation lands.
restart_freeze_gate() {
    if [ -z "${RF_DURABLE}" ]; then
        echo "GATE RF N/A: account ${ACCOUNT} has no JetStream durable — a recreate cannot freeze an ack for it"
        return 0
    fi
    if [ "${SKIP_FREEZE}" = "true" ]; then
        echo "GATE RF SKIPPED (--skip-freeze-check): NOT verifying ${RF_STREAM}/${RF_DURABLE} Ack-Pending==0."
        echo "  WARNING: recreating the broker with an outstanding ack can freeze the ${RF_DURABLE} queue for ack_wait."
        return 0
    fi
    if [ "${EXECUTE}" != "true" ]; then
        echo "GATE RF (dry-run): WOULD require ${RF_STREAM}/${RF_DURABLE} to show Ack Pending 0 before any recreate"
        return 0
    fi
    [ -n "${OLD_PW}" ] || die "GATE RF FAIL: need the CURRENT ${ACCOUNT} credential (on stdin) to query ${RF_STREAM}/${RF_DURABLE}, or pass --skip-freeze-check"
    local ip info
    ip="$(resolve_ip)"
    [ -n "${ip}" ] || die "GATE RF FAIL: cannot resolve the container IP to query the consumer"
    info="$(NATS_USER="${PROBE_USER}" NATS_PASSWORD="${OLD_PW}" \
        nats consumer info "${RF_STREAM}" "${RF_DURABLE}" \
        --server "nats://${ip}:4222" --timeout 5s 2>/dev/null || true)"
    if [ -z "${info}" ]; then
        die "GATE RF FAIL: could not read ${RF_STREAM}/${RF_DURABLE} (stream/consumer absent or auth failed); --skip-freeze-check to override"
    fi
    local pending
    pending="$(printf '%s\n' "${info}" | grep -iE 'Ack Pending|Outstanding Acks' | grep -oE '[0-9]+' | head -1)"
    if [ "${pending:-1}" != "0" ]; then
        die "GATE RF FAIL: ${RF_STREAM}/${RF_DURABLE} has Ack-Pending ${pending:-unknown} (must be 0) — wait for it to drain"
    fi
    echo "GATE RF PASS: ${RF_STREAM}/${RF_DURABLE} Ack-Pending 0 — recreate is freeze-safe"
}

# ---------------------------------------------------------------------------
# Read the NEW password (stdin only) and the OLD password (optional)
# ---------------------------------------------------------------------------
NEW_PW=""
OLD_PW=""
if [ -t 0 ]; then
    read -r -s -p "NEW ${ACCOUNT}_NATS_PASSWORD: " NEW_PW; echo ""
    read -r -s -p "OLD password (empty to skip the R3 old-credential-dead gate): " OLD_PW; echo ""
else
    IFS= read -r NEW_PW || true
    IFS= read -r OLD_PW || true
fi

[ -n "${NEW_PW}" ] || die "no NEW password on stdin"

# Charset guard (founding §5.2): config/URL-safe alphanumeric only, so the value
# is safe both in the NATS config and inside any URL. REGENERATE, do not widen —
# widening the charset would re-introduce the quoting hazards this closes.
if ! [[ "${NEW_PW}" =~ ^[A-Za-z0-9]+$ ]]; then
    die "NEW password has characters outside [A-Za-z0-9] — regenerate (e.g. openssl rand -hex 24), do not widen the charset"
fi

# Run RF now that OLD_PW is known.
restart_freeze_gate

# ---------------------------------------------------------------------------
# The env-file must exist and contain exactly one target line.
# ---------------------------------------------------------------------------
[ -f "${ENV_FILE}" ] || die "env-file not found: ${ENV_FILE}"
match_count="$(grep -c "^${VAR_NAME}=" "${ENV_FILE}" || true)"
[ "${match_count}" = "1" ] || die "expected exactly one '${VAR_NAME}=' line in ${ENV_FILE}, found ${match_count}"

# ---------------------------------------------------------------------------
# DRY-RUN — print the plan and stop (no writes, no docker/nats mutation).
# ---------------------------------------------------------------------------
if [ "${EXECUTE}" != "true" ]; then
    echo ""
    echo "--- DRY-RUN PLAN (no changes made; re-run with --execute) ---"
    echo "  1. GATE R0 / GATE RF checked above."
    echo "  2. WOULD atomically rewrite the single '${VAR_NAME}=' line in ${ENV_FILE} (mode preserved)."
    if [ "${RESTART_MODE}" = "compose-recreate" ]; then
        echo "  3. WOULD recreate the container (OPERATOR path):"
        echo "       docker compose -f ${COMPOSE_FILE} --project-directory ${REPO_ROOT} up -d --force-recreate ${CONTAINER}"
    else
        echo "  3. WOULD signal the invoker to recreate '${CONTAINER}' (external mode), then wait for the new credential to go live."
    fi
    echo "  4. WOULD run the gates against the recreated broker:"
    echo "       GATE R2a  wrong password REFUSED (else abort: auth path vacuous)"
    echo "       GATE R2   NEW password AUTHENTICATES (nats user '${PROBE_USER}', subject '${PROBE_SUBJECT}')"
    echo "       GATE R3   OLD password REFUSED $([ -n "${OLD_PW}" ] && echo '(old provided)' || echo '(SKIP — no old given)')"
    print_checklist
    echo ""
    echo "DRY-RUN complete — no changes made."
    exit 0
fi

# ---------------------------------------------------------------------------
# EXECUTE — atomic env-file edit (only the target line changes; mode preserved).
# The NEW value is written via a pure-shell rewrite; it never touches argv.
# ---------------------------------------------------------------------------
old_mode="$(stat -c '%a' "${ENV_FILE}")"
tmp_env="$(mktemp "${ENV_FILE}.rotate.XXXXXX")"
chmod "${old_mode}" "${tmp_env}"
rewrote=0
while IFS= read -r line || [ -n "${line}" ]; do
    case "${line}" in
        "${VAR_NAME}="*) printf '%s=%s\n' "${VAR_NAME}" "${NEW_PW}"; rewrote=1 ;;
        *)               printf '%s\n' "${line}" ;;
    esac
done < "${ENV_FILE}" > "${tmp_env}"
if [ "${rewrote}" != "1" ]; then
    rm -f "${tmp_env}"
    die "internal: did not rewrite the '${VAR_NAME}=' line"
fi
mv "${tmp_env}" "${ENV_FILE}"
echo "GATE R1 PASS: '${VAR_NAME}' line updated in ${ENV_FILE} (mode ${old_mode} preserved)"

# ---------------------------------------------------------------------------
# Deliver: recreate the container so the entrypoint re-renders accounts.conf.
# ---------------------------------------------------------------------------
if [ "${RESTART_MODE}" = "compose-recreate" ]; then
    # OPERATOR-ONLY attended path — the Sec build lane never reaches here.
    echo "Recreating via compose (OPERATOR path)..."
    docker compose -f "${COMPOSE_FILE}" --project-directory "${REPO_ROOT}" up -d --force-recreate "${CONTAINER}"
else
    # external: the invoker performs the recreate; we gate+probe around it.
    echo ""
    echo "ROTATE-EXTERNAL-RECREATE-NOW"
    echo "  ACTION REQUIRED: recreate container '${CONTAINER}' now with the updated env-file."
    echo "  Waiting up to ${POLL_TIMEOUT}s for the new credential to become live..."
fi

if wait_for_new_auth "${NEW_PW}"; then
    echo "recreate observed: the broker accepted the new credential."
else
    die "the new credential never became live within ${POLL_TIMEOUT}s — recreate did not happen or failed"
fi

# ---------------------------------------------------------------------------
# GATE R2a — gate-of-the-gate: a WRONG password MUST be refused. If it is not,
# the auth path is vacuous and R2/R3 would prove nothing — abort.
# ---------------------------------------------------------------------------
if probe_pub "${WRONG_PW}"; then
    die "GATE R2a FAIL: a deliberately-wrong password AUTHENTICATED — auth path vacuous; aborting before R2/R3"
fi
echo "GATE R2a PASS: the auth path refuses a wrong password"

# ---------------------------------------------------------------------------
# GATE R2 — the NEW password authenticates.
# ---------------------------------------------------------------------------
if probe_pub "${NEW_PW}"; then
    echo "GATE R2 PASS: new password authenticates (user '${PROBE_USER}')"
else
    die "GATE R2 FAIL: new password rejected — env-file and broker disagree; investigate before touching consumers"
fi

# ---------------------------------------------------------------------------
# GATE R3 — the OLD password is refused (the property that makes it a rotation).
# ---------------------------------------------------------------------------
if [ -n "${OLD_PW}" ]; then
    if probe_pub "${OLD_PW}"; then
        die "GATE R3 FAIL: the OLD password still authenticates — rotation did not take"
    fi
    echo "GATE R3 PASS: old credential is dead"
else
    echo "GATE R3 SKIPPED: no old password provided (pipe a second line / enter it at the prompt to enable)"
fi

echo ""
echo "=== Rotation complete for ${ACCOUNT} on '${CONTAINER}' ==="
print_checklist
