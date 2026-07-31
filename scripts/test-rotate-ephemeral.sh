#!/usr/bin/env bash
# =======================================
# test-rotate-ephemeral.sh — isolation-fenced end-to-end test for
# rotate-nats-password.sh, driven against a THROWAWAY nats-server container
# that rotates its OWN scratch credential. Never touches a live service.
# =======================================
#
# ISOLATION FENCES (handoff §5 / guardrails):
#   - Standalone `docker run` ONLY — never `docker compose`, never the
#     nats-infrastructure compose project.
#   - Unique container name: nats-sec-eph-<runid>. NO published host ports
#     (-p is never used) — the live broker owns 4222/8222; we reach the scratch
#     container on its bridge IP.
#   - `trap ... EXIT` removes the container even on failure / early-stop.
#   - The scratch template is read from the PINNED SHA via `git show`
#     (read-only), never the working tree — Session A may have it mid-edit.
#   - All eight scratch passwords are generated at runtime (openssl rand -hex,
#     alnum-safe), written only to a chmod-600 env-file under the work root,
#     NEVER printed, NEVER committed, NEVER placed on any argv.
#
# WHAT IT ASSERTS:
#   (i)   dry-run makes NO mutation (env-file hash unchanged, docker ps unchanged)
#         + the shapes it EMITS work as written: the [FREEZE] step carries its
#         credentials as an env assignment prefix inside `sops exec-env`, and the
#         [RE-RENDER] step names the compose SERVICE (--compose-service), never
#         the --container value (the two 2026-07-31 live-rotation defects)
#   (ii)  --execute --restart-mode external rotates one scratch account and the
#         script's R2a / R2 / R3 gates all PASS (the harness performs the recreate
#         when the script signals ROTATE-EXTERNAL-RECREATE-NOW)
#   (iii) argv audit: no scratch password value ever appears in `ps -eo args`
#         (a hit is reported by LABEL only, never quoting the value)
#   (iv)  isolation: pre-existing containers (incl. ships-computer-nats) are
#         byte-identical before vs after
#   (v)   teardown: the container is GONE after EXIT — including a second,
#         deliberately-failed run proving the trap fires on failure
#
# 2026-07-30 (S1, DF-022): the rotation script gained the sops-aware dual mode.
# Docker/nats verbs are now behind an explicit `--live` (default DRY = runbook
# only), so BOTH invocations below pass `--live --source plaintext`. This file
# remains the PLAINTEXT-path proof and needs a live docker daemon + the scratch
# image; the sops path's proof is `test-rotate-sops-fixture.sh` (no daemons at
# all). Not re-run at the S1 landing — the S1 lane was fenced off docker.
#
# 2026-07-31 (rotate follow-up): the live rotations found a service-vs-container
# conflation on the compose-recreate path and a credential-less emitted [FREEZE]
# step. The EXECUTED compose-recreate path is proven in test-rotate-sops-fixture
# §(13c) under recording shims — deliberately NOT here: this harness's isolation
# fence bans `docker compose` outright (it would touch the real compose project),
# and that fence outranks the coverage. What this file adds is the EMITTED-shape
# check on the same dry-run it already performs. Also not re-run at that landing
# (the follow-up lane was fenced off docker as well).
#
# USAGE:
#   test-rotate-ephemeral.sh [--runid <id>] [--work-root <dir>]
#                            [--nats-repo <path>] [--pin <sha>]
# EXIT: 0 = all assertions passed · non-zero = at least one failed.
# =======================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROTATE="${SCRIPT_DIR}/rotate-nats-password.sh"
NATS_CLI="/usr/local/bin/nats"
IMAGE="nats-infrastructure-nats:latest"

RUNID="run-$(date +%s)"
WORK_ROOT="${SCRIPT_DIR}/undefined"
NATS_REPO="$(cd "${SCRIPT_DIR}/.." && pwd)"
PIN="f008c05"
REGISTER_PAGE="${SCRIPT_DIR}/../../ai-transition/docs/secrets-register/PAGE-nats.md"

while [ "$#" -gt 0 ]; do
    case "$1" in
        --runid)     RUNID="${2:?}"; shift 2 ;;
        --work-root) WORK_ROOT="${2:?}"; shift 2 ;;
        --nats-repo) NATS_REPO="${2:?}"; shift 2 ;;
        --pin)       PIN="${2:?}"; shift 2 ;;
        --register-page) REGISTER_PAGE="${2:?}"; shift 2 ;;
        *) echo "unknown argument: $1" >&2; exit 2 ;;
    esac
done

CNAME="nats-sec-eph-${RUNID}"
FAILCNAME="nats-sec-eph-${RUNID}-fail"
SCRATCH="${WORK_ROOT}/${RUNID}"
SCRATCH_ENV="${SCRATCH}/.env"
STORE_TAG="js-sec-eph-${RUNID}"

pass_n=0
fail_n=0
pass() { echo "  [PASS] $1"; pass_n=$((pass_n + 1)); }
fail() { echo "  [FAIL] $1"; fail_n=$((fail_n + 1)); }

# The scratch account under test (no JetStream durable → RF gate is N/A, so the
# fenced test never needs the freeze probe).
ACCOUNT="RICH"

# ---------------------------------------------------------------------------
# Teardown of the MAIN scratch container — fires even on failure / early-stop.
# ---------------------------------------------------------------------------
cleanup_main() { docker rm -f "${CNAME}" >/dev/null 2>&1 || true; }
trap cleanup_main EXIT

# ---------------------------------------------------------------------------
# Sanity: tools + image present (never pull, never touch the live broker).
# ---------------------------------------------------------------------------
[ -x "${ROTATE}" ]   || { echo "rotation script not executable: ${ROTATE}" >&2; exit 2; }
[ -x "${NATS_CLI}" ] || { echo "nats CLI not found: ${NATS_CLI}" >&2; exit 2; }
docker image inspect "${IMAGE}" >/dev/null 2>&1 || { echo "image absent (will NOT pull): ${IMAGE}" >&2; exit 2; }

echo "======================================="
echo "  test-rotate-ephemeral.sh   runid=${RUNID}"
echo "  container : ${CNAME}   (no published ports)"
echo "  work root : ${SCRATCH}"
echo "======================================="

# ---------------------------------------------------------------------------
# Build the scratch world.
# ---------------------------------------------------------------------------
mkdir -p "${SCRATCH}/config/accounts"

# Pinned template via git show (read-only); fall back to the working tree.
if git -C "${NATS_REPO}" show "${PIN}:config/accounts/accounts.conf.template" \
        > "${SCRATCH}/config/accounts/accounts.conf.template" 2>/dev/null; then
    echo "template: from ${PIN} (pinned, read-only)"
else
    cp "${NATS_REPO}/config/accounts/accounts.conf.template" \
       "${SCRATCH}/config/accounts/accounts.conf.template"
    echo "WARNING: could not read ${PIN}; used the working-tree template"
fi

# Minimal nats-server.conf modeled on the real one (stdout log; writable JS dir).
cat > "${SCRATCH}/config/nats-server.conf" <<EOF
server_name: "sec-eph-${RUNID}"
host: "0.0.0.0"
port: 4222
http: "0.0.0.0:8222"
max_payload: 1048576
jetstream {
    store_dir: "/tmp/${STORE_TAG}"
    max_mem: 64MB
    max_file: 256MB
}
logtime: true
debug: false
trace: false
include "accounts/accounts.conf"
EOF

# Generate all eight scratch passwords (alnum-safe hex). Values live ONLY in
# these shell vars + the chmod-600 env-file; never printed, committed, or argv'd.
gen() { openssl rand -hex 16; }
SCRATCH_ACCOUNTS="ADMIN RICH JAMES MARK FORGE FLEET_MEMORY GUARDKIT JARVIS"
umask 077
: > "${SCRATCH_ENV}"
declare -A SCRATCH_PW=()
for a in ${SCRATCH_ACCOUNTS}; do
    v="$(gen)"
    SCRATCH_PW["${a}"]="${v}"
    printf '%s_NATS_PASSWORD=%s\n' "${a}" "${v}" >> "${SCRATCH_ENV}"
done
chmod 600 "${SCRATCH_ENV}"
unset v

# Start the scratch container. Standalone run, no -p, bridge networking only.
run_scratch() {
    docker run -d --name "${CNAME}" \
        --env-file "${SCRATCH_ENV}" \
        -v "${SCRATCH}/config/nats-server.conf:/etc/nats/nats-server.conf:ro" \
        -v "${SCRATCH}/config/accounts:/etc/nats/config/accounts:ro" \
        "${IMAGE}" -c /etc/nats/nats-server.conf >/dev/null
}

resolve_ip() {
    docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "${CNAME}" 2>/dev/null || true
}

# Wait until user 'rich' with a given password authenticates (broker ready).
wait_ready() {
    local pw="$1" ip waited=0
    while [ "${waited}" -lt 40 ]; do
        ip="$(resolve_ip)"
        if [ -n "${ip}" ] && NATS_USER=rich NATS_PASSWORD="${pw}" \
                "${NATS_CLI}" pub probe.rich ready \
                --server "nats://${ip}:4222" --timeout 2s >/dev/null 2>&1; then
            return 0
        fi
        sleep 2
        waited=$((waited + 2))
    done
    return 1
}

# Snapshot of every OTHER container (id+name), for the isolation audit.
other_containers() {
    docker ps -a --format '{{.ID}} {{.Names}}' | grep -v "nats-sec-eph-${RUNID}" | sort || true
}
SHIPS_ID_BEFORE="$(docker inspect -f '{{.Id}}' ships-computer-nats 2>/dev/null || echo none)"
SHIPS_START_BEFORE="$(docker inspect -f '{{.State.StartedAt}}' ships-computer-nats 2>/dev/null || echo none)"
PS_BEFORE="$(other_containers)"

run_scratch
if wait_ready "${SCRATCH_PW[RICH]}"; then
    echo "scratch broker ready."
else
    fail "scratch broker did not become ready"
    exit 1
fi

# ---------------------------------------------------------------------------
# Background argv sampler (phase iii feeds off this) — captures `ps -eo args`.
# ---------------------------------------------------------------------------
PSDUMP="${SCRATCH}/ps-argv.dump"
: > "${PSDUMP}"
SAMPLING=1
sampler() { while [ -f "${SCRATCH}/.sampling" ]; do ps -eo args >> "${PSDUMP}" 2>/dev/null || true; sleep 0.2; done; }
touch "${SCRATCH}/.sampling"
sampler & SAMPLER_PID=$!
stop_sampler() { [ "${SAMPLING}" = "1" ] || return 0; SAMPLING=0; rm -f "${SCRATCH}/.sampling"; wait "${SAMPLER_PID}" 2>/dev/null || true; }

# =======================================
# Phase (i) — dry-run makes NO mutation.
# =======================================
echo ""
echo "--- Phase (i): dry-run makes no mutation ---"
HASH_BEFORE="$(sha256sum "${SCRATCH_ENV}" | awk '{print $1}')"
PS_DRY_BEFORE="$(docker ps -a --format '{{.ID}}' | sort)"
DRYLOG="${SCRATCH}/dry.log"
DRY_NEW="$(gen)"   # alnum, satisfies the charset guard
# --compose-service is passed a DISTINCTIVE value so the emitted-shape checks
# below can tell a plumbed-through service name from the container name. It
# changes nothing this run does: --restart-mode stays `external`, so no compose
# verb is ever reached (the isolation fence bans `docker compose` here).
if printf '%s\n%s\n' "${DRY_NEW}" "${SCRATCH_PW[RICH]}" | \
        "${ROTATE}" --account "${ACCOUNT}" --live --container "${CNAME}" \
        --compose-service scratch-svc \
        --source plaintext --env-file "${SCRATCH_ENV}" --register-page "${REGISTER_PAGE}" \
        > "${DRYLOG}" 2>&1; then
    if grep -q "DRY-RUN complete" "${DRYLOG}"; then
        pass "dry-run exited 0 and reported DRY-RUN complete"
    else
        fail "dry-run output missing 'DRY-RUN complete'"
    fi
else
    fail "dry-run exited non-zero"
fi
if grep -q "GATE R0 PASS" "${DRYLOG}"; then pass "dry-run ran GATE R0"; else fail "dry-run missing GATE R0"; fi
HASH_AFTER_DRY="$(sha256sum "${SCRATCH_ENV}" | awk '{print $1}')"
if [ "${HASH_BEFORE}" = "${HASH_AFTER_DRY}" ]; then pass "env-file unchanged by dry-run"; else fail "env-file CHANGED during dry-run"; fi
PS_DRY_AFTER="$(docker ps -a --format '{{.ID}}' | sort)"
if [ "${PS_DRY_BEFORE}" = "${PS_DRY_AFTER}" ]; then pass "no docker state change during dry-run"; else fail "docker state changed during dry-run"; fi

# --- the EMITTED runbook shapes (2026-07-31 defects 1 + 2) -------------------
# A runbook step this script prints is a step Rich pastes into a live attended
# window: it must work AS WRITTEN, and it must obey the same creds laws as an
# executed one.
if grep -Fq -- "'NATS_USER=forge NATS_PASSWORD=\"\$FORGE_NATS_PASSWORD\" nats consumer info PIPELINE forge-serve" "${DRYLOG}"; then
    pass "emitted [FREEZE] step carries creds as an env assignment prefix inside sops exec-env"
else
    fail "emitted [FREEZE] step has no credentials — as written it dies with Authorization Violation"
fi
if grep -Fq -- "up -d --force-recreate scratch-svc'" "${DRYLOG}"; then
    pass "--compose-service reaches the emitted recreate line (compose SERVICE key)"
else
    fail "--compose-service did not reach the emitted recreate line"
fi
if grep -F -- '--force-recreate' "${DRYLOG}" | grep -Fq -- "${CNAME}"; then
    fail "the CONTAINER name was emitted on a compose --force-recreate line (service/container conflation)"
else
    pass "no emitted compose --force-recreate line carries the container name"
fi
if grep -Fq "probe     : publish to 'probe.rich'" "${DRYLOG}"; then
    pass "the run announces its probe subject (probe.rich — matched by no stream filter)"
else
    fail "the run did not announce its probe subject"
fi

# =======================================
# Phase (ii) — execute (external): harness performs the recreate on signal.
# =======================================
echo ""
echo "--- Phase (ii): execute --restart-mode external; R2a/R2/R3 ---"
EXEC_NEW="$(gen)"
EXEC_OLD="${SCRATCH_PW[RICH]}"
ROTLOG="${SCRATCH}/exec.log"

# Launch the rotation in the background; feed NEW + OLD via a stdin pipe.
printf '%s\n%s\n' "${EXEC_NEW}" "${EXEC_OLD}" | \
    "${ROTATE}" --execute --live --restart-mode external \
    --account "${ACCOUNT}" --container "${CNAME}" \
    --source plaintext --env-file "${SCRATCH_ENV}" --register-page "${REGISTER_PAGE}" \
    --poll-timeout 60 > "${ROTLOG}" 2>&1 &
ROT_PID=$!

# Wait for the script to finish the env edit and signal the recreate.
waited=0
until grep -q "ROTATE-EXTERNAL-RECREATE-NOW" "${ROTLOG}" 2>/dev/null; do
    if ! kill -0 "${ROT_PID}" 2>/dev/null; then break; fi
    sleep 1; waited=$((waited + 1))
    [ "${waited}" -lt 40 ] || { fail "rotation never signalled the recreate"; break; }
done

# The script writes the env BEFORE signalling — confirm the new value landed.
if grep -q "^${ACCOUNT}_NATS_PASSWORD=${EXEC_NEW}\$" "${SCRATCH_ENV}"; then
    pass "env-file rewritten with the new value before the recreate signal"
else
    fail "env-file not updated before the recreate signal"
fi

# Perform the recreate: rm -f + identical run with the (now updated) env-file.
docker rm -f "${CNAME}" >/dev/null 2>&1 || true
run_scratch

# Wait for the rotation script to finish; capture its exit code.
RC=0; wait "${ROT_PID}" || RC=$?
if [ "${RC}" = "0" ]; then pass "rotation script exited 0"; else fail "rotation script exited ${RC}"; fi
for g in "GATE R2a PASS" "GATE R2 PASS" "GATE R3 PASS"; do
    if grep -q "${g}" "${ROTLOG}"; then pass "observed: ${g}"; else fail "missing: ${g}"; fi
done

# =======================================
# Phase (iii) — argv audit: no scratch secret ever appears in `ps -eo args`.
# =======================================
echo ""
echo "--- Phase (iii): argv audit (report by LABEL only) ---"
stop_sampler
argv_hit=0
check_argv() {  # $1 = label, $2 = value (never printed)
    if grep -Fq -- "$2" "${PSDUMP}"; then echo "  [LEAK] argv exposed: $1"; argv_hit=$((argv_hit + 1)); fi
}
check_argv "new-password" "${EXEC_NEW}"
check_argv "old-password" "${EXEC_OLD}"
check_argv "dry-run-new-password" "${DRY_NEW}"
for a in ${SCRATCH_ACCOUNTS}; do check_argv "scratch:${a}" "${SCRATCH_PW[$a]}"; done
if [ "${argv_hit}" = "0" ]; then
    pass "no scratch password value found in any sampled argv (${PSDUMP##*/})"
else
    fail "${argv_hit} argv exposure(s) — see LEAK lines above (values NOT quoted)"
fi

# =======================================
# Phase (iv) — isolation: pre-existing containers untouched.
# =======================================
echo ""
echo "--- Phase (iv): isolation audit ---"
SHIPS_ID_AFTER="$(docker inspect -f '{{.Id}}' ships-computer-nats 2>/dev/null || echo none)"
PS_AFTER="$(other_containers)"
if [ "${SHIPS_ID_BEFORE}" = "${SHIPS_ID_AFTER}" ]; then
    pass "ships-computer-nats same container id, untouched"
else
    fail "ships-computer-nats id changed (${SHIPS_ID_BEFORE} -> ${SHIPS_ID_AFTER})"
fi
if [ "${SHIPS_ID_AFTER}" != "none" ] && [ "$(docker inspect -f '{{.State.Running}}' ships-computer-nats 2>/dev/null)" = "true" ]; then
    pass "ships-computer-nats still Up"
else
    fail "ships-computer-nats not Up after the run"
fi
SHIPS_START_AFTER="$(docker inspect -f '{{.State.StartedAt}}' ships-computer-nats 2>/dev/null || echo none)"
if [ "${SHIPS_START_BEFORE}" = "${SHIPS_START_AFTER}" ]; then
    pass "ships-computer-nats StartedAt unchanged (this run never restarted it)"
else
    fail "ships-computer-nats StartedAt changed during this run (${SHIPS_START_BEFORE} -> ${SHIPS_START_AFTER}) — external actor"
fi
if [ "${PS_BEFORE}" = "${PS_AFTER}" ]; then
    pass "all pre-existing containers identical before vs after"
else
    fail "the set of pre-existing containers changed"
fi

# =======================================
# Phase (v) — teardown: main container gone after removal; trap fires on failure.
# =======================================
echo ""
echo "--- Phase (v): teardown audit ---"
cleanup_main
if docker ps -a --format '{{.Names}}' | grep -qx "${CNAME}"; then
    fail "main container ${CNAME} still present after teardown"
else
    pass "main container ${CNAME} is gone after teardown"
fi

# Induced-failure run: a BACKGROUND subshell with its OWN EXIT trap. Running it
# in the background (not on the left of `||`/`if`) keeps `set -e` ACTIVE inside,
# so the `false` genuinely aborts the subshell mid-test and the EXIT trap must
# do the teardown. `wait ... || true` collects the non-zero without aborting us.
induced_failure_proof() {
    (
        set -e
        trap 'docker rm -f "'"${FAILCNAME}"'" >/dev/null 2>&1 || true' EXIT
        docker run -d --name "${FAILCNAME}" \
            --env-file "${SCRATCH_ENV}" \
            -v "${SCRATCH}/config/nats-server.conf:/etc/nats/nats-server.conf:ro" \
            -v "${SCRATCH}/config/accounts:/etc/nats/config/accounts:ro" \
            "${IMAGE}" -c /etc/nats/nats-server.conf >/dev/null
        false                       # deliberate mid-test failure (set -e aborts here)
        echo "UNREACHABLE — set -e failed to abort"
    ) &
    local sub=$!
    wait "${sub}" || true
}
induced_failure_proof
if docker ps -a --format '{{.Names}}' | grep -qx "${FAILCNAME}"; then
    fail "induced-failure trap did NOT remove ${FAILCNAME}"
    docker rm -f "${FAILCNAME}" >/dev/null 2>&1 || true
else
    pass "induced-failure trap removed ${FAILCNAME} (teardown fires on failure)"
fi

# ---------------------------------------------------------------------------
echo ""
echo "======================================="
echo "  RESULTS: ${pass_n} passed, ${fail_n} failed"
echo "======================================="
[ "${fail_n}" -eq 0 ]
