#!/usr/bin/env bash
# =============================================================================
# provision-kv.sh — Idempotent KV Bucket Provisioning
# =============================================================================
# Reads KV bucket definitions from kv/kv-definitions.json and applies the
# check-then-create-or-update idempotency pattern for each bucket.
#
# Safe to run multiple times: on first deploy, on reboot, and after definition changes.
#
# Environment variables:
#   NATS_URL    — NATS server URL (default: nats://localhost:4222)
#   NATS_CREDS  — Path to NATS credentials file (optional)
#
# Usage:
#   ./kv/provision-kv.sh              # Provision all KV buckets
#   ./kv/provision-kv.sh --dry-run    # Preview actions without modifying
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

# Dry-run mode
DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
    echo "=== DRY RUN MODE — no changes will be made ==="
fi

# Summary counters
created=0
updated=0
current=0
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
# Provision a single KV bucket
# ---------------------------------------------------------------------------
provision_kv_bucket() {
    local name="$1"
    local ttl="$2"
    local storage="$3"
    local history="$4"
    local max_value_size="$5"
    local replicas="$6"

    # Build TTL flags — null/empty means no TTL (persistent)
    local ttl_opts=()
    if [[ -n "$ttl" ]] && [[ "$ttl" != "null" ]]; then
        ttl_opts=("--ttl" "$ttl")
    fi

    # Build storage flag
    local storage_opts=()
    if [[ -n "$storage" ]] && [[ "$storage" != "null" ]]; then
        storage_opts=("--storage" "$storage")
    fi

    # Build history flag
    local history_opts=()
    if [[ -n "$history" ]] && [[ "$history" != "null" ]]; then
        history_opts=("--history" "$history")
    fi

    # Build max-value-size flag
    local max_value_size_opts=()
    if [[ -n "$max_value_size" ]] && [[ "$max_value_size" != "null" ]]; then
        max_value_size_opts=("--max-value-size" "$max_value_size")
    fi

    # Build replicas flag
    local replicas_opts=()
    if [[ -n "$replicas" ]] && [[ "$replicas" != "null" ]]; then
        replicas_opts=("--replicas" "$replicas")
    fi

    # Check if KV bucket already exists via: nats kv info <NAME>
    if nats kv info "$name" "${NATS_OPTS[@]}" >/dev/null 2>&1; then
        # Bucket exists — check if update is needed
        if [[ "$DRY_RUN" == "true" ]]; then
            echo "[DRY-RUN] Would check/update KV bucket: $name"
            current=$((current + 1))
            return 0
        fi

        # Attempt update with all configured flags
        local update_opts=()
        [[ ${#ttl_opts[@]} -gt 0 ]] && update_opts+=("${ttl_opts[@]}")
        [[ ${#history_opts[@]} -gt 0 ]] && update_opts+=("${history_opts[@]}")
        [[ ${#max_value_size_opts[@]} -gt 0 ]] && update_opts+=("${max_value_size_opts[@]}")
        [[ ${#replicas_opts[@]} -gt 0 ]] && update_opts+=("${replicas_opts[@]}")

        if [[ ${#update_opts[@]} -gt 0 ]]; then
            if nats kv update "$name" "${NATS_OPTS[@]}" "${update_opts[@]}" >/dev/null 2>&1; then
                echo "[UPDATE] KV $name"
                updated=$((updated + 1))
            else
                echo "[ERROR] KV $name — failed to update bucket" >&2
                errors=$((errors + 1))
            fi
        else
            echo "[OK] KV $name"
            current=$((current + 1))
        fi
    else
        # Bucket does not exist — create via: nats kv add <NAME>
        if [[ "$DRY_RUN" == "true" ]]; then
            echo "[DRY-RUN] Would create KV bucket: $name (ttl=${ttl:-none}, storage=${storage:-file}, history=${history:-1})"
            created=$((created + 1))
            return 0
        fi

        local create_opts=()
        [[ ${#ttl_opts[@]} -gt 0 ]] && create_opts+=("${ttl_opts[@]}")
        [[ ${#storage_opts[@]} -gt 0 ]] && create_opts+=("${storage_opts[@]}")
        [[ ${#history_opts[@]} -gt 0 ]] && create_opts+=("${history_opts[@]}")
        [[ ${#max_value_size_opts[@]} -gt 0 ]] && create_opts+=("${max_value_size_opts[@]}")
        [[ ${#replicas_opts[@]} -gt 0 ]] && create_opts+=("${replicas_opts[@]}")

        if nats kv add "$name" "${NATS_OPTS[@]}" "${create_opts[@]}" >/dev/null 2>&1; then
            echo "[CREATE] KV $name"
            created=$((created + 1))
        else
            echo "[ERROR] KV $name — failed to create bucket" >&2
            errors=$((errors + 1))
        fi
    fi
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
    echo "=========================================="
    echo "KV Bucket Provisioning"
    echo "=========================================="
    echo "NATS URL:    ${NATS_URL}"
    echo "Definitions: ${KV_DEFS_FILE}"
    echo ""

    # Wait for NATS to be healthy (skip in dry-run mode)
    if [[ "$DRY_RUN" != "true" ]]; then
        wait_for_nats
    fi

    # Count total KV buckets from .kv_buckets[] array
    local total
    total=$(jq '.kv_buckets | length' "$KV_DEFS_FILE")
    echo "Processing ${total} KV bucket definitions..."
    echo ""

    # Iterate over each KV bucket in .kv_buckets[] and extract fields
    local i=0
    while [[ $i -lt $total ]]; do
        local name ttl storage history max_value_size replicas

        name=$(jq -r ".kv_buckets[$i].name" "$KV_DEFS_FILE")
        ttl=$(jq -r ".kv_buckets[$i].ttl // empty" "$KV_DEFS_FILE")
        storage=$(jq -r ".kv_buckets[$i].storage // empty" "$KV_DEFS_FILE")
        history=$(jq -r ".kv_buckets[$i].history // empty" "$KV_DEFS_FILE")
        max_value_size=$(jq -r ".kv_buckets[$i].max_value_size // empty" "$KV_DEFS_FILE")
        replicas=$(jq -r ".kv_buckets[$i].replicas // empty" "$KV_DEFS_FILE")

        provision_kv_bucket "$name" "$ttl" "$storage" "$history" "$max_value_size" "$replicas"

        i=$((i + 1))
    done

    # ---------------------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------------------
    echo ""
    echo "=========================================="
    echo "KV Buckets: ${created} created, ${updated} updated, ${current} already current, ${errors} errors"
    echo "=========================================="

    if [[ $errors -gt 0 ]]; then
        echo "WARNING: ${errors} bucket(s) had errors. Check output above." >&2
    fi

    # Exit 0 even with non-fatal errors (buckets are processed individually)
    # Only fatal errors (missing jq, no NATS, missing file) cause non-zero exit
    exit 0
}

main
