#!/usr/bin/env bash
# =======================================
# rotate-nats-password.sh — per-account rotation of the eight NATS account
# passwords on the ships-computer broker, generalizing the rotate.sh gate
# grammar to the founding secrets-register entry's tested recipe.
#
# DUAL-MODE (DF-022, 2026-07-30): the broker's plaintext `.env` no longer
# exists — it is `nats/broker.enc.env` under the out-of-repo sops secrets root.
# This script reads/writes EITHER source (plaintext-preferred, sops-fallback —
# the deploy-script pattern of record) and carries the R4 consumer re-sync.
# =======================================
#
# SPEC (binding, newest-doc-wins):
#   docs/ways-of-working/secrets-close-out-and-rotation-handoff.md §3-S1 (this
#   mode) + docs/secrets-register/PAGE-nats.md §3 (the CONSUMERS map) / §5 (the
#   procedure) / §6 (the R-gate grammar) / §10.4 (the broker sops wrapper +
#   the ONE-recreate carve-out) + PAGE-jarvis-nats-password.md §5 (founding
#   recipe) + fleet-memory/deploy/nas/rotate.sh (the dual-mode loader shape).
#
# THE DELIVERY MECHANISM (founding §5 + Wave 3 `c6820ed`):
#   The broker entrypoint (scripts/docker-entrypoint.sh) re-renders
#   config/accounts/accounts.conf from the environment via envsubst on EVERY
#   container START, and the compose `nats` service now takes all eight
#   passwords as interpolated `environment:` entries (`${VAR:?}`) fed by
#   `sops exec-env` — a bare `up -d` fails loudly and ciphertext can never
#   transit envsubst. Rotation delivery is therefore:
#       edit the SOURCE (enc or plaintext)  ->  RECREATE the container
#       under `sops exec-env` with --force-recreate.
#   A plain `docker restart` does NOT re-read the env, and a value-identical
#   rendered config makes a bare `up -d` a silent no-op — `--force-recreate`
#   is the recreate verb (Wave-2 lesson).
#
# SECRETS HYGIENE (survives a `ps -eo args` audit AND a `set -x` audit):
#   - Passwords travel STDIN -> shell var -> the nats CLI's NATS_USER /
#     NATS_PASSWORD ENVIRONMENT (an assignment PREFIX consumed by the shell —
#     never the process argv). We never use `env VAR=val nats ...` (that puts
#     `val` in the argv of `env`). No password is ever echoed or committed.
#   - NEVER hand a chatty CLI a credentials-embedded URL: the 2026-07-30
#     display exposure (`nats rtt` echoed the live RICH_NATS_PASSWORD) is why
#     probes here are quiet publishes with creds via env.
#   - XTRACE LAW: every region that touches a secret value brackets itself with
#     xtrace_off / xtrace_on, so `bash -x` NEVER prints a secret. A function
#     that takes a secret in a positional MUST only be called from inside such
#     a region (the call line itself would otherwise be traced).
#   - RUNTIME PLAINTEXT LAW: the only plaintext ever written to disk is a
#     0600 temp under /run/user/$UID (the caller's private tmpfs), registered
#     in a trap that `shred -u`s it on EXIT/INT/TERM. Never /tmp, never
#     /dev/shm, never the secrets root, never a repo.
#   - PROBE-HARNESS LAW: capture `rc=$?` on the line after the probed command,
#     BEFORE any `$(…)` substitution (the Wave-2 false alarm).
#   - No inline `#` comments are ever written into an encrypted dotenv file
#     (`sops exec-env` does not strip them; they pollute values).
#
# WHAT THIS SCRIPT DOES NOT DO:
#   - It NEVER touches docker, the broker, systemd or the nats CLI unless the
#     explicit `--live` flag is passed. Default is DRY: the freeze gate, the
#     broker re-render and the R2a/R2/R3 gates are EMITTED AS OPERATOR RUNBOOK
#     STEPS for the attended session.
#   - `--live` additionally requires an explicit `--container` target (no
#     default) so a stray invocation can only ever resolve to a named scratch
#     container.
#   - Nothing is WRITTEN (env-file, enc file) until `--execute` is given.
#     `--execute` mutates secret stores; `--live` touches running services.
#     They are independent.
#   - It never SSHes. Consumer files that live on another host (Node B) are
#     emitted as runbook lines only.
#
# USAGE:
#   rotate-nats-password.sh --account <NAME> [options]
#
#   Required:
#     --account <ADMIN|RICH|JAMES|MARK|FORGE|FLEET_MEMORY|GUARDKIT|JARVIS>
#   Source selection (DF-022 dual mode):
#     --source <auto|sops|plaintext>   default auto — SOPS-PREFERRED: the
#                                      encrypted authority wins whenever it
#                                      exists; plaintext only if there is no
#                                      enc authority (DF-022 retired the broker's
#                                      plaintext .env, so a stray/restored one
#                                      must never divert a rotation). Force
#                                      plaintext with --source plaintext.
#     --secrets-root <dir>      out-of-repo sops root
#                               default /home/richardwoollcott/.config/fleet-secrets
#     --enc-file <rel>          broker authority file, RELATIVE to the root
#                               default nats/broker.enc.env
#     --sops-bin <path>         absolute sops path
#                               default /home/richardwoollcott/.local/bin/sops
#     --env-file <path>         plaintext-mode source; default the repo-root .env
#     --runtime-dir <dir>       tmpfs for the 0600 window; default /run/user/$UID
#   Consumers (R4):
#     --this-host <gb10|nodeb>  which host's consumer rows are LOCAL (default gb10)
#     --no-consumer-sync        never rewrite consumer enc files (runbook only)
#   Live actions (all default OFF):
#     --live                    permit docker/nats/systemd verbs (requires --container)
#     --container <name>        target broker container (NO default)
#     --restart-mode <compose-recreate|external>   default external
#     --compose-file <path>     compose file for compose-recreate mode
#     --skip-freeze-check       skip the JetStream Ack-Pending-0 gate (loud)
#     --poll-timeout <seconds>  wait for the recreate (default 60)
#   Other:
#     --register-page <path>    consumer-checklist source (PAGE-nats.md)
#     --execute                 actually write (default is dry-run)
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
LIVE="false"

SOURCE_MODE="auto"
SECRETS_ROOT="/home/richardwoollcott/.config/fleet-secrets"
ENC_FILE="nats/broker.enc.env"
SOPS_BIN="/home/richardwoollcott/.local/bin/sops"
RUNTIME_DIR="/run/user/$(id -u)"
THIS_HOST="gb10"
CONSUMER_SYNC="true"

# A deliberately-wrong password for the gate-of-the-gate probe (R2a). It is not
# a secret: it exists only to prove the auth path actually checks passwords.
WRONG_PW="definitely-wrong-password-probe"

die() { echo "ERROR: $*" >&2; exit 1; }

# Print the comment header only — it STOPS at the first non-comment line, so no
# live code can ever be dumped into --help however the header grows/shrinks.
usage() { awk 'NR >= 2 { if ($0 !~ /^#/) exit; sub(/^# ?/, ""); print }' "${BASH_SOURCE[0]}"; }

# ---------------------------------------------------------------------------
# CONSUMERS — the R4 map, mirroring PAGE-nats.md §3 per USER (and the §10 wave
# maps of the per-consumer pages, which name each file's sops destination).
# Columns: ACCOUNT|HOST|ENC_FILE(rel to that host's root)|MODE:KEY|req|opt|NOTE
#   MODE plain = the key's whole value IS the password.
#   MODE url   = the password is embedded in a DSN (nats://user:pw@host:port);
#                only the userinfo password is swapped, and only when the
#                userinfo user matches this account's nats user.
#   req = the key MUST be present (absence aborts BEFORE any write).
#   opt = a mapped-but-unverified copy; ABSENCE is reported SKIP, not a failure.
#         'opt' covers an absent key ONLY — a key that is present but drifted
#         (url row whose DSN is unparseable or carries a different user) aborts
#         in the PLAN phase on every row, req or opt.
# PERISHABLE — "trust the pages, verify the estate": re-read PAGE-nats §3 and
# the per-consumer pages' §10 before an attended rotation.
# Broker-only members (ADMIN / JAMES / MARK) have NO rows: PAGE-nats §8 carries
# their open DISCOVERY cells — never replace a DISCOVERY with a guess.
# ---------------------------------------------------------------------------
CONSUMERS="\
RICH|gb10|nats/specialist-agent.enc.env|plain:NATS_PASSWORD|req|specialist pair (PAGE-nats 3.5 rows 1-2): recreate BOTH roles via sops exec-env … 'docker compose -f <abs>/specialist-agent/docker-compose.dual-role.yml up -d --force-recreate'
RICH|gb10|study-tutor/study-tutor-root.enc.env|plain:NATS_PASSWORD|req|gcse-tutor (PAGE-nats 3.5 row 3 / PAGE-study-tutor 10.3): sops exec-env … 'docker compose -f <abs>/study-tutor/docker-compose.study-tutor.yml up -d --force-recreate gcse-tutor' — GB10 pair retires with the Spark move
RICH|nodeb|study-tutor/http-env.enc.env|plain:NATS_PASSWORD|opt|Node B :8100 project (PAGE-study-tutor 10.2b addendum) — VERIFY at run time whether it carries the rich NATS credential; recreate over the authorized gb10_to_nodeb route, ATTENDED
RICH|nodeb|study-tutor/http-env-kc.enc.env|plain:NATS_PASSWORD|opt|Node B :8101 keycloak/OIDC project (PAGE-study-tutor 10.2b) — verify at run time
FORGE|gb10|nats/forge-nats.enc.env|url:FORGE_NATS_URL|req|forge-prod (PAGE-nats 3.2 / 10.3) is docker run-managed, NOT compose: re-run the deploy recipe run line with -e FORGE_NATS_URL under sops exec-env — Ack-Pending-0 freeze FIRST (PIPELINE/forge-serve)
JARVIS|gb10|slack-jarvis/jarvis.enc.env|plain:JARVIS_NATS_PASSWORD|req|jarvis daemon (PAGE-slack-jarvis 10.x, systemd sops drop-in --same-process): systemctl --user stop jarvis-serve-nats; sleep 10; start — never a bare restart
FLEET_MEMORY|gb10|fleet-memory-pg/relay-env-deploy.enc.env|url:FLEET_MEMORY_NATS_URL|req|fleet-memory-relay (PAGE-nats 3.3 row 1 / PAGE-fleet-memory-pg 10.3): sops exec-env … 'docker compose up -d --force-recreate' from deploy/relay — the Created timestamp MUST change
FLEET_MEMORY|gb10|fleet-memory-pg/fleet-memory-root.enc.env|url:FLEET_MEMORY_NATS_URL|req|fleet-memory root reader (PAGE-nats 3.3 row 2) — TWICE-STALE copy (PAGE-fleet-memory-pg 9): R4 on this file is mandatory, picked up at next process start
FLEET_MEMORY|gb10|fleet-memory-pg/guardkit.enc.env|url:FLEET_MEMORY_NATS_URL|req|guardkit reader copy (PAGE-nats 3.3 row 3) — next guardkit process start
GUARDKIT|gb10|fleet-memory-pg/guardkit.enc.env|plain:GUARDKIT_NATS_PASSWORD|opt|PAGE-nats 3.4 + 8 DISCOVERY: no on-disk consumer copy was found in the 07-11 sweep — if the key is absent this is a SKIP, and the invoking env of the harvest publisher is still the open cell"

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
        --source)         SOURCE_MODE="${2:-}"; shift 2 ;;
        --secrets-root)   SECRETS_ROOT="${2:-}"; shift 2 ;;
        --enc-file)       ENC_FILE="${2:-}"; shift 2 ;;
        --sops-bin)       SOPS_BIN="${2:-}"; shift 2 ;;
        --runtime-dir)    RUNTIME_DIR="${2:-}"; shift 2 ;;
        --this-host)      THIS_HOST="${2:-}"; shift 2 ;;
        --no-consumer-sync) CONSUMER_SYNC="false"; shift ;;
        --skip-freeze-check) SKIP_FREEZE="true"; shift ;;
        --execute)        EXECUTE="true"; shift ;;
        --live)           LIVE="true"; shift ;;
        -h|--help)        usage; exit 0 ;;
        *) die "unknown argument: $1 (see --help)" ;;
    esac
done

[ -n "${ACCOUNT}" ] || die "--account is required (see --help)"

case "${SOURCE_MODE}" in
    auto|sops|plaintext) ;;
    *) die "--source must be auto, sops or plaintext" ;;
esac
case "${THIS_HOST}" in
    gb10|nodeb) ;;
    *) die "--this-host must be gb10 or nodeb" ;;
esac
case "${RESTART_MODE}" in
    compose-recreate|external) ;;
    *) die "--restart-mode must be compose-recreate or external" ;;
esac
if [ "${LIVE}" = "true" ]; then
    [ -n "${CONTAINER}" ] || die "--live requires --container (no default) — refusing to guess a live target"
else
    [ -z "${CONTAINER}" ] || die "--container given without --live: this run performs NO docker/nats action (drop --container or add --live)"
fi

# Resolve the dual-mode source. DF-022 RETIRED the broker's plaintext `.env`, so
# for THIS script `auto` is SOPS-PREFERRED (the inverse of the generic dual-mode
# loader): a stray or restored plaintext `.env` must never silently divert a
# rotation away from the encrypted authority — that would skip the ENTIRE sops
# estate (authority + every consumer enc file) and still exit 0.
AUTO_NOTE=""
if [ "${SOURCE_MODE}" = "auto" ]; then
    if [ -f "${SECRETS_ROOT}/${ENC_FILE}" ]; then
        SOURCE_MODE="sops"
    elif [ -f "${ENV_FILE}" ]; then
        SOURCE_MODE="plaintext"
        AUTO_NOTE="1"
    else
        SOURCE_MODE="sops"   # let the sops preflight say precisely what is missing
    fi
fi

# ---------------------------------------------------------------------------
# Per-account map (VALUES cited from config/accounts/accounts.conf.template @
# nats-infrastructure f008c05). For each account: the NATS username, the
# password ref-name (the env-file / enc-file key), and a subject the user is
# PERMITTED to publish to (so a successful publish means auth passed, not
# perm-denied). The RF (restart-freeze) column names the JetStream durable a
# broker recreate could freeze mid-ack; empty = no durable, RF is N/A.
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

# The broker recreate is ALWAYS gated on PIPELINE/forge-serve Ack-Pending-0 —
# it drops every client for ~2s, exactly as a forge-prod recreate does
# (PAGE-nats §5 gate 1 / §10.4). That is broker-wide, not per-account: the
# per-account RF_DURABLE above is the account's OWN durable.
BROKER_FREEZE_STREAM="PIPELINE"
BROKER_FREEZE_DURABLE="forge-serve"

echo "======================================="
echo "  rotate-nats-password.sh"
echo "  account   : ${ACCOUNT}  (nats user '${PROBE_USER}', ref ${VAR_NAME})"
echo "  source    : ${SOURCE_MODE}"
if [ "${SOURCE_MODE}" = "sops" ]; then
    echo "  root/enc  : ${SECRETS_ROOT}/${ENC_FILE}"
else
    echo "  env-file  : ${ENV_FILE}"
fi
echo "  host rows : ${THIS_HOST}  (consumer sync: ${CONSUMER_SYNC})"
echo "  live      : ${LIVE}$([ "${LIVE}" = "true" ] && echo "  container ${CONTAINER} (${RESTART_MODE})" || echo "  (no docker/nats/systemd verb will run)")"
echo "  write     : $([ "${EXECUTE}" = "true" ] && echo EXECUTE || echo DRY-RUN)"
echo "======================================="
if [ "${SOURCE_MODE}" = "plaintext" ]; then
    echo ""
    if [ -n "${AUTO_NOTE}" ]; then
        echo "NOTE: --source auto resolved to PLAINTEXT — there is no encrypted authority at"
        echo "      ${SECRETS_ROOT}/${ENC_FILE}."
    fi
    echo "WARNING: PLAINTEXT SOURCE. DF-022 retired the broker's plaintext .env. This run"
    echo "         touches ONLY ${ENV_FILE} — the sops authority and EVERY consumer enc"
    echo "         file are left untouched (R4 is runbook-only). If the estate is on sops,"
    echo "         stop and re-run with --source sops."
fi

# ---------------------------------------------------------------------------
# XTRACE LAW helpers — see the header. Bracket EVERY secret-touching region.
# ---------------------------------------------------------------------------
XTRACE_WAS=""
xtrace_off() {
    case $- in
        *x*) XTRACE_WAS="1"; set +x ;;
        *)   XTRACE_WAS="" ;;
    esac
}
xtrace_on() {
    if [ -n "${XTRACE_WAS}" ]; then XTRACE_WAS=""; set -x; fi
    return 0
}

# ---------------------------------------------------------------------------
# RUNTIME PLAINTEXT LAW — 0600 temps under the caller's tmpfs, shredded by a
# trap on every exit path.
# ---------------------------------------------------------------------------
TMP_PATHS=()
cleanup_tmp() {
    local f
    for f in "${TMP_PATHS[@]:-}"; do
        [ -n "${f}" ] || continue
        [ -e "${f}" ] || continue
        shred -u -n 1 "${f}" 2>/dev/null || rm -f "${f}" 2>/dev/null || true
    done
    TMP_PATHS=()
}
trap cleanup_tmp EXIT INT TERM

# Sets RUNTIME_TMP_OUT to a fresh 0600 temp under RUNTIME_DIR and registers it
# with the trap. NOT a $(...) helper on purpose: a command substitution runs in
# a SUBSHELL, so the registration would be lost and a failure path could leave a
# plaintext window behind.
RUNTIME_TMP_OUT=""
runtime_tmp() {
    local t
    [ -d "${RUNTIME_DIR}" ] || die "runtime dir not found: ${RUNTIME_DIR} (plaintext may live NOWHERE else)"
    t="$(mktemp "${RUNTIME_DIR}/rotate-nats.XXXXXXXX")"
    chmod 600 "${t}"
    TMP_PATHS+=("${t}")
    RUNTIME_TMP_OUT="${t}"
}

# ---------------------------------------------------------------------------
# Live helpers (docker / nats). NEVER reached unless --live.
# ---------------------------------------------------------------------------
require_live() { [ "${LIVE}" = "true" ] || die "internal: live verb attempted without --live"; }

resolve_ip() {
    require_live
    docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' \
        "${CONTAINER}" 2>/dev/null || true
}

container_running() {
    require_live
    [ "$(docker inspect -f '{{.State.Running}}' "${CONTAINER}" 2>/dev/null || echo false)" = "true" ]
}

# Publish-probe. $1 = the password value (a function positional — internal to
# this shell, never a separate process's argv). The password reaches the nats
# CLI via the NATS_PASSWORD environment assignment PREFIX (not argv). The
# --server value is a bridge IP:port and carries NO credential — the 07-30
# display-exposure rule (never a creds-embedded URL to a chatty CLI).
# XTRACE LAW: only ever called from inside an xtrace_off region.
# RC CONTRACT: 0 = authenticated · 90 = THE PROBE COULD NOT RUN (no container IP)
# · anything else = the broker refused. 90 is a distinct sentinel on purpose:
# R2a is the gate-of-the-gate, and "could not ask" must never be scored as
# "correctly refused" (that would make R2/R3 vacuous — the very thing R2a exists
# to prevent). 90 is outside the nats CLI's own exit range.
PROBE_UNAVAILABLE=90
probe_pub() {
    local pw="$1" ip
    ip="$(resolve_ip)"
    [ -n "${ip}" ] || return "${PROBE_UNAVAILABLE}"
    NATS_USER="${PROBE_USER}" NATS_PASSWORD="${pw}" \
        nats pub "${PROBE_SUBJECT}" "sec-rotate-probe" \
        --server "nats://${ip}:4222" --timeout 3s >/dev/null 2>&1
}

# Wait until the NEW password authenticates (i.e. the recreate has happened and
# the broker re-rendered accounts.conf from the updated env). Times out.
# XTRACE LAW: only ever called from inside an xtrace_off region.
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
# sops helpers. Every call runs FROM the secrets root (run-from-secrets-root
# law: .sops.yaml resolves from the WORKING DIR, not the target file's path).
# ---------------------------------------------------------------------------
sops_preflight() {
    [ -x "${SOPS_BIN}" ] || die "sops not executable at ${SOPS_BIN} (absolute path required — minimal PATHs)"
    [ -d "${SECRETS_ROOT}" ] || die "secrets root not found: ${SECRETS_ROOT}"
    [ -f "${SECRETS_ROOT}/.sops.yaml" ] || die "no .sops.yaml at ${SECRETS_ROOT} — sops would resolve the WRONG creation rules"
    # Ciphertext stays out of git, always: refuse a root that is inside a work tree.
    local inside rc
    inside="$(git -C "${SECRETS_ROOT}" rev-parse --is-inside-work-tree 2>/dev/null || true)"
    rc=0
    [ "${inside}" = "true" ] && rc=1
    [ "${rc}" = "0" ] || die "secrets root ${SECRETS_ROOT} is inside a git work tree — ciphertext NEVER lives in git"
}

# Decrypt <rel> into the global DOTENV_IN. XTRACE LAW: caller region only.
DOTENV_IN=""
sops_decrypt_into_DOTENV_IN() {
    local rel="$1"
    [ -f "${SECRETS_ROOT}/${rel}" ] || return 3
    ( cd "${SECRETS_ROOT}" && "${SOPS_BIN}" -d --input-type dotenv --output-type dotenv "${rel}" ) > /dev/null 2>&1 || return 4
    DOTENV_IN="$( cd "${SECRETS_ROOT}" && "${SOPS_BIN}" -d --input-type dotenv --output-type dotenv "${rel}" )"
    return 0
}

# Encrypt the global DOTENV_OUT back over <rel>, preserving mode. The plaintext
# window is a 0600 tmpfs temp, shredded immediately (and by the trap on any
# failure path). --filename-override makes the root's creation_rules match the
# DESTINATION path even though the input lives in /run/user (least-recipient +
# escrow rules therefore apply exactly as for an in-place edit).
# XTRACE LAW: caller region only.
DOTENV_OUT=""
sops_encrypt_from_DOTENV_OUT() {
    local rel="$1" tmp_plain tmp_cipher mode
    mode="$(stat -c '%a' "${SECRETS_ROOT}/${rel}")"
    runtime_tmp; tmp_plain="${RUNTIME_TMP_OUT}"
    runtime_tmp; tmp_cipher="${RUNTIME_TMP_OUT}"
    RUNTIME_TMP_OUT=""
    printf '%s\n' "${DOTENV_OUT}" > "${tmp_plain}"
    ( cd "${SECRETS_ROOT}" && "${SOPS_BIN}" -e --input-type dotenv --output-type dotenv \
        --filename-override "${rel}" "${tmp_plain}" ) > "${tmp_cipher}"
    # Only after a SUCCESSFUL encrypt does the destination change (set -e above).
    # COACH FIX (2026-07-30): atomic delivery — install(1) unlinks the dest
    # before recreating it, leaving a crash window in which the SOLE ciphertext
    # copy of live credentials does not exist. Stage the ciphertext (never
    # plaintext) in a temp INSIDE the destination directory and mv over the
    # dest: an atomic same-filesystem rename with no missing-file window.
    local dest_tmp
    dest_tmp="$(mktemp "${SECRETS_ROOT}/${rel}.tmp.XXXXXX")"
    cp "${tmp_cipher}" "${dest_tmp}"
    chmod "${mode}" "${dest_tmp}"
    mv -f "${dest_tmp}" "${SECRETS_ROOT}/${rel}"
    shred -u -n 1 "${tmp_plain}" 2>/dev/null || rm -f "${tmp_plain}"
    shred -u -n 1 "${tmp_cipher}" 2>/dev/null || rm -f "${tmp_cipher}"
}

# ---------------------------------------------------------------------------
# dotenv edit helpers — pure shell, no temp file, no argv, no here-strings
# (bash may back a here-string with a /tmp file; process substitution is a pipe).
# XTRACE LAW: caller region only.
# ---------------------------------------------------------------------------

# Validate a nats DSN WITHOUT touching NEW_PW — the single parser, so the PLAN
# phase and the APPLY phase can never disagree about what is rewritable.
# Globals in: URL_IN, PROBE_USER. Globals out: URL_RC (0 ok · 1 unparseable ·
# 2 different user). Never emits a value.
URL_IN=""; URL_OUT=""; URL_RC=0
url_validate() {
    local rest userinfo user
    URL_RC=0
    case "${URL_IN}" in
        *://*@*) ;;
        *) URL_RC=1; return 0 ;;
    esac
    rest="${URL_IN#*://}"
    userinfo="${rest%@*}"     # greedy-left: everything before the LAST @
    case "${userinfo}" in
        *:*) user="${userinfo%%:*}" ;;
        *) URL_RC=1; return 0 ;;
    esac
    if [ "${user}" != "${PROBE_USER}" ]; then URL_RC=2; return 0; fi
    return 0
}

# A NON-secret reason string for a URL_RC. Globals in: URL_RC. Safe to display.
url_rc_reason() {  # $1 = the key name (a ref-name, never a value)
    case "${URL_RC}" in
        1) printf '%s' "value of $1 is not a user:pw@host DSN" ;;
        2) printf '%s' "$1 carries a DIFFERENT nats user than '${PROBE_USER}'" ;;
        *) printf '%s' "internal url parse rc ${URL_RC} on $1" ;;
    esac
}

# Swap the password inside a nats DSN. Globals in: URL_IN, PROBE_USER, NEW_PW.
# Globals out: URL_OUT, URL_RC (0 ok · 1 unparseable · 2 different user).
url_swap_password() {
    local scheme rest hostpart
    URL_OUT=""
    url_validate
    [ "${URL_RC}" = "0" ] || return 0
    scheme="${URL_IN%%://*}"
    rest="${URL_IN#*://}"
    hostpart="${rest##*@}"
    URL_OUT="${scheme}://${PROBE_USER}:${NEW_PW}@${hostpart}"
    return 0
}

# Rewrite one key in DOTENV_IN -> DOTENV_OUT.
# Globals in: DOTENV_IN, EDIT_KEY, EDIT_MODE (plain|url), NEW_PW, PROBE_USER.
# Globals out: DOTENV_OUT, EDIT_HITS, EDIT_ERR ("" | a NON-secret reason).
EDIT_KEY=""; EDIT_MODE=""; EDIT_HITS=0; EDIT_ERR=""
dotenv_rewrite_key() {
    local line key value out="" first=1
    EDIT_HITS=0; EDIT_ERR=""; DOTENV_OUT=""
    while IFS= read -r line || [ -n "${line}" ]; do
        key="${line%%=*}"
        value="${line#*=}"
        if [ "${key}" = "${EDIT_KEY}" ] && [ "${line}" != "${key}" ]; then
            if [ "${EDIT_MODE}" = "url" ]; then
                URL_IN="${value}"
                url_swap_password
                if [ "${URL_RC}" = "0" ]; then
                    line="${key}=${URL_OUT}"; EDIT_HITS=$((EDIT_HITS + 1))
                else
                    # Defence-in-depth only: plan_consumers already refused this
                    # shape BEFORE any write (the two-phase guarantee).
                    EDIT_ERR="$(url_rc_reason "${EDIT_KEY}")"
                fi
                URL_IN=""; URL_OUT=""
            else
                line="${key}=${NEW_PW}"
                EDIT_HITS=$((EDIT_HITS + 1))
            fi
        fi
        if [ "${first}" = "1" ]; then out="${line}"; first=0; else out="${out}
${line}"; fi
    done < <(printf '%s\n' "${DOTENV_IN}")
    DOTENV_OUT="${out}"
}

# Read one key's value out of DOTENV_IN into VALUE_OUT (VALUE_FOUND=0/1).
# XTRACE LAW: caller region only.
VALUE_OUT=""; VALUE_FOUND=0
dotenv_get_key() {
    local line key
    VALUE_OUT=""; VALUE_FOUND=0
    while IFS= read -r line || [ -n "${line}" ]; do
        key="${line%%=*}"
        if [ "${key}" = "${EDIT_KEY}" ] && [ "${line}" != "${key}" ]; then
            VALUE_OUT="${line#*=}"; VALUE_FOUND=1
        fi
    done < <(printf '%s\n' "${DOTENV_IN}")
}

# Post-write proof: the ciphertext really carries the new value. Reports by KEY
# NAME only — never a value. Globals in: EDIT_KEY, EDIT_MODE, NEW_PW.
# XTRACE LAW: caller region only. Returns 0 pass · 1 fail.
verify_enc_key() {
    local rel="$1"
    sops_decrypt_into_DOTENV_IN "${rel}" || return 1
    dotenv_get_key
    [ "${VALUE_FOUND}" = "1" ] || return 1
    if [ "${EDIT_MODE}" = "url" ]; then
        URL_IN="${VALUE_OUT}"
        url_swap_password
        URL_IN=""
        [ "${URL_RC}" = "0" ] || return 1
        [ "${URL_OUT}" = "${VALUE_OUT}" ] || return 1
        URL_OUT=""
    else
        [ "${VALUE_OUT}" = "${NEW_PW}" ] || return 1
    fi
    VALUE_OUT=""
    return 0
}

# ---------------------------------------------------------------------------
# CONSUMER (R4) planning + application.
# ---------------------------------------------------------------------------
consumer_rows() {  # stdout: the CONSUMERS rows for this account (non-secret)
    printf '%s\n' "${CONSUMERS}" | awk -F'|' -v a="${ACCOUNT}" '$1 == a'
}

# Validate every LOCAL consumer row BEFORE any write (two-phase: ANY condition
# that would make the APPLY phase abort must be caught here, while the estate is
# still consistent). That is: the file exists · it decrypts · the key is present
# · AND (url rows) its value really is a DSN whose userinfo user is this
# account's nats user. Validating the DSN only at apply-time was the half-applied
# rotation hole — the authority and earlier rows were already rewritten before
# the drifted row was ever parsed.
# Fills CONSUMER_PLAN (rel|mode|key) — verdicts printed: APPLY · SKIP.
CONSUMER_PLAN=()
plan_consumers() {
    local row host rel spec need note mode key
    CONSUMER_PLAN=()
    [ "${SOURCE_MODE}" = "sops" ] || return 0
    [ "${CONSUMER_SYNC}" = "true" ] || return 0
    while IFS='|' read -r _acct host rel spec need note; do
        [ -n "${rel:-}" ] || continue
        [ "${host}" = "${THIS_HOST}" ] || continue
        mode="${spec%%:*}"; key="${spec#*:}"
        if [ ! -f "${SECRETS_ROOT}/${rel}" ]; then
            if [ "${need}" = "req" ]; then
                die "R4 PLAN FAIL: required consumer file missing: ${SECRETS_ROOT}/${rel} (verify the estate against PAGE-nats §3 — no write performed)"
            fi
            echo "  R4 plan: SKIP  ${rel} (${key}) — file absent, row is 'opt' [${note}]"
            continue
        fi
        xtrace_off
        if ! sops_decrypt_into_DOTENV_IN "${rel}"; then
            DOTENV_IN=""
            xtrace_on
            die "R4 PLAN FAIL: cannot decrypt ${rel} (recipient/root problem) — no write performed"
        fi
        EDIT_KEY="${key}"
        dotenv_get_key
        local found="${VALUE_FOUND}" urc=0 reason=""
        # COACH BLOCKER FIX (2026-07-30): enforce the exactly-one-line invariant
        # HERE, in PLAN, so a duplicate-key consumer file can never abort at
        # APPLY with the authority already rewritten (the half-applied-estate
        # class ffa9ed5/26eb78b closed for shape/user but not for multiplicity).
        # grep -c emits a count, never a value; we are inside xtrace_off.
        local plan_kcount
        plan_kcount="$(printf '%s\n' "${DOTENV_IN}" | grep -c "^${key}=" || true)"
        if [ "${found}" = "1" ] && [ "${plan_kcount}" != "1" ]; then
            VALUE_OUT=""; DOTENV_IN=""
            xtrace_on
            die "R4 PLAN FAIL: ${rel} carries ${plan_kcount} '${key}=' lines (expected exactly 1) — no write performed"
        fi
        # url rows: parse + user-match NOW, in the plan phase, so a drifted or
        # non-DSN value can never abort a half-written estate. The value stays
        # inside this xtrace_off region and is never emitted; only the key NAME
        # appears in the reason string.
        if [ "${found}" = "1" ] && [ "${mode}" = "url" ]; then
            URL_IN="${VALUE_OUT}"
            url_validate
            urc="${URL_RC}"
            if [ "${urc}" != "0" ]; then reason="$(url_rc_reason "${key}")"; fi
            URL_IN=""; URL_RC=0
        fi
        VALUE_OUT=""
        DOTENV_IN=""
        xtrace_on
        if [ "${found}" != "1" ]; then
            if [ "${need}" = "req" ]; then
                die "R4 PLAN FAIL: key ${key} absent from ${rel} (map vs estate drift — reconcile PAGE-nats §3 first; no write performed)"
            fi
            echo "  R4 plan: SKIP  ${rel} (${key}) — key absent, row is 'opt' [DISCOVERY stays open]"
            continue
        fi
        if [ "${urc}" != "0" ]; then
            # 'opt' covers an ABSENT key, never a PRESENT-but-drifted one: a copy
            # that claims to carry this account's credential but does not is a
            # map-vs-estate divergence the operator must reconcile first.
            die "R4 PLAN FAIL: ${rel}: ${reason} (map vs estate drift — reconcile PAGE-nats §3 first; no write performed)"
        fi
        echo "  R4 plan: APPLY ${rel} (${mode}:${key})"
        CONSUMER_PLAN+=("${rel}|${mode}|${key}")
    done < <(consumer_rows)
}

apply_consumers() {
    local entry rel mode key
    for entry in "${CONSUMER_PLAN[@]:-}"; do
        [ -n "${entry}" ] || continue
        rel="${entry%%|*}"
        mode="$(printf '%s' "${entry}" | cut -d'|' -f2)"
        key="${entry##*|}"
        xtrace_off
        sops_decrypt_into_DOTENV_IN "${rel}" || { DOTENV_IN=""; xtrace_on; die "R4 FAIL: decrypt of ${rel} failed mid-apply"; }
        EDIT_KEY="${key}"; EDIT_MODE="${mode}"
        dotenv_rewrite_key
        local hits="${EDIT_HITS}" err="${EDIT_ERR}"
        if [ -n "${err}" ]; then
            DOTENV_IN=""; DOTENV_OUT=""
            xtrace_on
            die "R4 FAIL on ${rel}: ${err}"
        fi
        if [ "${hits}" != "1" ]; then
            DOTENV_IN=""; DOTENV_OUT=""
            xtrace_on
            die "R4 FAIL on ${rel}: expected exactly one '${key}=' line, rewrote ${hits}"
        fi
        sops_encrypt_from_DOTENV_OUT "${rel}"
        DOTENV_IN=""; DOTENV_OUT=""
        local vrc=0
        verify_enc_key "${rel}" || vrc=1
        DOTENV_IN=""
        xtrace_on
        [ "${vrc}" = "0" ] || die "R4 VERIFY FAIL: ${rel} does not carry the new value after re-encrypt"
        echo "  R4 SYNCED + VERIFIED: ${rel} (${key}) — ciphertext-only, mode preserved"
    done
}

emit_consumer_runbook() {
    local row host rel spec need note
    echo ""
    echo "--- R4 CONSUMER MAP for ${ACCOUNT} (PAGE-nats §3; verify the estate before acting) ---"
    row="$(consumer_rows || true)"
    if [ -z "${row}" ]; then
        echo "  (no consumer rows mapped — broker-side only; PAGE-nats §8 holds the open DISCOVERY cell)"
        return 0
    fi
    while IFS='|' read -r _acct host rel spec need note; do
        [ -n "${rel:-}" ] || continue
        if [ "${host}" = "${THIS_HOST}" ]; then
            echo "  [${host} · LOCAL · ${need}] ${rel}  (${spec})"
        else
            echo "  [${host} · REMOTE — runbook only, this script never SSHes · ${need}] ${rel}  (${spec})"
        fi
        echo "        restart: ${note}"
    done < <(consumer_rows)
}

emit_broker_runbook() {
    local wrapper_cd
    wrapper_cd="cd ${SECRETS_ROOT} && ${SOPS_BIN} exec-env ${ENC_FILE}"
    echo ""
    echo "--- OPERATOR RUNBOOK — the live steps this script did NOT run (no --live) ---"
    echo "ATTENDED ONLY, venue claimed, Rich present. Run in this order."
    echo ""
    echo "  [FREEZE] Ack-Pending-0 gate — the broker recreate drops EVERY client for ~2s;"
    echo "           a recreate with an outstanding ack freezes the build queue for ack_wait (1h)"
    echo "           and a second restart does NOT clear it (broker-side timer)."
    echo "             ${wrapper_cd} 'nats consumer info ${BROKER_FREEZE_STREAM} ${BROKER_FREEZE_DURABLE} --server nats://127.0.0.1:4222'"
    echo "           MUST show 'Ack Pending: 0' / 'Outstanding Acks: 0'."
    echo "           Creds via NATS_USER/NATS_PASSWORD env ONLY — never on argv, and NEVER"
    echo "           embedded in a URL handed to a chatty CLI (the 2026-07-30 display exposure)."
    if [ -n "${RF_DURABLE}" ]; then
        echo "           Also this account's own durable: ${RF_STREAM}/${RF_DURABLE} Ack-Pending 0."
    fi
    echo ""
    echo "  [RE-RENDER] ONE broker recreate (the §10.4 carve-out: never two — each is a"
    echo "              fleet-wide drop + another freeze cycle):"
    echo "             ${wrapper_cd} \\"
    echo "               'docker compose -f ${COMPOSE_FILE} --project-directory ${REPO_ROOT} up -d --force-recreate nats'"
    echo "              (a bare 'up -d' fails loudly since c6820ed; a value-identical config makes"
    echo "               a non-forced 'up -d' a silent no-op — --force-recreate is the verb)"
    echo "              Expect the entrypoint log: 'Processed: …accounts.conf.template -> …accounts.conf'."
    echo ""
    echo "  [R2a] wrong-credential REFUSED (gate-of-the-gate; a vacuous auth path invalidates R2/R3)."
    echo "  [R2 ] the NEW ${ACCOUNT} credential authenticates as nats user '${PROBE_USER}'"
    echo "        (quiet publish to '${PROBE_SUBJECT}', creds via env) + curl :8222/connz?auth=1"
    echo "        reconverges to baseline with zero Authorization Violations."
    echo "  [R3 ] the OLD credential is REFUSED (Authorization Violation) — a scratch client,"
    echo "        quiet shape, creds via env, never a creds-in-URL."
    echo "  [R4 ] every consumer copy below carries the new value, then each consumer restarts."
    emit_consumer_runbook
    echo ""
    echo "  [ROWS] Dated rows on PAGE-nats.md §9 (+ each consumer's page). The ⚠ 2026-07-30"
    echo "         exposure row closes on the RICH rotation."
}

# ---------------------------------------------------------------------------
# GATE R0 — the target container is running (LIVE only; inspect by name).
# ---------------------------------------------------------------------------
if [ "${LIVE}" = "true" ]; then
    if container_running; then
        echo "GATE R0 PASS: container '${CONTAINER}' is running"
    else
        die "GATE R0 FAIL: container '${CONTAINER}' is not running (nothing to rotate)"
    fi
else
    echo "GATE R0 N/A: no --live — this run performs no docker/nats/systemd action"
fi

# ---------------------------------------------------------------------------
# GATE RF — restart-freeze gate (accounts with a JetStream durable only).
# LIVE only; otherwise it is emitted in the runbook above.
# ---------------------------------------------------------------------------
restart_freeze_gate() {
    if [ "${LIVE}" != "true" ]; then
        echo "GATE RF RUNBOOK: no --live — the Ack-Pending-0 freeze gate is an OPERATOR step (printed below)"
        return 0
    fi
    if [ -z "${RF_DURABLE}" ]; then
        echo "GATE RF N/A: account ${ACCOUNT} has no JetStream durable — a recreate cannot freeze an ack for it"
        echo "  NOTE: the BROKER recreate itself is still gated on ${BROKER_FREEZE_STREAM}/${BROKER_FREEZE_DURABLE} Ack-Pending-0 (runbook)"
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
    # COACH BLOCKER FIX (2026-07-30): test the non-secret OLD_GIVEN flag —
    # `[ -n "${OLD_PW}" ]` here sat OUTSIDE the xtrace bracket and printed the
    # old credential verbatim under bash -x (the XTRACE LAW's own test missed
    # this line because the shipped harness never drives --live).
    [ "${OLD_GIVEN}" = "1" ] || die "GATE RF FAIL: need the CURRENT ${ACCOUNT} credential (on stdin) to query ${RF_STREAM}/${RF_DURABLE}, or pass --skip-freeze-check"
    local ip info
    ip="$(resolve_ip)"
    [ -n "${ip}" ] || die "GATE RF FAIL: cannot resolve the container IP to query the consumer"
    xtrace_off
    info="$(NATS_USER="${PROBE_USER}" NATS_PASSWORD="${OLD_PW}" \
        nats consumer info "${RF_STREAM}" "${RF_DURABLE}" \
        --server "nats://${ip}:4222" --timeout 5s 2>/dev/null || true)"
    xtrace_on
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
# Read the NEW password (stdin only) and the OLD password (optional).
# XTRACE LAW region: from here to the end, every secret touch is bracketed.
# ---------------------------------------------------------------------------
NEW_PW=""
OLD_PW=""
xtrace_off
if [ -t 0 ]; then
    read -r -s -p "NEW ${ACCOUNT}_NATS_PASSWORD: " NEW_PW; echo ""
    read -r -s -p "OLD password (empty to skip the R3 old-credential-dead gate): " OLD_PW; echo ""
else
    IFS= read -r NEW_PW || true
    IFS= read -r OLD_PW || true
fi
NEW_EMPTY=1; [ -z "${NEW_PW}" ] || NEW_EMPTY=0
NEW_CHARSET_OK=0
if [[ "${NEW_PW}" =~ ^[A-Za-z0-9]+$ ]]; then NEW_CHARSET_OK=1; fi
OLD_GIVEN=0; [ -z "${OLD_PW}" ] || OLD_GIVEN=1
xtrace_on

[ "${NEW_EMPTY}" = "0" ] || die "no NEW password on stdin"

# Charset guard (founding §5.2): config/URL-safe alphanumeric only, so the value
# is safe both in the NATS config and inside any URL. REGENERATE, do not widen —
# widening the charset would re-introduce the quoting hazards this closes.
[ "${NEW_CHARSET_OK}" = "1" ] || \
    die "NEW password has characters outside [A-Za-z0-9] — regenerate (e.g. openssl rand -hex 24), do not widen the charset"

# Run RF now that OLD_PW is known.
restart_freeze_gate

# ---------------------------------------------------------------------------
# SOURCE preflight — the authority file must exist and hold exactly one target.
# ---------------------------------------------------------------------------
if [ "${SOURCE_MODE}" = "plaintext" ]; then
    [ -f "${ENV_FILE}" ] || die "env-file not found: ${ENV_FILE} (DF-022: the broker plaintext .env is retired — use --source sops)"
    match_count="$(grep -c "^${VAR_NAME}=" "${ENV_FILE}" || true)"
    [ "${match_count}" = "1" ] || die "expected exactly one '${VAR_NAME}=' line in ${ENV_FILE}, found ${match_count}"
    echo "SOURCE PASS: plaintext ${ENV_FILE} holds exactly one '${VAR_NAME}=' line"
else
    sops_preflight
    [ -f "${SECRETS_ROOT}/${ENC_FILE}" ] || die "encrypted authority file not found: ${SECRETS_ROOT}/${ENC_FILE}"
    xtrace_off
    if ! sops_decrypt_into_DOTENV_IN "${ENC_FILE}"; then
        DOTENV_IN=""
        xtrace_on
        die "cannot decrypt ${ENC_FILE} from ${SECRETS_ROOT} (is this machine a recipient? is the age key readable?)"
    fi
    EDIT_KEY="${VAR_NAME}"
    dotenv_get_key
    VALUE_OUT=""
    broker_key_found="${VALUE_FOUND}"
    DOTENV_IN=""
    xtrace_on
    [ "${broker_key_found}" = "1" ] || die "'${VAR_NAME}' absent from ${ENC_FILE} — wrong authority file or map drift"
    echo "SOURCE PASS: ${SECRETS_ROOT}/${ENC_FILE} decrypts and carries '${VAR_NAME}' (value never displayed)"
fi

# R4 planning happens BEFORE any write, so a map-vs-estate drift aborts clean.
echo ""
echo "--- R4 consumer plan (${THIS_HOST} rows; sops mode only) ---"
if [ "${SOURCE_MODE}" != "sops" ]; then
    echo "  (plaintext source: consumer enc files are NOT touched by this run — runbook only)"
elif [ "${CONSUMER_SYNC}" != "true" ]; then
    echo "  (--no-consumer-sync: runbook only)"
else
    plan_consumers
    [ "${#CONSUMER_PLAN[@]}" -gt 0 ] || echo "  (no local consumer rows to apply for ${ACCOUNT})"
fi

# ---------------------------------------------------------------------------
# DRY-RUN — print the plan + the operator runbook and stop (no writes at all).
# ---------------------------------------------------------------------------
if [ "${EXECUTE}" != "true" ]; then
    echo ""
    echo "--- DRY-RUN PLAN (no changes made; re-run with --execute) ---"
    echo "  1. GATE R0 / GATE RF handled above."
    if [ "${SOURCE_MODE}" = "plaintext" ]; then
        echo "  2. WOULD atomically rewrite the single '${VAR_NAME}=' line in ${ENV_FILE} (mode preserved)."
    else
        echo "  2. WOULD sops -d ${ENC_FILE}, rewrite '${VAR_NAME}' IN MEMORY, and sops -e it back"
        echo "     (0600 plaintext window under ${RUNTIME_DIR} only, shredded by the EXIT trap; mode preserved)."
        echo "  3. WOULD re-sync + verify the ${#CONSUMER_PLAN[@]} planned consumer enc file(s) above (R4)."
    fi
    if [ "${LIVE}" = "true" ]; then
        if [ "${RESTART_MODE}" = "compose-recreate" ]; then
            echo "  4. WOULD recreate the container (OPERATOR path):"
            echo "       docker compose -f ${COMPOSE_FILE} --project-directory ${REPO_ROOT} up -d --force-recreate ${CONTAINER}"
        else
            echo "  4. WOULD signal the invoker to recreate '${CONTAINER}' (external mode), then wait for the new credential."
        fi
        echo "  5. WOULD run GATE R2a / R2 / R3 against the recreated broker."
    fi
    emit_broker_runbook
    print_checklist
    echo ""
    echo "DRY-RUN complete — no changes made."
    exit 0
fi

# ---------------------------------------------------------------------------
# EXECUTE — write the new value to the AUTHORITY source.
# ---------------------------------------------------------------------------
if [ "${SOURCE_MODE}" = "plaintext" ]; then
    # Atomic env-file edit (only the target line changes; mode preserved). The
    # NEW value is written via a pure-shell rewrite; it never touches argv.
    # RUNTIME PLAINTEXT LAW applies to THIS path too: the working copy is a 0600
    # temp on the caller's tmpfs, registered with the shred-trap. It is NEVER
    # created beside ${ENV_FILE} — that path is typically inside a git work tree,
    # mktemp's 0600 would then be widened to the source's (possibly 644) mode,
    # and a leftover would be un-gitignored and stageable by `git add -A`.
    old_mode="$(stat -c '%a' "${ENV_FILE}")"
    runtime_tmp; tmp_env="${RUNTIME_TMP_OUT}"; RUNTIME_TMP_OUT=""
    xtrace_off
    rewrote=0
    while IFS= read -r line || [ -n "${line}" ]; do
        case "${line}" in
            "${VAR_NAME}="*) printf '%s=%s\n' "${VAR_NAME}" "${NEW_PW}"; rewrote=1 ;;
            *)               printf '%s\n' "${line}" ;;
        esac
    done < "${ENV_FILE}" > "${tmp_env}"
    xtrace_on
    if [ "${rewrote}" != "1" ]; then
        shred -u -n 1 "${tmp_env}" 2>/dev/null || rm -f "${tmp_env}"
        die "internal: did not rewrite the '${VAR_NAME}=' line"
    fi
    # install(1), not mv: the temp lives on another filesystem (tmpfs) and must be
    # shredded, not moved. Mode is set explicitly from the source.
    install -m "${old_mode}" "${tmp_env}" "${ENV_FILE}"
    shred -u -n 1 "${tmp_env}" 2>/dev/null || rm -f "${tmp_env}"
    echo "GATE R1 PASS: '${VAR_NAME}' line updated in ${ENV_FILE} (mode ${old_mode} preserved)"
    echo "  NOTE: plaintext source — the sops estate (authority + consumer enc files) was NOT touched."
else
    xtrace_off
    sops_decrypt_into_DOTENV_IN "${ENC_FILE}" || { DOTENV_IN=""; xtrace_on; die "R1 FAIL: decrypt of ${ENC_FILE} failed"; }
    EDIT_KEY="${VAR_NAME}"; EDIT_MODE="plain"
    dotenv_rewrite_key
    r1_hits="${EDIT_HITS}"; r1_err="${EDIT_ERR}"
    if [ -n "${r1_err}" ] || [ "${r1_hits}" != "1" ]; then
        DOTENV_IN=""; DOTENV_OUT=""
        xtrace_on
        die "R1 FAIL: expected exactly one '${VAR_NAME}=' line in ${ENC_FILE} (rewrote ${r1_hits}) ${r1_err}"
    fi
    sops_encrypt_from_DOTENV_OUT "${ENC_FILE}"
    DOTENV_IN=""; DOTENV_OUT=""
    r1_vrc=0
    verify_enc_key "${ENC_FILE}" || r1_vrc=1
    DOTENV_IN=""
    xtrace_on
    [ "${r1_vrc}" = "0" ] || die "R1 VERIFY FAIL: ${ENC_FILE} does not carry the new value after re-encrypt"
    echo "GATE R1 PASS: '${VAR_NAME}' re-encrypted into ${SECRETS_ROOT}/${ENC_FILE} (ciphertext-only, mode preserved, verified by decrypt)"
fi

# ---------------------------------------------------------------------------
# R4 — consumer enc-file re-sync (sops mode; the planned rows only).
# ---------------------------------------------------------------------------
if [ "${SOURCE_MODE}" = "sops" ] && [ "${CONSUMER_SYNC}" = "true" ]; then
    echo ""
    echo "--- R4 consumer re-sync (${THIS_HOST}) ---"
    apply_consumers
    [ "${#CONSUMER_PLAN[@]}" -gt 0 ] || echo "  (nothing to apply)"
fi

# ---------------------------------------------------------------------------
# Deliver: the broker re-render. RUNBOOK unless --live.
# ---------------------------------------------------------------------------
if [ "${LIVE}" != "true" ]; then
    echo ""
    echo "SOURCES UPDATED. The live delivery is the OPERATOR's attended step — this run"
    echo "touched no container, no daemon and no broker."
    emit_broker_runbook
    print_checklist
    echo ""
    echo "=== ${ACCOUNT} source rotation complete (no live action taken) ==="
    exit 0
fi

if [ "${RESTART_MODE}" = "compose-recreate" ]; then
    # OPERATOR-ONLY attended path.
    echo "Recreating via compose (OPERATOR path)..."
    if [ "${SOURCE_MODE}" = "sops" ]; then
        ( cd "${SECRETS_ROOT}" && "${SOPS_BIN}" exec-env "${ENC_FILE}" \
            "docker compose -f '${COMPOSE_FILE}' --project-directory '${REPO_ROOT}' up -d --force-recreate '${CONTAINER}'" )
    else
        docker compose -f "${COMPOSE_FILE}" --project-directory "${REPO_ROOT}" up -d --force-recreate "${CONTAINER}"
    fi
else
    # external: the invoker performs the recreate; we gate+probe around it.
    echo ""
    echo "ROTATE-EXTERNAL-RECREATE-NOW"
    echo "  ACTION REQUIRED: recreate container '${CONTAINER}' now from the updated source."
    echo "  Waiting up to ${POLL_TIMEOUT}s for the new credential to become live..."
fi

xtrace_off
auth_rc=0
wait_for_new_auth "${NEW_PW}" || auth_rc=1
xtrace_on
if [ "${auth_rc}" = "0" ]; then
    echo "recreate observed: the broker accepted the new credential."
else
    die "the new credential never became live within ${POLL_TIMEOUT}s — recreate did not happen or failed"
fi

# ---------------------------------------------------------------------------
# GATE R2a — gate-of-the-gate: a WRONG password MUST be refused. If it is not,
# the auth path is vacuous and R2/R3 would prove nothing — abort.
# ---------------------------------------------------------------------------
xtrace_off
r2a_rc=0
probe_pub "${WRONG_PW}" || r2a_rc=$?
xtrace_on
[ "${r2a_rc}" != "${PROBE_UNAVAILABLE}" ] || \
    die "GATE R2a INCONCLUSIVE: the probe could not run (no container IP) — 'could not ask' is NOT 'correctly refused'; aborting before R2/R3"
[ "${r2a_rc}" != "0" ] || die "GATE R2a FAIL: a deliberately-wrong password AUTHENTICATED — auth path vacuous; aborting before R2/R3"
echo "GATE R2a PASS: the auth path refuses a wrong password"

# ---------------------------------------------------------------------------
# GATE R2 — the NEW password authenticates.
# ---------------------------------------------------------------------------
xtrace_off
r2_rc=0
probe_pub "${NEW_PW}" || r2_rc=$?
xtrace_on
[ "${r2_rc}" != "${PROBE_UNAVAILABLE}" ] || \
    die "GATE R2 INCONCLUSIVE: the probe could not run (no container IP) — no verdict"
[ "${r2_rc}" = "0" ] || die "GATE R2 FAIL: new password rejected — source and broker disagree; investigate before touching consumers"
echo "GATE R2 PASS: new password authenticates (user '${PROBE_USER}')"

# ---------------------------------------------------------------------------
# GATE R3 — the OLD password is refused (the property that makes it a rotation).
# ---------------------------------------------------------------------------
if [ "${OLD_GIVEN}" = "1" ]; then
    xtrace_off
    r3_rc=0
    probe_pub "${OLD_PW}" || r3_rc=$?
    xtrace_on
    [ "${r3_rc}" != "${PROBE_UNAVAILABLE}" ] || \
        die "GATE R3 INCONCLUSIVE: the probe could not run (no container IP) — no verdict"
    [ "${r3_rc}" != "0" ] || die "GATE R3 FAIL: the OLD password still authenticates — rotation did not take"
    echo "GATE R3 PASS: old credential is dead"
else
    echo "GATE R3 SKIPPED: no old password provided (pipe a second line / enter it at the prompt to enable)"
fi

echo ""
echo "=== Rotation complete for ${ACCOUNT} on '${CONTAINER}' ==="
emit_consumer_runbook
print_checklist
