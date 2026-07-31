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
#   (6c) two-phase safety, DRIFTED DSN: a url row whose userinfo user is NOT this
#        account aborts in the PLAN phase — authority AND every other consumer
#        byte-identical (the half-applied-rotation hole)
#   (6d) two-phase safety, NON-DSN value: a url row whose value is not a
#        user:pw@host DSN aborts in the PLAN phase, same untouched estate
#   (6e) source-selection fence: `--source auto` with a plaintext .env present
#        must still choose the SOPS authority (DF-022 — plaintext must never
#        silently divert a rotation past the whole encrypted estate)
#   (7)  zero plaintext at rest: no secret value anywhere under the fixture root,
#        every file still sops-ciphertext, no /run/user temp survives
#   (8)  `bash -x` (set -x) audit: no secret value in the trace
#   (9)  argv audit: no secret value in any sampled `ps -eo args`
#   (10) display audit: no secret value on the script's stdout/stderr
#   (11) non-recipient refusal (the R2a analogue at the sops layer)
#   (12) flag fences: --live without --container, and --container without --live
#   (13) SERVICE vs CONTAINER (2026-07-31 defect 1): the emitted AND the executed
#        `docker compose … --force-recreate <X>` take the compose SERVICE name
#        (--compose-service), never the --container value; the container name is
#        still what `docker inspect` is asked about; and --restart-mode
#        compose-recreate REFUSES to run without an explicit --compose-service
#   (14) the emitted [FREEZE] step WORKS AS WRITTEN (2026-07-31 defect 2): its
#        credentials ride as an assignment prefix INSIDE the sops exec-env quoted
#        command (env, never argv), and the FORGE self-rotation caveat is emitted
#   (15) PROBE-SUBJECT LAW (2026-07-31 defect 3), BOTH clauses: for every
#        account, the probe subject the script announces must be (a) PERMITTED —
#        matched against that user's `publish:` grants PARSED OUT of
#        config/accounts/accounts.conf.template (an unpermitted subject is
#        refused asynchronously by a core `nats pub`, so GATE R2 would pass
#        vacuously) — AND (b) checked against the stream filters PARSED OUT of
#        streams/stream-definitions.json: an uncaptured subject must carry NO
#        attribution note, a captured one MUST carry a loud one
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
nohas() { if grep -Fq -- "$2" "$1"; then fail "$4"; else pass "$3"; fi; }

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
# Build a synthetic secrets root. $1 = path · $2 = variant:
#   ok              — the healthy estate
#   break-req       — omits NATS_PASSWORD from the REQUIRED specialist file
#   break-url-user  — fleet-memory-root's DSN carries a DIFFERENT nats user
#                     (the plausible stale/divergent copy: that file is the
#                     "TWICE-STALE" row in the CONSUMERS map)
#   break-url-shape — fleet-memory-root's value is not a DSN at all
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

    # Broker authority — all eight. FIDELITY: the REAL nats/broker.enc.env (and
    # forge-nats / jarvis / specialist-agent) carry WHOLE-LINE `#` comments,
    # including ones containing `|` and `=`. The exec-env parser law bans INLINE
    # (trailing) comments on a value line — it does not ban comment lines — so
    # the fixture must meet the shape S2 will actually meet: the rewrite must
    # round-trip every comment byte-exactly.
    {
        printf '# nats-infrastructure — broker account passwords (DF-022 sops authority)\n'
        printf '# NATS Account Passwords\n'
        printf '# Account: SYS | User: admin | consumed by: docker-entrypoint.sh envsubst\n'
        printf '# rendered as KEY=VALUE pairs into accounts.conf; no inline comments\n'
        printf 'ADMIN_NATS_PASSWORD=%s\n' "${OLD_ADMIN}"
        printf 'RICH_NATS_PASSWORD=%s\n' "${OLD_RICH}"
        printf 'JAMES_NATS_PASSWORD=%s\n' "$(gen)"
        printf 'MARK_NATS_PASSWORD=%s\n' "$(gen)"
        printf 'FORGE_NATS_PASSWORD=%s\n' "${OLD_FORGE}"
        printf 'FLEET_MEMORY_NATS_PASSWORD=%s\n' "${OLD_FM}"
        printf 'GUARDKIT_NATS_PASSWORD=%s\n' "${OLD_GUARDKIT}"
        printf '# Account: JARVIS | User: jarvis | systemd --user consumer\n'
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
    case "${variant}" in
        break-url-user)
            # A plausible divergence: the TWICE-STALE copy points at another user.
            printf 'FLEET_MEMORY_NATS_URL=nats://someoneelse:%s@127.0.0.1:4222\nFLEET_MEMORY_EMBED_URL=http://127.0.0.1:8080\n' \
                "${OLD_FM}" > "${root}/fleet-memory-pg/fleet-memory-root.enc.env" ;;
        break-url-shape)
            # Present, required, but not a DSN at all (a host:port was recorded).
            printf 'FLEET_MEMORY_NATS_URL=127.0.0.1:4222\nFLEET_MEMORY_EMBED_URL=http://127.0.0.1:8080\n' \
                > "${root}/fleet-memory-pg/fleet-memory-root.enc.env" ;;
        break-dup-key)
            # COACH BLOCKER (2026-07-30): the key present TWICE — must abort in
            # PLAN, never at apply with the authority already rewritten.
            printf 'FLEET_MEMORY_NATS_URL=nats://fleet-memory:%s@127.0.0.1:4222\nFLEET_MEMORY_NATS_URL=nats://fleet-memory:%s@127.0.0.1:4222\nFLEET_MEMORY_EMBED_URL=http://127.0.0.1:8080\n' \
                "${OLD_FM}" "${OLD_FM}" > "${root}/fleet-memory-pg/fleet-memory-root.enc.env" ;;
        *)
            printf 'FLEET_MEMORY_NATS_URL=nats://fleet-memory:%s@127.0.0.1:4222\nFLEET_MEMORY_EMBED_URL=http://127.0.0.1:8080\n' \
                "${OLD_FM}" > "${root}/fleet-memory-pg/fleet-memory-root.enc.env" ;;
    esac
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
# --secrets-root is passed even here: these cases are SUPPOSED to die in the
# arg-validation block before any source resolution, but isolation from the real
# root must be by CONSTRUCTION, not by that ordering happening to hold.
fence_rc=0
printf '%s\n\n' "$(gen)" | "${ROTATE}" --secrets-root "${ROOT}" --sops-bin "${SOPS_BIN}" \
    --account RICH --live >/dev/null 2>&1 || fence_rc=$?
nchk "${fence_rc}" "--live without --container is refused" "--live without --container was accepted"
fence_rc=0
printf '%s\n\n' "$(gen)" | "${ROTATE}" --secrets-root "${ROOT}" --sops-bin "${SOPS_BIN}" \
    --account RICH --container some-box >/dev/null 2>&1 || fence_rc=$?
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
# Fidelity proof: EVERY line of the authority except the rotated one must survive
# byte-exactly — comment lines included, and the fixture's comments carry `|` and
# `=` exactly as the real broker.enc.env does. Compared as a hash so no value is
# ever printed.
AUTH_SANS_BEFORE="$(dec "${ROOT}" nats/broker.enc.env | grep -v '^RICH_NATS_PASSWORD=' | sha256sum)"
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
same "$(dec "${ROOT}" nats/broker.enc.env | grep -v '^RICH_NATS_PASSWORD=' | sha256sum)" \
    "${AUTH_SANS_BEFORE}" \
    "authority round-trips byte-exactly except the rotated line (comment lines with | and = survive)" \
    "the rewrite disturbed a non-target line of the authority (comments?)"
if dec "${ROOT}" nats/broker.enc.env | grep -Fq '# Account: SYS | User: admin'; then
    pass "the fixture's real-shape comment line is still present after the rewrite"
else
    fail "a comment line was lost by the rewrite — the fixture no longer matches the real file shape"
fi
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
# (6c)+(6d) two-phase safety for URL rows — the half-applied-rotation hole.
# A url row's DSN parse + userinfo-user match MUST happen in the PLAN phase. If
# it happens only at apply time, the authority is already re-encrypted and the
# earlier consumer rows already written when the drifted row aborts — exactly the
# state two-phase exists to prevent. FLEET_MEMORY is the case that matters: three
# url rows, and the drifted one (fleet-memory-root) is NOT first in the map.
# ---------------------------------------------------------------------------
url_drift_case() {  # $1 variant · $2 label
    local variant="$1" label="$2" root log rc before
    root="${WORK}/fleet-secrets-${variant}"
    log="${WORK}/exec-${variant}.log"
    make_root "${root}" "${variant}"
    before="$(hash_root "${root}")"
    rc=0
    printf '%s\n%s\n' "$(gen)" "${OLD_FM}" | \
        "${ROTATE}" --secrets-root "${root}" --sops-bin "${SOPS_BIN}" --source sops \
        --register-page "${REGISTER_PAGE}" --account FLEET_MEMORY --execute > "${log}" 2>&1 || rc=$?
    nchk "${rc}" "${label}: aborts non-zero (rc ${rc})" "${label}: the drifted estate was accepted"
    has "${log}" "R4 PLAN FAIL" "${label}: abort is reported as an R4 PLAN failure" \
        "${label}: aborted somewhere OTHER than the plan phase (half-applied risk)"
    if grep -Fq "GATE R1 PASS" "${log}"; then
        fail "${label}: the authority was re-encrypted BEFORE the drift was caught"
    else
        pass "${label}: no GATE R1 write was attempted"
    fi
    if grep -Fq "R4 SYNCED + VERIFIED" "${log}"; then
        fail "${label}: a consumer file was written BEFORE the drift was caught"
    else
        pass "${label}: no consumer file was written"
    fi
    same "$(hash_root "${root}")" "${before}" \
        "${label}: TWO-PHASE PROVEN — authority AND every consumer byte-identical" \
        "${label}: the estate was half-applied (files changed before the abort)"
}
echo ""
echo "--- (6c) two-phase safety: url row carrying a DIFFERENT nats user ---"
url_drift_case break-url-user "drifted DSN user"
echo ""
echo "--- (6d) two-phase safety: url row whose value is not a DSN ---"
url_drift_case break-url-shape "non-DSN url value"
url_drift_case break-dup-key "dup-key row (coach blocker 2026-07-30)"

# ---------------------------------------------------------------------------
# (6e) source selection: a stray plaintext .env must NOT divert the rotation.
# DF-022 retired the broker's plaintext .env; `--source auto` must therefore
# choose the SOPS authority whenever one exists. The old plaintext-preferred
# resolution exited 0 with a success banner having touched NOTHING encrypted.
# ---------------------------------------------------------------------------
echo ""
echo "--- (6e) --source auto is SOPS-preferred (a stray .env cannot divert it) ---"
ROOT5="${WORK}/fleet-secrets-auto"
make_root "${ROOT5}" ok
STRAY_ENV="${WORK}/stray.env"
printf 'RICH_NATS_PASSWORD=%s\n' "$(gen)" > "${STRAY_ENV}"
chmod 600 "${STRAY_ENV}"
AUTOLOG="${WORK}/exec-auto.log"
AUTO_NEW="$(gen)"
auto_rc=0
printf '%s\n%s\n' "${AUTO_NEW}" "${OLD_RICH}" | \
    "${ROTATE}" --secrets-root "${ROOT5}" --sops-bin "${SOPS_BIN}" --env-file "${STRAY_ENV}" \
    --register-page "${REGISTER_PAGE}" --account RICH --execute > "${AUTOLOG}" 2>&1 || auto_rc=$?
chk "${auto_rc}" "auto-source run exited 0" "auto-source run exited ${auto_rc}"
has "${AUTOLOG}" "source    : sops" "--source auto chose the SOPS authority despite a plaintext .env" \
    "--source auto fell through to plaintext and skipped the whole sops estate"
same "$(val_of "${ROOT5}" nats/broker.enc.env RICH_NATS_PASSWORD)" "${AUTO_NEW}" \
    "the encrypted authority really took the new value under auto" \
    "the encrypted authority was left stale under auto"
same "$(val_of "${ROOT5}" nats/specialist-agent.enc.env NATS_PASSWORD)" "${AUTO_NEW}" \
    "consumer re-sync still ran under auto" "consumers were skipped under auto"
if grep -Fq -- "${AUTO_NEW}" "${STRAY_ENV}"; then
    fail "the stray plaintext .env was written by the auto run"
else
    pass "the stray plaintext .env was NOT written (the sops authority is the target)"
fi
# The plaintext branch itself must still work when it is asked for explicitly,
# and must leave NO temp beside the env-file (RUNTIME PLAINTEXT LAW: the working
# copy lives on the tmpfs, never in a git work tree).
PT_ENV="${WORK}/plaintext/.env"
mkdir -p "${WORK}/plaintext"
PT_NEW="$(gen)"
printf 'ADMIN_NATS_PASSWORD=%s\nRICH_NATS_PASSWORD=%s\n' "${OLD_ADMIN}" "${OLD_RICH}" > "${PT_ENV}"
chmod 644 "${PT_ENV}"
PTLOG="${WORK}/exec-plaintext.log"
pt_rc=0
printf '%s\n%s\n' "${PT_NEW}" "${OLD_RICH}" | \
    "${ROTATE}" --secrets-root "${ROOT5}" --sops-bin "${SOPS_BIN}" --env-file "${PT_ENV}" \
    --source plaintext --register-page "${REGISTER_PAGE}" --account RICH --execute \
    > "${PTLOG}" 2>&1 || pt_rc=$?
chk "${pt_rc}" "explicit --source plaintext still rotates the env-file" "plaintext run exited ${pt_rc}"
if grep -Fq -- "${PT_NEW}" "${PT_ENV}"; then
    pass "plaintext env-file carries the new value"
else
    fail "plaintext env-file was not rewritten"
fi
has "${PTLOG}" "WARNING: PLAINTEXT SOURCE" "plaintext mode warns that the sops estate is untouched" \
    "plaintext mode exits successfully with no warning about the skipped sops estate"
pt_temps="$(find "${WORK}/plaintext" -maxdepth 1 -name '.env.rotate.*' | wc -l)"
chk "${pt_temps}" "no plaintext temp left beside the env-file" \
    "${pt_temps} temp(s) left beside the env-file — repo-adjacent plaintext"
same "$(stat -c '%a' "${PT_ENV}")" "644" "env-file mode preserved" "env-file mode changed"
# Construction-level proof (no race to win): with the runtime dir ABSENT the
# plaintext branch must DIE, because its working copy is a /run/user temp. The
# old branch mktemp'd beside the env-file — inside a git work tree, with the
# source's mode (e.g. 644) copied onto it — and would have succeeded here.
PTLOG2="${WORK}/exec-plaintext-notmpfs.log"
PT_BEFORE="$(sha256sum "${PT_ENV}")"
pt2_rc=0
printf '%s\n%s\n' "$(gen)" "${OLD_RICH}" | \
    "${ROTATE}" --secrets-root "${ROOT5}" --sops-bin "${SOPS_BIN}" --env-file "${PT_ENV}" \
    --source plaintext --runtime-dir "${WORK}/no-such-tmpfs" --register-page "${REGISTER_PAGE}" \
    --account RICH --execute > "${PTLOG2}" 2>&1 || pt2_rc=$?
nchk "${pt2_rc}" "plaintext branch refuses to write with no tmpfs — its working copy IS a /run/user temp" \
    "plaintext branch wrote without a tmpfs — the working copy is NOT under the runtime dir"
has "${PTLOG2}" "runtime dir not found" "the refusal names the missing runtime dir" \
    "the refusal did not come from the RUNTIME PLAINTEXT LAW check"
same "$(sha256sum "${PT_ENV}")" "${PT_BEFORE}" "env-file untouched by the refused run" \
    "the env-file was written despite the refusal"

# ---------------------------------------------------------------------------
# (7) zero plaintext at rest + still-ciphertext + no tmpfs residue.
# ---------------------------------------------------------------------------
echo ""
echo "--- (7) zero plaintext at rest ---"
# Every fixture root built so far (the drift roots and the auto root included).
PLAINTEXT_ROOTS=("${ROOT}" "${ROOT2}" "${ROOT4}" "${ROOT5}" \
                 "${WORK}/fleet-secrets-break-url-user" "${WORK}/fleet-secrets-break-url-shape")
i=0
clear_hits=0
for v in "${ALL_VALUES[@]}"; do
    i=$((i + 1))
    if grep -rFq -- "${v}" "${PLAINTEXT_ROOTS[@]}" 2>/dev/null; then
        fail "value #${i} found in cleartext under a fixture root"
        clear_hits=$((clear_hits + 1))
    fi
done
# Guarded: a genuine leak must NOT also print a contradicting PASS.
chk "${clear_hits}" \
    "none of the ${#ALL_VALUES[@]} synthetic values appears in cleartext under any of the ${#PLAINTEXT_ROOTS[@]} fixture roots" \
    "${clear_hits} synthetic value(s) found in cleartext (see the FAILs above)"
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
# (13) SERVICE vs CONTAINER — the 2026-07-31 conflation.
# `docker compose up -d --force-recreate <X>` resolves X against the compose
# file's `services:` keys; `docker inspect <Y>` resolves Y against CONTAINER
# names. This project maps service `nats` -> container `ships-computer-nats`, so
# feeding the container name to compose fails with 'no such service'.
# ---------------------------------------------------------------------------
echo ""
echo "--- (13) compose SERVICE vs docker CONTAINER ---"
# (13a) the DRY runbook's [RE-RENDER] line carries the default SERVICE.
has "${DRYLOG}" "up -d --force-recreate nats'" \
    "(13a) default runbook recreate names the compose SERVICE 'nats'" \
    "(13a) the default runbook recreate lost the compose service name"
# (13b) --compose-service really plumbs through to the emitted line.
CSVCLOG="${WORK}/dry-compose-service.log"
csvc_rc=0
run_rotate "${CSVCLOG}" "$(gen)" "$(gen)" --account RICH --compose-service brokerx || csvc_rc=$?
chk "${csvc_rc}" "(13b) --compose-service dry run exited 0" "(13b) --compose-service dry run exited ${csvc_rc}"
has "${CSVCLOG}" "up -d --force-recreate brokerx'" \
    "(13b) --compose-service brokerx reaches the emitted recreate line" \
    "(13b) --compose-service was ignored by the runbook emitter"
nohas "${CSVCLOG}" "up -d --force-recreate nats'" \
    "(13b) the overridden runbook no longer names the default service" \
    "(13b) the runbook emitted BOTH the default and the overridden service"
# (13c) the EXECUTED compose line. Recording shims stand in for docker/nats.
# THE FENCE IS NOT WEAKENED: the recorder is prepended IN FRONT of the exit-97
# forbidden shim, which itself sits in front of the real binaries — a miss falls
# through to the fence, never to a real daemon. The recorder opens no socket: it
# appends its argv to a log and answers the two `docker inspect` templates the
# script needs from a literal string. The PATH override is inline, so it applies
# to this ONE invocation and the forbidden-verb audit stays armed everywhere else.
RECSHIM="${WORK}/recshim"
RECLOG="${WORK}/recorded-invocations.log"
mkdir -p "${RECSHIM}"
: > "${RECLOG}"
cat > "${RECSHIM}/docker" <<EOF
#!/usr/bin/env bash
printf 'docker %s\n' "\$*" >> "${RECLOG}"
if [ "\$1" = "inspect" ]; then
    case "\$*" in
        *State.Running*) echo "true" ;;
        *IPAddress*)     echo "10.255.255.254" ;;
    esac
fi
exit 0
EOF
cat > "${RECSHIM}/nats" <<EOF
#!/usr/bin/env bash
printf 'nats %s\n' "\$*" >> "${RECLOG}"
exit 1
EOF
chmod 755 "${RECSHIM}/docker" "${RECSHIM}/nats"
ROOT6="${WORK}/fleet-secrets-compose"
make_root "${ROOT6}" ok
CSLOG="${WORK}/exec-compose-recreate.log"
cs_rc=0
printf '%s\n%s\n' "$(gen)" "${OLD_RICH}" | \
    PATH="${RECSHIM}:${PATH}" "${ROTATE}" --secrets-root "${ROOT6}" --sops-bin "${SOPS_BIN}" \
    --source sops --register-page "${REGISTER_PAGE}" --account RICH --execute \
    --live --container ships-computer-nats --restart-mode compose-recreate \
    --compose-service scratch-svc --poll-timeout 2 > "${CSLOG}" 2>&1 || cs_rc=$?
has "${CSLOG}" "Recreating via compose (OPERATOR path)" \
    "(13c) the run reached the compose-recreate step" \
    "(13c) the run never reached the compose-recreate step (nothing to audit)"
has "${RECLOG}" "up -d --force-recreate scratch-svc" \
    "(13c) EXECUTED compose line carries the SERVICE name" \
    "(13c) the executed compose line did not carry the --compose-service value"
if grep -F 'up -d --force-recreate' "${RECLOG}" | grep -Fq 'ships-computer-nats'; then
    fail "(13c) THE DEFECT: the CONTAINER name was handed to 'docker compose --force-recreate'"
else
    pass "(13c) the container name never appears on a compose --force-recreate line"
fi
if grep -F 'docker inspect' "${RECLOG}" | grep -Fq 'ships-computer-nats'; then
    pass "(13c) --container keeps its CONTAINER meaning (R0/probe inspect by name)"
else
    fail "(13c) the container name was not used for the docker inspect gates"
fi
# The run is EXPECTED to end non-zero: the recorder's `nats` always refuses, so
# wait_for_new_auth times out AFTER the recreate. That is the point at which it
# must fail — anything earlier means the compose audit above was vacuous.
nchk "${cs_rc}" "(13c) the fenced live run ends at the auth wait (rc ${cs_rc}), after the recreate" \
    "(13c) the fenced live run exited 0 — the auth gates were satisfied by a shim"
has "${CSLOG}" "never became live" \
    "(13c) the failure is the auth-wait timeout, not an earlier abort" \
    "(13c) the run aborted somewhere other than the auth wait"
# (13d) THE REQUIREMENT, not a default. A defaulted service name is still a
# guess, and guessing is the whole defect — compose-recreate must REFUSE to
# proceed without an explicit --compose-service, with a message that names both
# flags in plain words. Nothing else about the estate may be touched.
CSREQLOG="${WORK}/fence-compose-service-missing.log"
HASH_CSREQ="$(hash_root "${ROOT6}")"
csreq_rc=0
printf '%s\n\n' "$(gen)" | "${ROTATE}" --secrets-root "${ROOT6}" --sops-bin "${SOPS_BIN}" \
    --source sops --register-page "${REGISTER_PAGE}" --account RICH \
    --restart-mode compose-recreate > "${CSREQLOG}" 2>&1 || csreq_rc=$?
nchk "${csreq_rc}" "(13d) --restart-mode compose-recreate WITHOUT --compose-service is refused" \
    "(13d) compose-recreate ran with no --compose-service — the name was guessed again"
has "${CSREQLOG}" "requires --compose-service" \
    "(13d) the refusal names the missing flag" \
    "(13d) the refusal does not name --compose-service"
has "${CSREQLOG}" "It is NOT --container" \
    "(13d) the refusal spells out the SERVICE-vs-CONTAINER distinction in plain words" \
    "(13d) the refusal leaves the operator to work out which name is wanted"
has "${CSREQLOG}" "no such service" \
    "(13d) the refusal quotes the failure the operator would otherwise have seen" \
    "(13d) the refusal omits the actual compose failure mode"
same "$(hash_root "${ROOT6}")" "${HASH_CSREQ}" \
    "(13d) the refused run mutated nothing" "(13d) an enc file changed during the refused run"
# (13e) an EMPTY service name is refused too: `up -d --force-recreate` with no
# operand widens to EVERY service in the project — a fleet-wide recreate from a
# typo'd flag value.
CSEMPTYLOG="${WORK}/fence-compose-service-empty.log"
csempty_rc=0
printf '%s\n\n' "$(gen)" | "${ROTATE}" --secrets-root "${ROOT6}" --sops-bin "${SOPS_BIN}" \
    --source sops --register-page "${REGISTER_PAGE}" --account RICH \
    --restart-mode compose-recreate --compose-service "" > "${CSEMPTYLOG}" 2>&1 || csempty_rc=$?
nchk "${csempty_rc}" "(13e) an EMPTY --compose-service is refused" \
    "(13e) an empty --compose-service was accepted — the recreate would widen to every service"
has "${CSEMPTYLOG}" "must not be empty" \
    "(13e) the refusal says the service name may not be empty" \
    "(13e) the empty-value refusal came from somewhere else"
# (13f) external mode is UNAFFECTED — it executes no compose verb, so it must
# never acquire the new requirement. (DRYLOG above is exactly such a run and
# exited 0; assert the runbook flags its service name as the repo fallback so a
# paste-follower is not handed an unchecked guess.)
has "${DRYLOG}" "no --compose-service was passed" \
    "(13f) external-mode runbook marks its service name as this repo's own fallback" \
    "(13f) the external-mode runbook presents an unpassed service name as authoritative"
nohas "${CSVCLOG}" "no --compose-service was passed" \
    "(13f) the fallback caveat disappears once --compose-service is given" \
    "(13f) the fallback caveat is printed even when the flag was passed"

# ---------------------------------------------------------------------------
# (14) the emitted [FREEZE] step must WORK AS WRITTEN.
# Emitted bare (no creds) it dies with 'Authorization Violation'; emitted with
# creds on argv it would leak them to `ps`. The one shape that satisfies both is
# an assignment PREFIX inside the sops exec-env quoted command.
# ---------------------------------------------------------------------------
echo ""
echo "--- (14) emitted [FREEZE] step carries credentials, via env, inside exec-env ---"
FREEZE_CMD="'NATS_USER=forge NATS_PASSWORD=\"\$FORGE_NATS_PASSWORD\" nats consumer info PIPELINE forge-serve --server nats://127.0.0.1:4222'"
has "${DRYLOG}" "${FREEZE_CMD}" \
    "(14) the freeze step is emitted with NATS_USER/NATS_PASSWORD as an env assignment prefix" \
    "(14) the emitted freeze step does not carry the proven credential shape"
nohas "${DRYLOG}" "exec-env nats/broker.enc.env 'nats consumer info" \
    "(14) the old credential-less freeze line is gone" \
    "(14) THE DEFECT: the freeze line is still emitted with no credentials"
nohas "${DRYLOG}" "--password" \
    "(14) no --password style argv flag is ever emitted" \
    "(14) the runbook emits a credential on argv"
nohas "${DRYLOG}" "nats://forge:" \
    "(14) no creds-embedded URL is emitted (the 2026-07-30 display exposure)" \
    "(14) the runbook emits a creds-in-URL"
if grep -A1 -F "exec-env nats/broker.enc.env \\" "${DRYLOG}" | grep -Fq "'NATS_USER=forge NATS_PASSWORD="; then
    pass "(14) the credentialled command sits INSIDE the sops exec-env wrapper (next line)"
else
    fail "(14) the credentialled command is not wrapped by sops exec-env"
fi
nohas "${DRYLOG}" "ROTATING FORGE ITSELF" \
    "(14) the forge self-rotation caveat is NOT shown for a RICH rotation" \
    "(14) the forge-only caveat leaked into a RICH runbook"
FZLOG="${WORK}/dry-forge-freeze.log"
fz_rc=0
run_rotate "${FZLOG}" "$(gen)" "$(gen)" --account FORGE || fz_rc=$?
chk "${fz_rc}" "(14) FORGE dry run exited 0" "(14) FORGE dry run exited ${fz_rc}"
has "${FZLOG}" "ROTATING FORGE ITSELF" \
    "(14) rotating FORGE emits the 'freeze reading must predate the write' caveat" \
    "(14) the FORGE self-rotation caveat is missing — the emitted freeze line would be refused"

# ---------------------------------------------------------------------------
# (15) PROBE-SUBJECT LAW — derived, not golden. The stream filters are parsed
# out of streams/stream-definitions.json at run time, so adding a stream that
# swallows a probe subject fails this section without anyone editing a list.
# ---------------------------------------------------------------------------
echo ""
echo "--- (15) probe subjects vs the JetStream stream filters ---"
STREAM_DEFS="${SCRIPT_DIR}/../streams/stream-definitions.json"
stream_filters() {
    sed -n 's/.*"subjects"[[:space:]]*:[[:space:]]*\[\(.*\)\].*/\1/p' "${STREAM_DEFS}" \
        | tr ',' '\n' | tr -d ' "' | grep -v '^$'
}
# Every KV bucket is ALSO a stream (KV_<bucket>) whose subject filter is
# $KV.<bucket>.> — declared by name, never by a "subjects" key, so the parse
# above cannot see it. A probe on a $KV subject would not merely be persisted:
# it is a KV API call. Derive those filters too, from the same file.
kv_filters() {
    sed -n '/"kv_buckets"/,$p' "${STREAM_DEFS}" \
        | sed -n "s/.*\"name\"[[:space:]]*:[[:space:]]*\"\([^\"]*\)\".*/\$KV.\1.>/p"
}
# NATS subject matching: '*' = exactly one token · '>' = one-or-more trailing
# tokens · otherwise token equality.
subject_matches_filter() {  # $1 subject · $2 filter → 0 = CAPTURED
    local subj="$1" filt="$2" i=0
    local -a s=() f=()
    IFS='.' read -r -a s < <(printf '%s\n' "${subj}")
    IFS='.' read -r -a f < <(printf '%s\n' "${filt}")
    while [ "${i}" -lt "${#f[@]}" ]; do
        if [ "${f[${i}]}" = ">" ]; then
            if [ "${#s[@]}" -gt "${i}" ]; then return 0; fi
            return 1
        fi
        if [ "${i}" -ge "${#s[@]}" ]; then return 1; fi
        if [ "${f[${i}]}" != "*" ] && [ "${f[${i}]}" != "${s[${i}]}" ]; then return 1; fi
        i=$((i + 1))
    done
    if [ "${#s[@]}" -eq "${#f[@]}" ]; then return 0; fi
    return 1
}
[ -f "${STREAM_DEFS}" ] || { echo "stream definitions not found: ${STREAM_DEFS}" >&2; exit 2; }
mapfile -t FILTERS < <(stream_filters; kv_filters)
# Gate-of-the-gate #1: a parse that silently yields nothing would pass every
# account vacuously. 8 declared streams (one of which lists 2 subjects) + 4 KV
# buckets = 13 filters; require the full set, not "some".
if [ "${#FILTERS[@]}" -ge 13 ]; then
    pass "(15) parsed ${#FILTERS[@]} stream + KV subject filters out of stream-definitions.json"
else
    fail "(15) only ${#FILTERS[@]} filters parsed — the capture check would be vacuous"
fi
kv_seen=0
for filt in "${FILTERS[@]}"; do
    case "${filt}" in "\$KV."*) kv_seen=$((kv_seen + 1)) ;; esac
done
if [ "${kv_seen}" -ge 4 ]; then
    pass "(15) the implicit KV_<bucket> streams are in the filter set (${kv_seen} \$KV filters)"
else
    fail "(15) only ${kv_seen} \$KV filters derived — a \$KV probe subject would slip through"
fi
# Gate-of-the-gate #2: the matcher itself must call the known cases correctly.
matcher_bad=0
if ! subject_matches_filter "memory.episode.sec.probe" "memory.episode.>"; then matcher_bad=$((matcher_bad + 1)); fi
if ! subject_matches_filter "finproxy.sec.probe" "finproxy.>"; then matcher_bad=$((matcher_bad + 1)); fi
if subject_matches_filter "probe.rich" "pipeline.>"; then matcher_bad=$((matcher_bad + 1)); fi
if subject_matches_filter "_INBOX.sec.probe" "memory.dlq.>"; then matcher_bad=$((matcher_bad + 1)); fi
if subject_matches_filter "memory.episode" "memory.episode.>"; then matcher_bad=$((matcher_bad + 1)); fi
if ! subject_matches_filter "\$KV.agent-status.sec.probe" "\$KV.agent-status.>"; then matcher_bad=$((matcher_bad + 1)); fi
if subject_matches_filter "probe.rich" "\$KV.agent-status.>"; then matcher_bad=$((matcher_bad + 1)); fi
# …and on the PERMISSION half's cases too (the same matcher is reused below
# against `publish:` grants — NATS wildcard semantics are identical for a stream
# filter and a permission subject). An UNPERMITTED subject must be REJECTED by
# every grant shape, and the allow-all grant `>` (accounts.conf.template:40,48)
# must accept everything, or the new half would wave anything through.
if subject_matches_filter "zzzbogus.sec.probe" "runbook.>"; then matcher_bad=$((matcher_bad + 1)); fi
if subject_matches_filter "zzzbogus.sec.probe" "memory.episode.>"; then matcher_bad=$((matcher_bad + 1)); fi
if subject_matches_filter "runbook.sec.probe" "runbook.build.>"; then matcher_bad=$((matcher_bad + 1)); fi
if ! subject_matches_filter "zzzbogus.sec.probe" ">"; then matcher_bad=$((matcher_bad + 1)); fi
if ! subject_matches_filter "_INBOX.sec.probe" "_INBOX.>"; then matcher_bad=$((matcher_bad + 1)); fi
chk "${matcher_bad}" "(15) the subject/filter matcher is sound on known cases" \
    "(15) ${matcher_bad} matcher self-test(s) failed — the capture verdicts cannot be trusted"

# ---------------------------------------------------------------------------
# (15) THE PERMISSION HALF. The PROBE-SUBJECT LAW (rotate-nats-password.sh:59-63)
# has TWO clauses: the probe subject must be (a) PERMITTED for the account AND
# (b) captured by no stream filter. The filter parse above tests (b) only.
# Testing (a) is not cosmetic: probe_pub (rotate-nats-password.sh:535-542) is a
# fire-and-forget CORE `nats pub`, so a publish-permission violation is
# delivered asynchronously — it neither closes the connection nor fails the CLI.
# An unpermitted subject would therefore make GATE R2 pass VACUOUSLY, proving
# nothing about the new credential, which is exactly the failure class R2a
# exists to prevent. Derived, not golden: the grants are parsed out of
# config/accounts/accounts.conf.template at run time, so narrowing a user's
# grants fails this section without anyone editing a list here.
# ---------------------------------------------------------------------------
ACCOUNTS_TMPL="${SCRIPT_DIR}/../config/accounts/accounts.conf.template"
[ -f "${ACCOUNTS_TMPL}" ] || { echo "accounts template not found: ${ACCOUNTS_TMPL}" >&2; exit 2; }
# Prints one publish-grant subject per line for a nats user; empty output means
# the user has NO permissions block (NATS = allow-all). Handles all three shapes
# in the template: the single-string form (`publish: ">"`, …:40/48/189), the
# one-line list (`publish: [ … ]`, …:106/124) and the multi-line list
# (…:68-85/160-166). Whole-line `#` comments are dropped BEFORE quoted strings
# are harvested, because the comment prose itself contains quoted subject-like
# text (…:74-75, :81-82) that would otherwise be read as a grant.
user_publish_grants() {  # $1 = nats user name
    awk -v want="$1" '
        function emit(t,   s) {
            while (match(t, /"[^"]*"/)) {
                s = substr(t, RSTART + 1, RLENGTH - 2)
                if (s != "") { print s }
                t = substr(t, RSTART + RLENGTH)
            }
        }
        /^[[:space:]]*#/ { next }
        match($0, /user:[[:space:]]*"[^"]+"/) {
            u = substr($0, RSTART, RLENGTH)
            sub(/^user:[[:space:]]*"/, "", u); sub(/"$/, "", u)
            cur = u; inpub = 0; next
        }
        cur != want { next }
        inpub == 0 && $0 ~ /publish:/ {
            rest = $0
            sub(/.*publish:[[:space:]]*/, "", rest)
            emit(rest)
            if (rest ~ /\[/ && rest !~ /\]/) { inpub = 1 }
            next
        }
        inpub == 1 {
            emit($0)
            if ($0 ~ /\]/) { inpub = 0 }
        }
    ' "${ACCOUNTS_TMPL}"
}
# Gate-of-the-gate #3: a parse that silently yielded nothing would make the
# permission half vacuous, so prove the parser on all three grant shapes and on
# its comment immunity BEFORE any verdict leans on it. Structural, not golden —
# adding a grant to a user must not break this.
parser_bad=0
mapfile -t G_MARK < <(user_publish_grants "mark")            # single-string form
if [ "${#G_MARK[@]}" != "1" ] || [ "${G_MARK[0]}" != "finproxy.>" ]; then parser_bad=$((parser_bad + 1)); fi
mapfile -t G_RICH < <(user_publish_grants "rich")            # single-string allow-all
if [ "${#G_RICH[@]}" != "1" ] || [ "${G_RICH[0]}" != ">" ]; then parser_bad=$((parser_bad + 1)); fi
mapfile -t G_GK < <(user_publish_grants "guardkit")          # one-line list form
if [ "${#G_GK[@]}" != "1" ] || [ "${G_GK[0]}" != "memory.episode.>" ]; then parser_bad=$((parser_bad + 1)); fi
mapfile -t G_FORGE < <(user_publish_grants "forge")          # multi-line list form
if [ "${#G_FORGE[@]}" -lt 5 ]; then parser_bad=$((parser_bad + 1)); fi
# first and last entries of the multi-line block: proves the accumulation runs
# from the `publish: [` line through the closing `]`, not just the first line.
forge_joined=" ${G_FORGE[*]} "
case "${forge_joined}" in *" pipeline.> "*) : ;; *) parser_bad=$((parser_bad + 1)) ;; esac
case "${forge_joined}" in *" _INBOX.> "*) : ;; *) parser_bad=$((parser_bad + 1)) ;; esac
# comment immunity: a grant subject can never contain whitespace, so any
# harvested prose (from the quoted fragments at …:74-75 / :81-82) shows up here.
for g in "${G_FORGE[@]}" "${G_RICH[@]}" "${G_GK[@]}" "${G_MARK[@]}"; do
    case "${g}" in *[[:space:]]*) parser_bad=$((parser_bad + 1)) ;; esac
done
chk "${parser_bad}" "(15) the publish-grant parser is sound on all three grant shapes (+ comment-immune)" \
    "(15) ${parser_bad} grant-parser self-test(s) failed — the permission verdicts cannot be trusted"

captured_accounts=""
probe_bad=0
for acct in ADMIN RICH JAMES MARK FORGE FLEET_MEMORY GUARDKIT JARVIS; do
    plog="${WORK}/dry-probe-${acct}.log"
    p_rc=0
    run_rotate "${plog}" "$(gen)" "$(gen)" --account "${acct}" || p_rc=$?
    if [ "${p_rc}" != "0" ]; then
        fail "(15) ${acct}: dry run exited ${p_rc}"
        probe_bad=$((probe_bad + 1))
        continue
    fi
    subj="$(sed -n "s/^ *probe *: publish to '\([^']*\)'.*/\1/p" "${plog}" | head -1)"
    if [ -z "${subj}" ]; then
        fail "(15) ${acct}: the run did not announce a probe subject"
        probe_bad=$((probe_bad + 1))
        continue
    fi
    # ---- clause (a): is that subject PERMITTED for the user the probe runs as?
    # The user comes from the run's own banner (rotate-nats-password.sh:433), so
    # the account->user mapping is tested too, not assumed.
    puser="$(sed -n "s/^ *account *: .*(nats user '\([^']*\)'.*/\1/p" "${plog}" | head -1)"
    if [ -z "${puser}" ]; then
        fail "(15) ${acct}: the run did not announce the probe's nats user"
        probe_bad=$((probe_bad + 1))
        continue
    fi
    mapfile -t GRANTS < <(user_publish_grants "${puser}")
    permitted=""
    if [ "${#GRANTS[@]}" -eq 0 ]; then
        # accounts.conf.template:201-208 — admin's user carries NO permissions
        # block at all, so NATS grants it every subject. That is the ONE
        # allow-all exception; any OTHER user parsing empty is a parse hole or a
        # user that may not publish at all, and must NOT be waved through.
        if [ "${puser}" = "admin" ]; then
            permitted="no permissions block — allow-all"
        fi
    else
        for g in "${GRANTS[@]}"; do
            if subject_matches_filter "${subj}" "${g}"; then permitted="${g}"; break; fi
        done
    fi
    if [ -z "${permitted}" ]; then
        fail "(15) ${acct}: '${subj}' is NOT permitted for nats user '${puser}' — the probe would be refused asynchronously and GATE R2 would pass VACUOUSLY"
        probe_bad=$((probe_bad + 1))
        continue
    fi
    # ---- clause (b): is it captured by a stream filter?
    hit=""
    for filt in "${FILTERS[@]}"; do
        if subject_matches_filter "${subj}" "${filt}"; then hit="${filt}"; break; fi
    done
    noted=0
    if grep -Fq "PROBE ATTRIBUTION" "${plog}"; then noted=1; fi
    if [ -n "${hit}" ]; then
        captured_accounts="${captured_accounts}${acct} "
        if [ "${noted}" = "1" ]; then
            pass "(15) ${acct}: '${subj}' is permitted ('${puser}' grant: ${permitted}), captured by '${hit}', and the run says so LOUDLY"
        else
            fail "(15) ${acct}: '${subj}' lands in a stream ('${hit}') with NO attribution note"
            probe_bad=$((probe_bad + 1))
        fi
    else
        if [ "${noted}" = "0" ]; then
            pass "(15) ${acct}: '${subj}' is permitted ('${puser}' grant: ${permitted}) and captured by NO stream filter"
        else
            fail "(15) ${acct}: '${subj}' is uncaptured yet the run printed an attribution note"
            probe_bad=$((probe_bad + 1))
        fi
    fi
done
chk "${probe_bad}" "(15) every account's probe subject obeys the PROBE-SUBJECT LAW" \
    "(15) ${probe_bad} probe-subject verdict(s) failed"
# The ONLY accounts allowed to keep a captured subject are the two whose grants
# contain no uncaptured subject at all: guardkit may publish only
# memory.episode.>, mark only finproxy.>. A third name here means a curable
# probe was left in a stream.
same "${captured_accounts}" "MARK GUARDKIT " \
    "(15) exactly MARK + GUARDKIT keep a captured subject (their grants allow nothing else)" \
    "(15) the set of stream-captured probe accounts changed — a curable probe is landing in a stream"

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
