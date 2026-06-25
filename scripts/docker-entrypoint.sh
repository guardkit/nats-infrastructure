#!/bin/sh
# =============================================================================
# Docker Entrypoint — NATS Server with envsubst Template Processing
# =============================================================================
# Processes .conf.template files under /etc/nats/config/accounts/ using
# envsubst to substitute ${VAR} password placeholders from environment
# variables, then launches nats-server with the processed configuration.
#
# Safety:
#   - Every required password var must be set, non-empty, and NOT equal to
#     the literal placeholder value "changeme" shipped in .env.example.
#   - After substitution, every processed file is grep-checked for both
#     "changeme" and unsubstituted ${VAR} references. If either survives,
#     the container refuses to start — this is the post-substitution
#     safeguard added after the MacBook incident where envsubst silently
#     produced a config still containing the placeholder literal.
#   - Runs on every container start, so a restart after editing .env
#     regenerates the processed config (idempotent).
#
# Required environment variables:
#   Core accounts — validated up-front by REQUIRED_VARS (clear "missing var" error):
#     RICH_NATS_PASSWORD          — Rich's APPMILLA account password
#     JAMES_NATS_PASSWORD         — James's APPMILLA account password
#     MARK_NATS_PASSWORD          — Mark's FINPROXY account password
#     ADMIN_NATS_PASSWORD         — SYS admin account password
#   Service identities — referenced by the template and substituted by envsubst
#   below; a missing value yields password: "" which the post-substitution guard
#   rejects, so the broker still refuses to start without them:
#     FORGE_NATS_PASSWORD         — forge service identity (APPMILLA) password
#     FLEET_MEMORY_NATS_PASSWORD  — fleet-memory relay service identity (APPMILLA)
#
# Usage (Docker):
#   ENTRYPOINT ["scripts/docker-entrypoint.sh"]
#   CMD ["-c", "/etc/nats/nats-server.conf"]

set -eu

# ---------------------------------------------------------------------------
# Configuration paths and constants
# ---------------------------------------------------------------------------
NATS_CONFIG_DIR="${NATS_CONFIG_DIR:-/etc/nats}"
TEMPLATE_DIR="${NATS_CONFIG_DIR}/config/accounts"
OUTPUT_DIR="${NATS_CONFIG_DIR}/accounts"
# Log directory for nats-server. Overridable so the entrypoint can run
# outside the container (e.g. in CI smoke tests) without root.
NATS_LOG_DIR="${NATS_LOG_DIR:-/var/log/nats}"

# Literal placeholder value shipped in .env.example. If this value ever
# reaches the processed config the container is insecure — refuse to start.
PLACEHOLDER_VALUE="changeme"

REQUIRED_VARS="RICH_NATS_PASSWORD JAMES_NATS_PASSWORD MARK_NATS_PASSWORD ADMIN_NATS_PASSWORD"

# ---------------------------------------------------------------------------
# Validate required password variables
# ---------------------------------------------------------------------------
# Each var must be:
#   - set (not unbound)
#   - non-empty
#   - NOT equal to the placeholder value "changeme"
missing_vars=""
placeholder_vars=""
for var in $REQUIRED_VARS; do
    eval "val=\${${var}:-}"
    if [ -z "$val" ]; then
        missing_vars="${missing_vars} ${var}"
    elif [ "$val" = "$PLACEHOLDER_VALUE" ]; then
        placeholder_vars="${placeholder_vars} ${var}"
    fi
done

if [ -n "$missing_vars" ]; then
    echo "ERROR: Missing or empty required environment variables:${missing_vars}" >&2
    echo "Set these in .env or Docker Compose environment block." >&2
    exit 1
fi

if [ -n "$placeholder_vars" ]; then
    echo "ERROR: Placeholder password '${PLACEHOLDER_VALUE}' detected for:${placeholder_vars}" >&2
    echo "Replace every '${PLACEHOLDER_VALUE}' value in .env with a real, unique password." >&2
    echo "The entrypoint refuses to start with placeholder credentials." >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Create required directories
# ---------------------------------------------------------------------------
# Create the output directory for processed config files
mkdir -p "${OUTPUT_DIR}"
# Create the log directory referenced in nats-server.conf
mkdir -p "${NATS_LOG_DIR}"

# ---------------------------------------------------------------------------
# Process templates with envsubst (re-runs every container start)
# ---------------------------------------------------------------------------
processed_any=0
for template in "${TEMPLATE_DIR}"/*.conf.template; do
    if [ ! -f "$template" ]; then
        echo "WARNING: No .conf.template files found in ${TEMPLATE_DIR}" >&2
        break
    fi
    filename=$(basename "$template" .template)
    output="${OUTPUT_DIR}/${filename}"
    # Restrict substitution to ONLY the password variables. A blanket
    # `envsubst` would also clobber NATS system subjects written as `$JS.…` /
    # `$KV.…` in permission ACLs (envsubst treats them as shell vars → empty),
    # producing invalid subjects like `.API.>`. Naming the allowed vars leaves
    # every other `$`-token (NATS subjects) untouched, which is what lets
    # accounts use subject-scoped permissions including JetStream/KV subjects.
    envsubst '${RICH_NATS_PASSWORD} ${JAMES_NATS_PASSWORD} ${MARK_NATS_PASSWORD} ${ADMIN_NATS_PASSWORD} ${FORGE_NATS_PASSWORD} ${FLEET_MEMORY_NATS_PASSWORD}' < "$template" > "$output"
    processed_any=1
    echo "Processed: ${template} -> ${output}"
done

# ---------------------------------------------------------------------------
# Post-substitution safeguard — refuse to start on a compromised config
# ---------------------------------------------------------------------------
# Catches two failure modes observed or feared in production:
#   1. The placeholder string "changeme" is still present in the processed
#      config (e.g. a template was edited to hardcode it, or the validation
#      above was bypassed). This was the MacBook incident.
#   2. An unsubstituted "${VAR}" reference slipped through because the env
#      var was missing/unexported when envsubst ran (envsubst treats missing
#      vars as empty strings by default).
if [ "$processed_any" -eq 1 ]; then
    for processed in "${OUTPUT_DIR}"/*.conf; do
        [ -f "$processed" ] || continue

        if grep -q "\"${PLACEHOLDER_VALUE}\"" "$processed"; then
            echo "ERROR: Placeholder '${PLACEHOLDER_VALUE}' found in processed config: ${processed}" >&2
            echo "Substitution did not produce a safe config. Refusing to start." >&2
            exit 1
        fi

        if grep -qE '\$\{[A-Z_][A-Z0-9_]*\}' "$processed"; then
            unsubstituted=$(grep -oE '\$\{[A-Z_][A-Z0-9_]*\}' "$processed" | sort -u | tr '\n' ' ')
            echo "ERROR: Unsubstituted variable reference(s) in ${processed}: ${unsubstituted}" >&2
            echo "Check that all required env vars are set and exported when the container starts." >&2
            exit 1
        fi

        # envsubst silently replaces a missing/unset variable with an empty
        # string — which would produce password: "" (an open account). Treat
        # any empty quoted password as a hard failure.
        if grep -qE 'password[[:space:]]*:[[:space:]]*""' "$processed"; then
            echo "ERROR: Empty password value in processed config: ${processed}" >&2
            echo "Likely cause: envsubst substituted a missing env var with an empty string." >&2
            exit 1
        fi
    done
fi

# ---------------------------------------------------------------------------
# Launch NATS server
# ---------------------------------------------------------------------------
# exec replaces this shell process with nats-server so signals (SIGTERM, etc.)
# are forwarded correctly for graceful shutdown.
exec nats-server "$@"
