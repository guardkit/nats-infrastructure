#!/bin/sh
# =============================================================================
# NATS Server Verification Script
# =============================================================================
# Verifies that the NATS server started correctly with the expected
# configuration from TASK-NATS-001 through TASK-NATS-003.
#
# Checks performed:
#   1. Health endpoint responds (http://localhost:8222/healthz)
#   2. JetStream is initialised and reporting memory/storage info
#   3. Server name is 'ships-computer' and version is reported
#   4. (Optional) Account authentication via nats CLI
#   5. (Optional) JetStream streams provisioned — requires nats CLI
#
# Usage:
#   ./scripts/verify-nats.sh
#
# Exit codes:
#   0 — All checks passed
#   1 — One or more checks failed
#
# Dependencies:
#   Required: curl
#   Optional: jq (for JSON parsing), nats CLI (for auth + stream checks)
# =============================================================================

set -u

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
NATS_MONITOR_URL="${NATS_MONITOR_URL:-http://localhost:8222}"
TIMEOUT="${TIMEOUT:-30}"
CURL_TIMEOUT=5

# Track overall result
exit_code=0
checks_passed=0
checks_failed=0

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

# Print a PASS result for a check
pass_check() {
    echo "  [PASS] $1"
    checks_passed=$((checks_passed + 1))
}

# Print a FAIL result for a check and set exit code
fail_check() {
    echo "  [FAIL] $1"
    checks_failed=$((checks_failed + 1))
    exit_code=1
}

# Check if a command is available
has_command() {
    command -v "$1" >/dev/null 2>&1
}

# Parse a JSON field value using jq or grep fallback
# Usage: json_field "json_string" "field_name"
json_field() {
    local json="$1"
    local field="$2"
    if has_command jq; then
        echo "$json" | jq -r ".$field // empty" 2>/dev/null
    else
        # Fallback: extract value using grep + sed
        echo "$json" | grep -o "\"${field}\"[[:space:]]*:[[:space:]]*\"[^\"]*\"" \
            | sed 's/.*:[[:space:]]*"\(.*\)"/\1/' 2>/dev/null
    fi
}

# Parse a numeric JSON field using jq or grep fallback
json_num_field() {
    local json="$1"
    local field="$2"
    if has_command jq; then
        echo "$json" | jq -r ".$field // empty" 2>/dev/null
    else
        echo "$json" | grep -o "\"${field}\"[[:space:]]*:[[:space:]]*[0-9]*" \
            | sed 's/.*:[[:space:]]*//' 2>/dev/null
    fi
}

# ---------------------------------------------------------------------------
# Wait for NATS to be ready
# ---------------------------------------------------------------------------

echo "============================================="
echo "  NATS Server Verification"
echo "============================================="
echo ""
echo "Monitor URL: ${NATS_MONITOR_URL}"
echo "Timeout: ${TIMEOUT}s"
echo ""

# Wait for the monitoring endpoint to become available
echo "Waiting for NATS server to be ready..."
elapsed=0
while [ "$elapsed" -lt "$TIMEOUT" ]; do
    if curl -sS --max-time "$CURL_TIMEOUT" "${NATS_MONITOR_URL}/healthz" >/dev/null 2>&1; then
        echo "NATS server is responding."
        echo ""
        break
    fi
    sleep 1
    elapsed=$((elapsed + 1))
done

if [ "$elapsed" -ge "$TIMEOUT" ]; then
    echo ""
    fail_check "NATS server did not respond within ${TIMEOUT}s timeout"
    echo ""
    echo "============================================="
    echo "  Results: ${checks_passed} passed, ${checks_failed} failed"
    echo "============================================="
    exit 1
fi

# ---------------------------------------------------------------------------
# Check 1: Health endpoint responds
# ---------------------------------------------------------------------------
echo "--- Check 1: Health Endpoint ---"

health_response=$(curl -sS --max-time "$CURL_TIMEOUT" -o /dev/null -w "%{http_code}" "${NATS_MONITOR_URL}/healthz" 2>/dev/null)

if [ "$health_response" = "200" ]; then
    pass_check "Health endpoint returned HTTP 200"
else
    fail_check "Health endpoint returned HTTP ${health_response} (expected 200)"
fi
echo ""

# ---------------------------------------------------------------------------
# Check 2: JetStream is initialised
# ---------------------------------------------------------------------------
echo "--- Check 2: JetStream Status ---"

jsz_response=$(curl -sS --max-time "$CURL_TIMEOUT" "${NATS_MONITOR_URL}/jsz" 2>/dev/null)

if [ -n "$jsz_response" ]; then
    # Verify JetStream info contains memory and storage fields
    js_memory=$(json_num_field "$jsz_response" "memory")
    js_storage=$(json_num_field "$jsz_response" "store")

    if [ -n "$js_memory" ] || [ -n "$js_storage" ]; then
        pass_check "JetStream is initialised (memory/storage info present)"
    else
        # Try alternate field names
        js_config=$(echo "$jsz_response" | grep -c "config" 2>/dev/null || true)
        if [ "$js_config" -gt 0 ]; then
            pass_check "JetStream is initialised (config info present)"
        else
            fail_check "JetStream endpoint responded but missing memory/storage info"
        fi
    fi
else
    fail_check "JetStream endpoint (/jsz) did not respond"
fi
echo ""

# ---------------------------------------------------------------------------
# Check 3: Server name and version
# ---------------------------------------------------------------------------
echo "--- Check 3: Server Info ---"

varz_response=$(curl -sS --max-time "$CURL_TIMEOUT" "${NATS_MONITOR_URL}/varz" 2>/dev/null)

if [ -n "$varz_response" ]; then
    # Check server_name
    actual_server_name=$(json_field "$varz_response" "server_name")

    if [ "$actual_server_name" = "ships-computer" ]; then
        pass_check "server_name is 'ships-computer'"
    else
        fail_check "server_name is '${actual_server_name}' (expected 'ships-computer')"
    fi

    # Check version is reported
    actual_version=$(json_field "$varz_response" "version")

    if [ -n "$actual_version" ]; then
        pass_check "NATS server version: ${actual_version}"
    else
        fail_check "Server version not reported in /varz"
    fi
else
    fail_check "Server info endpoint (/varz) did not respond"
    fail_check "Cannot check server version — /varz unavailable"
fi
echo ""

# ---------------------------------------------------------------------------
# Check 4: Account authentication (optional — requires nats CLI)
# ---------------------------------------------------------------------------
echo "--- Check 4: Account Authentication (Optional) ---"

if has_command nats; then
    # Test APPMILLA account (rich user) if credentials are available
    if [ -n "${RICH_NATS_PASSWORD:-}" ]; then
        nats_pub_result=$(nats pub test.verify "verify" \
            --user rich --password "${RICH_NATS_PASSWORD}" \
            --server "nats://localhost:4222" \
            --timeout 3s 2>&1) || true

        if echo "$nats_pub_result" | grep -qi "published\|ok\|success"; then
            pass_check "APPMILLA user 'rich' can connect and publish"
        else
            fail_check "APPMILLA user 'rich' connection failed: ${nats_pub_result}"
        fi
    else
        echo "  [SKIP] APPMILLA auth — RICH_NATS_PASSWORD not set"
    fi

    # Test FINPROXY account (mark user) if credentials are available
    if [ -n "${MARK_NATS_PASSWORD:-}" ]; then
        nats_sub_result=$(nats pub finproxy.test.verify "verify" \
            --user mark --password "${MARK_NATS_PASSWORD}" \
            --server "nats://localhost:4222" \
            --timeout 3s 2>&1) || true

        if echo "$nats_sub_result" | grep -qi "published\|ok\|success"; then
            pass_check "FINPROXY user 'mark' can connect with scoped access"
        else
            fail_check "FINPROXY user 'mark' connection failed: ${nats_sub_result}"
        fi
    else
        echo "  [SKIP] FINPROXY auth — MARK_NATS_PASSWORD not set"
    fi
else
    echo "  [SKIP] Account authentication checks — nats CLI not installed"
    echo "         Install: https://github.com/nats-io/natscli"
fi
echo ""

# ---------------------------------------------------------------------------
# Check 5: JetStream streams provisioned (optional — requires nats CLI)
# ---------------------------------------------------------------------------
echo "--- Check 5: JetStream Streams (Optional) ---"

if has_command nats; then
    EXPECTED_STREAMS="PIPELINE AGENTS JARVIS NOTIFICATIONS SYSTEM FLEET FINPROXY"
    streams_ok=0
    streams_missing=0

    for stream in $EXPECTED_STREAMS; do
        if nats stream info "$stream" --server "${NATS_URL:-nats://localhost:4222}" --json >/dev/null 2>&1; then
            echo "  [OK] $stream"
            streams_ok=$((streams_ok + 1))
        else
            echo "  [MISSING] $stream"
            streams_missing=$((streams_missing + 1))
        fi
    done

    echo ""
    echo "  Streams: ${streams_ok} found, ${streams_missing} missing"

    if [ "$streams_missing" -gt 0 ]; then
        echo "  NOTE: Missing streams can be provisioned with: ./streams/provision-streams.sh"
    fi
else
    echo "  [SKIP] JetStream stream checks — nats CLI not installed"
    echo "         Install: https://github.com/nats-io/natscli"
fi
echo ""

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo "============================================="
echo "  Results: ${checks_passed} passed, ${checks_failed} failed"
echo "============================================="

if [ "$exit_code" -eq 0 ]; then
    echo "  All checks PASSED"
else
    echo "  Some checks FAILED — review output above"
fi

exit $exit_code
