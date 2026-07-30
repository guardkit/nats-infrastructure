#!/usr/bin/env bash
# =======================================
# test-rotate-sops-fixture.sh — the S1 coach gate for rotate-nats-password.sh's
# sops-aware mode. Drives the REAL script against a SYNTHETIC secrets root built
# at run time in a temp dir, with age identities generated at run time.
# =======================================
#
# SPEC: docs/ways-of-working/secrets-close-out-and-rotation-handoff.md §3-S1 +
#       §4 "S1 coach": fixture rotation end-to-end incl. consumer re-sync · no
#       plaintext at rest · display/argv clean · the freeze gate encoded in the
#       script path.
#
# ISOLATION FENCES (binding — this harness must be safe to run any time):
#   - It NEVER reads or writes the real secrets root (~/.config/fleet-secrets on
#     any box). Every invocation passes --secrets-root <fixture>.
#   - It NEVER touches docker, the nats CLI, systemd, ssh or the broker. That is
#     PROVEN, not assumed: a shim dir is prepended to PATH whose `docker`,
#     `docker-compose`, `nats`, `systemctl` and `ssh` record any invocation to a
#     log and exit non-zero. The log must stay EMPTY.
#   - Nothing it creates is ever committed: everything lives under a mktemp -d
#     work root, shredded + removed by an EXIT trap.
#   - Synthetic secret values are generated at run time (openssl rand -hex,
#     alnum so they satisfy the script's charset guard), never printed, never
#     placed on any argv (they travel stdin -> the script's shell vars).
#
# WHAT IT ASSERTS:
#   (0)  preflight: sops + age-keygen present; the shim PATH is in force
#   (1)  DRY (no --execute): zero mutation, and the OPERATOR RUNBOOK carries the
#        Ack-Pending-0 freeze gate + the ONE --force-recreate broker re-render +
#        R2a/R2/R3 + the R4 consumer map (local AND remote rows)
#   (2)  EXECUTE RICH end-to-end: broker authority enc rewritten + BOTH local
#        `rich` consumer enc files re-synced; old value dead everywhere; every
#        other key byte-identical
#   (3)  EXECUTE FLEET_MEMORY: the URL-embedded members (3 files) get ONLY the
#        password segment swapped — user/host/port/scheme preserved
#   (4)  EXECUTE JARVIS: the systemd consumer file's plain key re-synced
#   (5)  opt rows: --this-host nodeb, key absent -> SKIP, exit 0, no mutation
#   (6)  two-phase safety: a REQUIRED consumer key missing aborts in the PLAN
#        phase with the authority file still untouched
#   (6b) trap proof: a failing `sops -e` leaves NO plaintext window in /run/user
#        and does not half-write the destination
#   (7)  zero plaintext at rest: no secret value anywhere under the fixture root,
#        every file still sops-ciphertext, no /run/user temp survives
#   (8)  `bash -x` (set -x) audit: no secret value in the trace
#   (9)  argv audit: no secret value in any sampled `ps -eo args`
#   (10) display audit: no secret value on the script's stdout/stderr
#   (11) non-recipient refusal (the R2a analogue at the sops layer)
#   (12) flag fences: --live without --container, and --container without --live
#
# USAGE: test-rotate-sops-fixture.sh [--keep]
# EXIT: 0 = all assertions passed · non-zero = at least one failed.
# =======================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROTATE="${SCRIPT_DIR}/rotate-nats-password.sh"
SOPS_BIN="${SOPS_BIN:-/home/richardwoollcott/.local/bin/sops}"
AGE_KEYGEN="${AGE_KEYGEN:-/home/richardwoollcott/.local/bin/age-keygen}"
REGISTER_PAGE="${SCRIPT_DIR}/../../ai-transition/docs/secrets-register/PAGE-nats.md"
KEEP="false"

while [ "$#" -gt 0 ]; do
    case "$1" in
        --keep) KEEP="true"; shift ;;
        *) echo "unknown argument: $1" >&2; exit 2 ;;
    esac
done

pass_n=0
fail_n=0
pass() { echo "  [PASS] $1"; pass_n=$((pass_n + 1)); }
fail() { echo "  [FAIL] $1"; fail_n=$((fail_n + 1)); }
# Assertion helpers (kept as if/else so `A && B || C` never appears — the
# harness must be shellcheck-clean down to info level).
chk()   { if [ "$1" = "0" ]; then pass "$2"; else fail "$3"; fi; }      # $1 = rc
nchk()  { if [ "$1" != "0" ]; then pass "$2"; else fail "$3"; fi; }     # $1 = rc, expect non-zero
same()  { if [ "$1" = "$2" ]; then pass "$3"; else fail "$4"; fi; }     # values NEVER printed
has()   { if grep -Fq -- "$2" "$1"; then pass "$3"; else fail "$4"; fi; }

WORK="$(mktemp -d "${TMPDIR:-/tmp}/rotate-sops-fixture.XXXXXX")"
cleanup() {
    if [ "${KEEP}" = "true" ]; then
        echo "(--keep) fixture left at ${WORK}"
        return 0
    fi
    find "${WORK}" -type f -exec shred -u -n 1 {} + 2>/dev/null || true
    rm -rf "${WORK}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM
chmod 700 "${WORK}"

echo "======================================="
echo "  test-rotate-sops-fixture.sh"
echo "  work root : ${WORK}   (synthetic; shredded on exit)"
echo "  real secrets roots are NEVER touched"
echo "======================================="

# ---------------------------------------------------------------------------
# (0) Preflight + the no-daemon shim.
# ---------------------------------------------------------------------------
echo ""
echo "--- (0) preflight ---"
[ -x "${ROTATE}" ]     || { echo "rotation script not executable: ${ROTATE}" >&2; exit 2; }
[ -x "${SOPS_BIN}" ]   || { echo "sops not found: ${SOPS_BIN}" >&2; exit 2; }
[ -x "${AGE_KEYGEN}" ] || { echo "age-keygen not found: ${AGE_KEYGEN}" >&2; exit 2; }

SHIM="${WORK}/shim"
SHIM_LOG="${WORK}/forbidden-invocations.log"
mkdir -p "${SHIM}"
: > "${SHIM_LOG}"
for verb in docker docker-compose nats systemctl ssh; do
    cat > "${SHIM}/${verb}" <<EOF
#!/usr/bin/env bash
echo "FORBIDDEN: ${verb} \$*" >> "${SHIM_LOG}"
exit 97
EOF
    chmod 755 "${SHIM}/${verb}"
done
export PATH="${SHIM}:${PATH}"
if [ "$(command -v docker)" = "${SHIM}/docker" ]; then
    pass "shim PATH in force — docker/nats/systemctl/ssh cannot be reached for real"
else
    fail "shim PATH NOT in force"
fi

# ---------------------------------------------------------------------------
# Age identities (generated at run time — nothing pre-existing is read).
# ---------------------------------------------------------------------------
mkdir -p "${WORK}/age"
chmod 700 "${WORK}/age"
"${AGE_KEYGEN}" -o "${WORK}/age/main.txt"    >/dev/null 2>&1
"${AGE_KEYGEN}" -o "${WORK}/age/escrow.txt"  >/dev/null 2>&1
"${AGE_KEYGEN}" -o "${WORK}/age/outsider.txt" >/dev/null 2>&1
chmod 600 "${WORK}/age"/*.txt
# `age-keygen -y` derives the pubkey FROM THE BLOB — the truth (custody lesson).
PUB_MAIN="$("${AGE_KEYGEN}" -y "${WORK}/age/main.txt")"
PUB_ESCROW="$("${AGE_KEYGEN}" -y "${WORK}/age/escrow.txt")"
export SOPS_AGE_KEY_FILE="${WORK}/age/main.txt"

# ---------------------------------------------------------------------------
# Synthetic values. Alnum (the script's charset guard) — never printed.
# ---------------------------------------------------------------------------
gen() { openssl rand -hex 16; }
OLD_RICH="$(gen)";  NEW_RICH="$(gen)"
OLD_FM="$(gen)";    NEW_FM="$(gen)"
OLD_JARVIS="$(gen)"; NEW_JARVIS="$(gen)"
OLD_FORGE="$(gen)"
OLD_ADMIN="$(gen)"
OLD_GUARDKIT="$(gen)"
ALL_VALUES=("${OLD_RICH}" "${NEW_RICH}" "${OLD_FM}" "${NEW_FM}" "${OLD_JARVIS}" \
            "${NEW_JARVIS}" "${OLD_FORGE}" "${OLD_ADMIN}" "${OLD_GUARDKIT}")

# ---------------------------------------------------------------------------
# Build a synthetic secrets root. $1 = path · $2 = "ok" | "break-req"
# (break-req omits NATS_PASSWORD from the REQUIRED specialist consumer file).
# Per-PREFIX creation rules with NO catch-all: encryption of a /run/user temp
# can therefore only succeed if the script's --filename-override really maps to
# the DESTINATION path (that is the point of the shape).
# ---------------------------------------------------------------------------
make_root() {
    local root="$1" variant="${2:-ok}" f
    mkdir -p "${root}/nats" "${root}/slack-jarvis" "${root}/study-tutor" "${root}/fleet-memory-pg"
    chmod 700 "${root}"
    cat > "${root}/.sops.yaml" <<EOF
creation_rules:
  - path_regex: ^nats/.*\.enc\.env$
    age: ${PUB_MAIN},${PUB_ESCROW}
  - path_regex: ^slack-jarvis/.*\.enc\.env$
    age: ${PUB_MAIN},${PUB_ESCROW}
  - path_regex: ^study-tutor/.*\.enc\.env$
    age: ${PUB_MAIN},${PUB_ESCROW}
  - path_regex: ^fleet-memory-pg/.*\.enc\.env$
    age: ${PUB_MAIN},${PUB_ESCROW}
EOF
    umask 077

    # Broker authority — all eight, no inline comments (exec-env parser law).
    {
        printf 'ADMIN_NATS_PASSWORD=%s\n' "${OLD_ADMIN}"
        printf 'RICH_NATS_PASSWORD=%s\n' "${OLD_RICH}"
        printf 'JAMES_NATS_PASSWORD=%s\n' "$(gen)"
        printf 'MARK_NATS_PASSWORD=%s\n' "$(gen)"
        printf 'FORGE_NATS_PASSWORD=%s\n' "${OLD_FORGE}"
        printf 'FLEET_MEMORY_NATS_PASSWORD=%s\n' "${OLD_FM}"
        printf 'GUARDKIT_NATS_PASSWORD=%s\n' "${OLD_GUARDKIT}"
        printf 'JARVIS_NATS_PASSWORD=%s\n' "${OLD_JARVIS}"
    } > "${root}/nats/broker.enc.env"

    # rich consumers (plain fields).
    if [ "${variant}" = "break-req" ]; then
        printf 'NATS_USER=rich\nOPENAI_API_KEY=sk-fixture-dead\n' > "${root}/nats/specialist-agent.enc.env"
    else
        printf 'NATS_USER=rich\nNATS_PASSWORD=%s\nOPENAI_API_KEY=sk-fixture-dead\n' \
            "${OLD_RICH}" > "${root}/nats/specialist-agent.enc.env"
    fi
    printf 'NATS_USER=rich\nNATS_PASSWORD=%s\nSTUDY_TUTOR_PG_DSN=postgresql://st:fixturepw@127.0.0.1:5432/st\n' \
        "${OLD_RICH}" > "${root}/study-tutor/study-tutor-root.enc.env"

    # Node B rows (opt): present but WITHOUT the rich credential — the SKIP case.
    printf 'HTTP_PORT=8100\nSTUDY_TUTOR_HTTP_TOKENS={}\n' > "${root}/study-tutor/http-env.enc.env"
    printf 'HTTP_PORT=8101\nSTUDY_TUTOR_AUTH_MODE=oidc\n' > "${root}/study-tutor/http-env-kc.enc.env"

    # URL-embedded members.
    printf 'FORGE_NATS_URL=nats://forge:%s@127.0.0.1:4222\nFORGE_LOG_LEVEL=info\n' \
        "${OLD_FORGE}" > "${root}/nats/forge-nats.enc.env"
    printf 'FLEET_MEMORY_NATS_URL=nats://fleet-memory:%s@127.0.0.1:4222\nFLEET_MEMORY_PG_DSN=postgresql://fm:fixturepw@127.0.0.1:5432/fm\n' \
        "${OLD_FM}" > "${root}/fleet-memory-pg/relay-env-deploy.enc.env"
    printf 'FLEET_MEMORY_NATS_URL=nats://fleet-memory:%s@127.0.0.1:4222\nFLEET_MEMORY_EMBED_URL=http://127.0.0.1:8080\n' \
        "${OLD_FM}" > "${root}/fleet-memory-pg/fleet-memory-root.enc.env"
    # guardkit copy: URL member for FLEET_MEMORY, and NO GUARDKIT_NATS_PASSWORD
    # (PAGE-nats §8 DISCOVERY — the 'opt' SKIP path).
    printf 'FLEET_MEMORY_NATS_URL=nats://fleet-memory:%s@127.0.0.1:4222\nGOOGLE_API_KEY=fixture-dead\n' \
        "${OLD_FM}" > "${root}/fleet-memory-pg/guardkit.enc.env"

    # jarvis (systemd consumer, clean fields).
    printf 'JARVIS_NATS_URL=nats://127.0.0.1:4222\nJARVIS_NATS_USER=jarvis\nJARVIS_NATS_PASSWORD=%s\n' \
        "${OLD_JARVIS}" > "${root}/slack-jarvis/jarvis.enc.env"

    while IFS= read -r f; do
        chmod 600 "${f}"
        ( cd "${root}" && "${SOPS_BIN}" -e -i --input-type dotenv --output-type dotenv "${f#"${root}"/}" )
    done < <(find "${root}" -name '*.enc.env' -type f | sort)
}

# Decrypt one fixture file to stdout (test-side helper; values stay in memory).
dec() { ( cd "$1" && "${SOPS_BIN}" -d --input-type dotenv --output-type dotenv "$2" ); }

# Value of KEY in a fixture file, without ever printing it to the terminal.
val_of() { dec "$1" "$2" | awk -F= -v k="$3" '$1 == k { sub(/^[^=]*=/, ""); print; exit }'; }

hash_root() { find "$1" -name '*.enc.env' -type f -exec sha256sum {} + | sort; }

# Assert a value does NOT appear anywhere under a root (report by LABEL only).
assert_absent_under() {  # $1 root · $2 label · $3 value
    if grep -rFq -- "$3" "$1" 2>/dev/null; then
        fail "PLAINTEXT AT REST under $1 — $2 (value not quoted)"
    else
        pass "no plaintext at rest under $(basename "$1") — $2"
    fi
}

ROOT="${WORK}/fleet-secrets"
make_root "${ROOT}" ok
echo "synthetic root built: $(find "${ROOT}" -name '*.enc.env' | wc -l) encrypted files"

# ---------------------------------------------------------------------------
# (11) non-recipient refusal — the R2a analogue at the sops layer.
# ---------------------------------------------------------------------------
echo ""
echo "--- (11) non-recipient refusal (R2a analogue) ---"
out_rc=0
SOPS_AGE_KEY_FILE="${WORK}/age/outsider.txt" \
    "${SOPS_BIN}" -d --input-type dotenv --output-type dotenv "${ROOT}/nats/broker.enc.env" \
    >/dev/null 2>&1 || out_rc=$?
if [ "${out_rc}" != "0" ]; then
    pass "a non-recipient identity CANNOT decrypt the fixture ciphertext (rc ${out_rc})"
else
    fail "a non-recipient identity decrypted the ciphertext — least-recipient broken"
fi

# ---------------------------------------------------------------------------
# (12) flag fences.
# ---------------------------------------------------------------------------
echo ""
echo "--- (12) flag fences ---"
fence_rc=0
printf '%s\n\n' "$(gen)" | "${ROTATE}" --account RICH --live >/dev/null 2>&1 || fence_rc=$?
nchk "${fence_rc}" "--live without --container is refused" "--live without --container was accepted"
fence_rc=0
printf '%s\n\n' "$(gen)" | "${ROTATE}" --account RICH --container some-box >/dev/null 2>&1 || fence_rc=$?
nchk "${fence_rc}" "--container without --live is refused" "--container without --live was accepted"

# ---------------------------------------------------------------------------
# Invocation helper. Secrets travel STDIN only (never argv).
# ---------------------------------------------------------------------------
run_rotate() {  # $1 log · $2 new · $3 old · rest: args
    local log="$1" new="$2" old="$3"; shift 3
    printf '%s\n%s\n' "${new}" "${old}" | \
        "${ROTATE}" --secrets-root "${ROOT}" --sops-bin "${SOPS_BIN}" \
        --source sops --register-page "${REGISTER_PAGE}" "$@" > "${log}" 2>&1
}

# ---------------------------------------------------------------------------
# (1) DRY — zero mutation + the runbook content.
# ---------------------------------------------------------------------------
echo ""
echo "--- (1) DRY run: zero mutation + operator runbook ---"
HASH_BEFORE="$(hash_root "${ROOT}")"
DRYLOG="${WORK}/dry.log"
dry_rc=0
run_rotate "${DRYLOG}" "${NEW_RICH}" "${OLD_RICH}" --account RICH || dry_rc=$?
chk "${dry_rc}" "dry run exited 0" "dry run exited ${dry_rc}"
same "$(hash_root "${ROOT}")" "${HASH_BEFORE}" "no enc file mutated by the dry run" "an enc file CHANGED during the dry run"
for needle in \
    "GATE R0 N/A" \
    "DRY-RUN complete" \
    "OPERATOR RUNBOOK" \
    "[FREEZE] Ack-Pending-0 gate" \
    "nats consumer info PIPELINE forge-serve" \
    "up -d --force-recreate nats" \
    "[R2a] wrong-credential REFUSED" \
    "[R3 ] the OLD credential is REFUSED" \
    "R4 CONSUMER MAP for RICH" ; do
    if grep -Fq -- "${needle}" "${DRYLOG}"; then pass "runbook carries: ${needle}"; else fail "runbook MISSING: ${needle}"; fi
done
if grep -Fq "R4 plan: APPLY nats/specialist-agent.enc.env" "${DRYLOG}" && \
   grep -Fq "R4 plan: APPLY study-tutor/study-tutor-root.enc.env" "${DRYLOG}"; then
    pass "dry plan names BOTH local rich consumer files"
else
    fail "dry plan missing a local rich consumer file"
fi
if grep -Fq "REMOTE — runbook only" "${DRYLOG}"; then
    pass "Node B rows are emitted REMOTE/runbook-only (the script never SSHes)"
else
    fail "Node B rows not marked remote-only"
fi

# ---------------------------------------------------------------------------
# (2) EXECUTE RICH — authority + both local consumers, end to end.
# ---------------------------------------------------------------------------
echo ""
echo "--- (2) EXECUTE RICH: old -> new across authority + consumers ---"
EXECLOG="${WORK}/exec-rich.log"
exec_rc=0
run_rotate "${EXECLOG}" "${NEW_RICH}" "${OLD_RICH}" --account RICH --execute || exec_rc=$?
chk "${exec_rc}" "RICH rotation exited 0" "RICH rotation exited ${exec_rc}"
if [ "${exec_rc}" != "0" ]; then sed -n '1,60p' "${EXECLOG}"; fi
has "${EXECLOG}" "GATE R1 PASS" "GATE R1 PASS (authority re-encrypted + verified)" "no GATE R1 PASS"
for f in nats/specialist-agent.enc.env study-tutor/study-tutor-root.enc.env; do
    if grep -Fq "R4 SYNCED + VERIFIED: ${f}" "${EXECLOG}"; then pass "R4 synced+verified: ${f}"; else fail "R4 did not sync ${f}"; fi
done
same "$(val_of "${ROOT}" nats/broker.enc.env RICH_NATS_PASSWORD)" "${NEW_RICH}" \
    "broker authority RICH_NATS_PASSWORD == NEW" "broker authority did not take the new value"
same "$(val_of "${ROOT}" nats/specialist-agent.enc.env NATS_PASSWORD)" "${NEW_RICH}" \
    "specialist-agent NATS_PASSWORD == NEW" "specialist-agent not re-synced"
same "$(val_of "${ROOT}" study-tutor/study-tutor-root.enc.env NATS_PASSWORD)" "${NEW_RICH}" \
    "study-tutor root NATS_PASSWORD == NEW" "study-tutor root not re-synced"
same "$(val_of "${ROOT}" nats/specialist-agent.enc.env NATS_USER)" "rich" \
    "specialist-agent NATS_USER untouched" "specialist-agent NATS_USER changed"
same "$(val_of "${ROOT}" nats/specialist-agent.enc.env OPENAI_API_KEY)" "sk-fixture-dead" \
    "passenger key in the same file untouched" "passenger key changed"
same "$(val_of "${ROOT}" nats/broker.enc.env ADMIN_NATS_PASSWORD)" "${OLD_ADMIN}" \
    "other broker members untouched (ADMIN)" "another broker member changed"
assert_absent_under "${ROOT}" "OLD rich value" "${OLD_RICH}"
assert_absent_under "${ROOT}" "NEW rich value" "${NEW_RICH}"

# ---------------------------------------------------------------------------
# (3) EXECUTE FLEET_MEMORY — the URL-embedded members.
# ---------------------------------------------------------------------------
echo ""
echo "--- (3) EXECUTE FLEET_MEMORY: URL password segment only ---"
FMLOG="${WORK}/exec-fm.log"
fm_rc=0
run_rotate "${FMLOG}" "${NEW_FM}" "${OLD_FM}" --account FLEET_MEMORY --execute || fm_rc=$?
chk "${fm_rc}" "FLEET_MEMORY rotation exited 0" "FLEET_MEMORY rotation exited ${fm_rc}"
if [ "${fm_rc}" != "0" ]; then sed -n '1,60p' "${FMLOG}"; fi
for f in fleet-memory-pg/relay-env-deploy.enc.env \
         fleet-memory-pg/fleet-memory-root.enc.env \
         fleet-memory-pg/guardkit.enc.env ; do
    if grep -Fq "R4 SYNCED + VERIFIED: ${f}" "${FMLOG}"; then pass "R4 synced+verified: ${f}"; else fail "R4 did not sync ${f}"; fi
    got="$(val_of "${ROOT}" "${f}" FLEET_MEMORY_NATS_URL)"
    if [ "${got}" = "nats://fleet-memory:${NEW_FM}@127.0.0.1:4222" ]; then
        pass "URL rewritten with user/host/port preserved: ${f}"
    else
        fail "URL malformed after rewrite in ${f}"
    fi
done
same "$(val_of "${ROOT}" fleet-memory-pg/relay-env-deploy.enc.env FLEET_MEMORY_PG_DSN)" \
    "postgresql://fm:fixturepw@127.0.0.1:5432/fm" \
    "a DIFFERENT DSN in the same file untouched" "an unrelated DSN was rewritten"
if grep -Fq "R4 plan: SKIP  fleet-memory-pg/guardkit.enc.env" "${FMLOG}"; then
    fail "guardkit file skipped for FLEET_MEMORY (it is a req row)"
else
    pass "guardkit file treated as a FLEET_MEMORY req row"
fi
assert_absent_under "${ROOT}" "OLD fleet-memory value" "${OLD_FM}"
assert_absent_under "${ROOT}" "NEW fleet-memory value" "${NEW_FM}"

# The GUARDKIT member's own key is absent from that file (PAGE-nats §8
# DISCOVERY) — the 'opt' row must SKIP, not fail.
GKLOG="${WORK}/exec-guardkit.log"
gk_rc=0
run_rotate "${GKLOG}" "$(gen)" "${OLD_GUARDKIT}" --account GUARDKIT --execute || gk_rc=$?
chk "${gk_rc}" "GUARDKIT rotation exited 0 with its DISCOVERY row open" "GUARDKIT rotation exited ${gk_rc}"
has "${GKLOG}" "R4 plan: SKIP  fleet-memory-pg/guardkit.enc.env" \
    "absent 'opt' key reported SKIP (DISCOVERY stays open), not a failure" \
    "the absent opt key was not reported as SKIP"

# ---------------------------------------------------------------------------
# (4) EXECUTE JARVIS — the systemd consumer file.
# ---------------------------------------------------------------------------
echo ""
echo "--- (4) EXECUTE JARVIS: systemd consumer file ---"
JLOG="${WORK}/exec-jarvis.log"
j_rc=0
run_rotate "${JLOG}" "${NEW_JARVIS}" "${OLD_JARVIS}" --account JARVIS --execute || j_rc=$?
chk "${j_rc}" "JARVIS rotation exited 0" "JARVIS rotation exited ${j_rc}"
if [ "${j_rc}" != "0" ]; then sed -n '1,60p' "${JLOG}"; fi
same "$(val_of "${ROOT}" slack-jarvis/jarvis.enc.env JARVIS_NATS_PASSWORD)" "${NEW_JARVIS}" \
    "jarvis consumer copy == NEW" "jarvis consumer copy not re-synced"
same "$(val_of "${ROOT}" nats/broker.enc.env JARVIS_NATS_PASSWORD)" "${NEW_JARVIS}" \
    "broker authority JARVIS member == NEW" "broker authority JARVIS member stale"
has "${JLOG}" "systemctl --user stop jarvis-serve-nats" \
    "the runbook names the systemd restart shape (never a bare restart)" \
    "the systemd restart shape is missing from the runbook"

# ---------------------------------------------------------------------------
# (5) opt rows on the OTHER host: --this-host nodeb -> SKIP, no mutation.
# ---------------------------------------------------------------------------
echo ""
echo "--- (5) --this-host nodeb: opt rows SKIP cleanly ---"
HASH_B4_NB="$(hash_root "${ROOT}")"
NBLOG="${WORK}/exec-nodeb.log"
nb_rc=0
run_rotate "${NBLOG}" "$(gen)" "$(gen)" --account RICH --this-host nodeb || nb_rc=$?
chk "${nb_rc}" "nodeb-host dry run exited 0" "nodeb-host run exited ${nb_rc}"
if grep -Fq "R4 plan: SKIP  study-tutor/http-env.enc.env" "${NBLOG}" && \
   grep -Fq "R4 plan: SKIP  study-tutor/http-env-kc.enc.env" "${NBLOG}"; then
    pass "both Node B opt rows reported SKIP (key absent, verify-at-run-time)"
else
    fail "Node B opt rows not reported SKIP"
fi
has "${NBLOG}" "REMOTE — runbook only" "gb10 rows become the REMOTE runbook rows from Node B" "gb10 rows not marked remote from Node B"
same "$(hash_root "${ROOT}")" "${HASH_B4_NB}" "no mutation from the nodeb-host run" "the nodeb-host run mutated a file"

# ---------------------------------------------------------------------------
# (6) two-phase safety: a REQUIRED consumer key missing aborts before any write.
# ---------------------------------------------------------------------------
echo ""
echo "--- (6) two-phase safety: required key missing aborts in PLAN ---"
ROOT2="${WORK}/fleet-secrets-broken"
make_root "${ROOT2}" break-req
HASH2_BEFORE="$(hash_root "${ROOT2}")"
BRKLOG="${WORK}/exec-broken.log"
brk_rc=0
printf '%s\n%s\n' "$(gen)" "${OLD_RICH}" | \
    "${ROTATE}" --secrets-root "${ROOT2}" --sops-bin "${SOPS_BIN}" --source sops \
    --register-page "${REGISTER_PAGE}" --account RICH --execute > "${BRKLOG}" 2>&1 || brk_rc=$?
nchk "${brk_rc}" "a missing REQUIRED consumer key aborts non-zero (rc ${brk_rc})" "the broken root was accepted"
has "${BRKLOG}" "R4 PLAN FAIL" "abort is reported as an R4 PLAN failure" "no R4 PLAN FAIL message"
same "$(hash_root "${ROOT2}")" "${HASH2_BEFORE}" \
    "TWO-PHASE PROVEN: authority file untouched when the plan fails" \
    "the authority file was written before the plan failed"

# ---------------------------------------------------------------------------
# (6b) trap proof: a FAILING `sops -e` mid-write must leave no plaintext window
# behind in /run/user and must not half-write the destination.
# ---------------------------------------------------------------------------
echo ""
echo "--- (6b) induced encrypt failure: trap shreds the plaintext window ---"
ROOT4="${WORK}/fleet-secrets-encfail"
make_root "${ROOT4}" ok
FAILSOPS="${WORK}/failing-sops"
cat > "${FAILSOPS}" <<EOF
#!/usr/bin/env bash
for a in "\$@"; do
    if [ "\$a" = "-e" ]; then exit 66; fi
done
exec "${SOPS_BIN}" "\$@"
EOF
chmod 755 "${FAILSOPS}"
HASH4_BEFORE="$(hash_root "${ROOT4}")"
FAILLOG="${WORK}/exec-encfail.log"
encfail_rc=0
printf '%s\n%s\n' "$(gen)" "${OLD_RICH}" | \
    "${ROTATE}" --secrets-root "${ROOT4}" --sops-bin "${FAILSOPS}" --source sops \
    --register-page "${REGISTER_PAGE}" --account RICH --execute > "${FAILLOG}" 2>&1 || encfail_rc=$?
nchk "${encfail_rc}" "a failing 'sops -e' aborts non-zero (rc ${encfail_rc})" "the failing encrypt was swallowed"
same "$(hash_root "${ROOT4}")" "${HASH4_BEFORE}" \
    "destination untouched when the encrypt fails (encrypt-to-temp-then-install)" \
    "the destination was written despite a failed encrypt"
encfail_left="$(find "/run/user/$(id -u)" -maxdepth 1 -name 'rotate-nats.*' 2>/dev/null | wc -l)"
chk "${encfail_left}" "EXIT trap shredded the plaintext window on the failure path" \
    "${encfail_left} plaintext window(s) survived a failed encrypt"

# ---------------------------------------------------------------------------
# (7) zero plaintext at rest + still-ciphertext + no tmpfs residue.
# ---------------------------------------------------------------------------
echo ""
echo "--- (7) zero plaintext at rest ---"
i=0
for v in "${ALL_VALUES[@]}"; do
    i=$((i + 1))
    if grep -rFq -- "${v}" "${ROOT}" "${ROOT2}" "${ROOT4}" 2>/dev/null; then
        fail "value #${i} found in cleartext under a fixture root"
    fi
done
pass "none of the ${#ALL_VALUES[@]} synthetic values appears in cleartext under any fixture root"
enc_bad=0
while IFS= read -r f; do
    grep -q '^sops_version=' "${f}" || enc_bad=$((enc_bad + 1))
    grep -q 'ENC\[AES256_GCM' "${f}" || enc_bad=$((enc_bad + 1))
done < <(find "${ROOT}" -name '*.enc.env' -type f)
chk "${enc_bad}" "every fixture file is still a valid sops dotenv ciphertext" "${enc_bad} ciphertext-shape defects"
mode_bad=0
while IFS= read -r f; do
    [ "$(stat -c '%a' "${f}")" = "600" ] || mode_bad=$((mode_bad + 1))
done < <(find "${ROOT}" -name '*.enc.env' -type f)
chk "${mode_bad}" "file modes preserved at 600 through re-encrypt" "${mode_bad} files lost their 600 mode"
leftover="$(find "/run/user/$(id -u)" -maxdepth 1 -name 'rotate-nats.*' 2>/dev/null | wc -l)"
chk "${leftover}" "no /run/user/\$UID plaintext window survived (trap shredded all)" "${leftover} runtime temp(s) left behind"

# ---------------------------------------------------------------------------
# (8)+(9)+(10) set -x trace, argv and display audits on a fresh root.
# ---------------------------------------------------------------------------
echo ""
echo "--- (8/9/10) set -x, argv and display audits ---"
ROOT3="${WORK}/fleet-secrets-xtrace"
make_root "${ROOT3}" ok
PSDUMP="${WORK}/ps-argv.dump"
: > "${PSDUMP}"
touch "${WORK}/.sampling"
( while [ -f "${WORK}/.sampling" ]; do ps -eo args >> "${PSDUMP}" 2>/dev/null || true; sleep 0.2; done ) &
SAMPLER_PID=$!
XNEW="$(gen)"
XTRACE_LOG="${WORK}/xtrace.log"
x_rc=0
printf '%s\n%s\n' "${XNEW}" "${OLD_RICH}" | \
    bash -x "${ROTATE}" --secrets-root "${ROOT3}" --sops-bin "${SOPS_BIN}" --source sops \
    --register-page "${REGISTER_PAGE}" --account RICH --execute > "${XTRACE_LOG}" 2>&1 || x_rc=$?
rm -f "${WORK}/.sampling"
wait "${SAMPLER_PID}" 2>/dev/null || true
chk "${x_rc}" "the traced run exited 0" "the traced run exited ${x_rc}"
if [ "${x_rc}" != "0" ]; then tail -20 "${XTRACE_LOG}"; fi
if grep -q '^+ ' "${XTRACE_LOG}"; then pass "xtrace really was active (trace lines present)"; else fail "no xtrace lines — the audit would be vacuous"; fi
trace_hit=0
for v in "${XNEW}" "${OLD_RICH}" "${OLD_FM}" "${OLD_JARVIS}"; do
    grep -Fq -- "${v}" "${XTRACE_LOG}" && trace_hit=$((trace_hit + 1))
done
chk "${trace_hit}" "set -x trace + stdout/stderr contain NO secret value (display clean)" \
    "${trace_hit} secret value(s) leaked into the trace/display (values not quoted)"
argv_hit=0
for v in "${XNEW}" "${OLD_RICH}" "${OLD_FM}" "${OLD_JARVIS}" "${NEW_RICH}"; do
    grep -Fq -- "${v}" "${PSDUMP}" && argv_hit=$((argv_hit + 1))
done
chk "${argv_hit}" "no secret value in any sampled 'ps -eo args'" \
    "${argv_hit} argv exposure(s) (values not quoted)"
same "$(val_of "${ROOT3}" nats/broker.enc.env RICH_NATS_PASSWORD)" "${XNEW}" \
    "the traced run really rotated (authority carries the new value)" "the traced run did not rotate"

# ---------------------------------------------------------------------------
# no-daemon audit (the whole run).
# ---------------------------------------------------------------------------
echo ""
echo "--- no-daemon audit ---"
if [ -s "${SHIM_LOG}" ]; then
    fail "a forbidden verb was invoked:"
    cat "${SHIM_LOG}"
else
    pass "docker / docker-compose / nats / systemctl / ssh were NEVER invoked"
fi

# ---------------------------------------------------------------------------
echo ""
echo "======================================="
echo "  RESULTS: ${pass_n} passed, ${fail_n} failed"
echo "======================================="
[ "${fail_n}" -eq 0 ]
