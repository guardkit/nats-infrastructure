#!/bin/sh
# =============================================================================
# Docker Entrypoint — NATS Server with envsubst Template Processing
# =============================================================================
# Processes .conf.template files under /etc/nats/config/accounts/ using
# envsubst to substitute ${VAR} password placeholders from environment
# variables, then launches nats-server with the processed configuration.
#
# Required environment variables:
#   RICH_NATS_PASSWORD   — Rich's APPMILLA account password
#   JAMES_NATS_PASSWORD  — James's APPMILLA account password
#   MARK_NATS_PASSWORD   — Mark's FINPROXY account password
#   ADMIN_NATS_PASSWORD  — SYS admin account password
#
# Usage (Docker):
#   ENTRYPOINT ["scripts/docker-entrypoint.sh"]
#   CMD ["-c", "/etc/nats/nats-server.conf"]

set -eu

# ---------------------------------------------------------------------------
# Configuration paths
# ---------------------------------------------------------------------------
NATS_CONFIG_DIR="${NATS_CONFIG_DIR:-/etc/nats}"
TEMPLATE_DIR="${NATS_CONFIG_DIR}/config/accounts"
OUTPUT_DIR="${NATS_CONFIG_DIR}/accounts"

# ---------------------------------------------------------------------------
# Validate required password variables are set
# ---------------------------------------------------------------------------
missing_vars=""
for var in RICH_NATS_PASSWORD JAMES_NATS_PASSWORD MARK_NATS_PASSWORD ADMIN_NATS_PASSWORD; do
    eval "val=\${${var}:-}"
    if [ -z "$val" ]; then
        missing_vars="${missing_vars} ${var}"
    fi
done

if [ -n "$missing_vars" ]; then
    echo "ERROR: Missing required environment variables:${missing_vars}" >&2
    echo "Set these in .env or Docker Compose environment block." >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Process templates with envsubst
# ---------------------------------------------------------------------------
# Create the output directory for processed config files
mkdir -p "${OUTPUT_DIR}"

# Substitute environment variables in each .conf.template file
for template in "${TEMPLATE_DIR}"/*.conf.template; do
    if [ ! -f "$template" ]; then
        echo "WARNING: No .conf.template files found in ${TEMPLATE_DIR}" >&2
        break
    fi
    filename=$(basename "$template" .template)
    output="${OUTPUT_DIR}/${filename}"
    envsubst < "$template" > "$output"
    echo "Processed: ${template} -> ${output}"
done

# ---------------------------------------------------------------------------
# Launch NATS server
# ---------------------------------------------------------------------------
# exec replaces this shell process with nats-server so signals (SIGTERM, etc.)
# are forwarded correctly for graceful shutdown.
exec nats-server "$@"
