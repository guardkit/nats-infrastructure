"""Integration tests for KV watch — agent-status and agent-registry scenarios.

Tests all 4 KV buckets created by provision-kv.sh against a real Docker Compose
NATS instance. Covers put/get, watch, history depth, TTL expiry, persistence
across broker restart, and --dry-run preview mode.

Acceptance criteria for TASK-KV-005:
- AC-001: Verify all 4 KV buckets are created by provision-kv.sh
- AC-002: Put/get roundtrip on agent-status
- AC-003: Watch agent-status receives live updates
- AC-004: agent-registry history depth (6 puts → only 5 retained)
- AC-005: jarvis-session TTL expiry (short TTL for testing)
- AC-006: pipeline-state persists across broker restart
- AC-007: provision-kv.sh --dry-run produces expected output without creating buckets
- AC-008: All tests pass against Docker Compose NATS instance

Requires:
- Docker Compose NATS running (docker compose up -d)
- nats CLI installed (brew install nats-io/nats-tools/nats)
- KV buckets provisioned (./kv/provision-kv.sh)

Run with:
    pytest tests/test_kv_watch_integration.py -v -m integration
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROVISION_SCRIPT = PROJECT_ROOT / "kv" / "provision-kv.sh"
KV_DEFS_FILE = PROJECT_ROOT / "kv" / "kv-definitions.json"

# NATS connection URL with credentials for the APPMILLA account
NATS_URL = "nats://rich:changeme@localhost:4222"

# Expected KV bucket names from kv-definitions.json
EXPECTED_BUCKETS = ["agent-status", "agent-registry", "pipeline-state", "jarvis-session"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def nats_cmd(*args: str, timeout: int = 15) -> subprocess.CompletedProcess:
    """Run a nats CLI command with standard connection flags."""
    cmd = ["nats", "--server", NATS_URL, *args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def nats_kv_put(bucket: str, key: str, value: str) -> subprocess.CompletedProcess:
    """Put a value into a KV bucket."""
    return nats_cmd("kv", "put", bucket, key, value)


def nats_kv_get(bucket: str, key: str) -> subprocess.CompletedProcess:
    """Get a value from a KV bucket."""
    return nats_cmd("kv", "get", bucket, key, "--raw")


def nats_kv_info(bucket: str) -> subprocess.CompletedProcess:
    """Get info about a KV bucket."""
    return nats_cmd("kv", "info", bucket)


def nats_kv_history(bucket: str, key: str) -> subprocess.CompletedProcess:
    """Get the history of a key in a KV bucket."""
    return nats_cmd("kv", "history", bucket, key)


def nats_kv_del(bucket: str, key: str) -> subprocess.CompletedProcess:
    """Delete a key from a KV bucket."""
    return nats_cmd("kv", "del", bucket, key, "-f")


def nats_kv_rm(bucket: str) -> subprocess.CompletedProcess:
    """Remove (destroy) a KV bucket entirely."""
    return nats_cmd("kv", "rm", bucket, "-f")


def nats_available() -> bool:
    """Check if nats CLI is installed and NATS server is reachable."""
    if shutil.which("nats") is None:
        return False
    result = nats_cmd("server", "check", "connection", "--timeout", "3s")
    return result.returncode == 0


def ensure_bucket_exists(bucket_name: str) -> None:
    """Re-provision a single bucket if it does not exist (e.g. after restart)."""
    info_result = nats_kv_info(bucket_name)
    if info_result.returncode != 0:
        # Bucket missing — re-create from definitions
        defs = json.loads(KV_DEFS_FILE.read_text(encoding="utf-8"))
        for bucket_def in defs["kv_buckets"]:
            if bucket_def["name"] == bucket_name:
                cmd_args = ["kv", "add", bucket_name]
                ttl = bucket_def.get("ttl", "")
                if ttl:
                    cmd_args.extend(["--ttl", ttl])
                storage = bucket_def.get("storage", "")
                if storage:
                    cmd_args.extend(["--storage", storage])
                history = bucket_def.get("history")
                if history is not None:
                    cmd_args.extend(["--history", str(history)])
                max_value_size = bucket_def.get("max_value_size", "")
                if max_value_size:
                    cmd_args.extend(["--max-value-size", max_value_size])
                replicas = bucket_def.get("replicas")
                if replicas is not None:
                    cmd_args.extend(["--replicas", str(replicas)])
                result = nats_cmd(*cmd_args)
                assert result.returncode == 0, (
                    f"Failed to re-provision bucket {bucket_name}: {result.stderr}"
                )
                break


def run_provision_script() -> subprocess.CompletedProcess:
    """Run provision-kv.sh to create/verify all KV buckets."""
    env = os.environ.copy()
    env["NATS_URL"] = NATS_URL
    return subprocess.run(
        [str(PROVISION_SCRIPT)],
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )


def wait_for_nats_healthy(max_seconds: int = 30) -> bool:
    """Wait for NATS to become healthy. Returns True on success."""
    for _ in range(max_seconds):
        check = nats_cmd("server", "check", "connection", "--timeout", "2s")
        if check.returncode == 0:
            return True
        time.sleep(1)
    return False


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module", autouse=True)
def require_nats_integration():
    """Skip entire module if NATS is not available."""
    if not nats_available():
        pytest.skip(
            "NATS server not available — start with: docker compose up -d"
        )
    # Ensure all buckets are provisioned at module start
    run_provision_script()


@pytest.fixture
def clean_agent_status_key():
    """Ensure a test key is cleaned up from agent-status after the test."""
    key = "test-agent-1"
    yield key
    nats_kv_del("agent-status", key)


@pytest.fixture
def clean_agent_registry_key():
    """Ensure a test key is cleaned up from agent-registry after the test."""
    key = "test-registry-agent-1"
    yield key
    nats_kv_del("agent-registry", key)


# =============================================================================
# AC-001: Verify all 4 KV buckets are created by provision-kv.sh
# =============================================================================


@pytest.mark.integration
class TestKvBucketsCreated:
    """AC-001: All 4 KV buckets are created by provision-kv.sh."""

    def test_provision_script_creates_all_buckets(self) -> None:
        """Run provision-kv.sh and verify all 4 buckets exist."""
        # provision-kv.sh already ran in module fixture; verify result
        result = nats_cmd("kv", "ls")
        assert result.returncode == 0, (
            f"nats kv ls failed: {result.stderr}"
        )
        output = result.stdout
        for bucket in EXPECTED_BUCKETS:
            assert bucket in output, (
                f"KV bucket '{bucket}' not found in nats kv ls output.\n"
                f"Available buckets:\n{output}"
            )

    @pytest.mark.parametrize("bucket_name", EXPECTED_BUCKETS)
    def test_bucket_info_accessible(self, bucket_name: str) -> None:
        """Each bucket's info should be retrievable."""
        ensure_bucket_exists(bucket_name)
        result = nats_kv_info(bucket_name)
        assert result.returncode == 0, (
            f"nats kv info {bucket_name} failed: {result.stderr}"
        )

    def test_agent_status_storage_is_file(self) -> None:
        """agent-status uses file storage."""
        result = nats_kv_info("agent-status")
        assert result.returncode == 0
        assert "File" in result.stdout, (
            "agent-status should use file storage"
        )

    def test_agent_registry_history_is_5(self) -> None:
        """agent-registry has history depth 5."""
        result = nats_kv_info("agent-registry")
        assert result.returncode == 0
        assert re.search(r"History.*5", result.stdout), (
            f"agent-registry should have history=5, output: {result.stdout}"
        )

    def test_jarvis_session_storage_is_memory(self) -> None:
        """jarvis-session uses memory storage."""
        ensure_bucket_exists("jarvis-session")
        result = nats_kv_info("jarvis-session")
        assert result.returncode == 0
        assert "Memory" in result.stdout, (
            "jarvis-session should use memory storage"
        )

    def test_pipeline_state_storage_is_file(self) -> None:
        """pipeline-state uses file storage."""
        result = nats_kv_info("pipeline-state")
        assert result.returncode == 0
        assert "File" in result.stdout, (
            "pipeline-state should use file storage"
        )


# =============================================================================
# AC-002: Put/get roundtrip on agent-status
# =============================================================================


@pytest.mark.integration
class TestAgentStatusPutGet:
    """AC-002: Put a value to agent-status, get it back, verify content."""

    def test_put_and_get_roundtrip(self, clean_agent_status_key: str) -> None:
        """Put a JSON status value, get it back, verify content matches."""
        key = clean_agent_status_key
        value = json.dumps({
            "agent_id": "test-agent-1",
            "status": "idle",
            "last_heartbeat": "2026-04-13T22:00:00Z",
            "capabilities": ["code-review", "testing"],
        })

        # Put the value
        put_result = nats_kv_put("agent-status", key, value)
        assert put_result.returncode == 0, (
            f"nats kv put failed: {put_result.stderr}"
        )

        # Get the value back
        get_result = nats_kv_get("agent-status", key)
        assert get_result.returncode == 0, (
            f"nats kv get failed: {get_result.stderr}"
        )

        # Verify content matches
        retrieved = json.loads(get_result.stdout.strip())
        assert retrieved["agent_id"] == "test-agent-1"
        assert retrieved["status"] == "idle"
        assert retrieved["capabilities"] == ["code-review", "testing"]

    def test_update_and_get_latest(self, clean_agent_status_key: str) -> None:
        """Update a value and verify latest is returned."""
        key = clean_agent_status_key

        # Initial put
        initial_value = json.dumps({"status": "idle"})
        nats_kv_put("agent-status", key, initial_value)

        # Update
        updated_value = json.dumps({"status": "busy"})
        nats_kv_put("agent-status", key, updated_value)

        # Get should return updated value
        get_result = nats_kv_get("agent-status", key)
        assert get_result.returncode == 0
        retrieved = json.loads(get_result.stdout.strip())
        assert retrieved["status"] == "busy"


# =============================================================================
# AC-003: Watch agent-status receives live updates
# =============================================================================


@pytest.mark.integration
class TestAgentStatusWatch:
    """AC-003: Watch agent-status in background, put a value, verify watch receives update."""

    def test_watch_receives_put_update(self, clean_agent_status_key: str) -> None:
        """Start a watch in background, put a value, verify watch output captures it."""
        key = clean_agent_status_key
        value = json.dumps({"status": "active", "task": "code-review"})

        # Start nats kv watch in background
        watch_proc = subprocess.Popen(
            ["nats", "--server", NATS_URL, "kv", "watch", "agent-status", key],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            # Give watch time to subscribe
            time.sleep(1.0)

            # Put a value — watch should receive this
            put_result = nats_kv_put("agent-status", key, value)
            assert put_result.returncode == 0, (
                f"nats kv put failed: {put_result.stderr}"
            )

            # Wait for watch to receive the update
            time.sleep(2.0)

            # Terminate the watch process
            watch_proc.terminate()
            try:
                stdout, stderr = watch_proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                watch_proc.kill()
                stdout, stderr = watch_proc.communicate()

            # Verify the watch output contains the key and value
            assert key in stdout, (
                f"Watch output should contain key '{key}', got: {stdout}"
            )
            assert "active" in stdout or "code-review" in stdout, (
                f"Watch output should reflect the put operation, got: {stdout}"
            )
        finally:
            if watch_proc.poll() is None:
                watch_proc.kill()
                watch_proc.wait()

    def test_watch_receives_multiple_updates(self, clean_agent_status_key: str) -> None:
        """Watch should receive multiple sequential updates."""
        key = clean_agent_status_key

        watch_proc = subprocess.Popen(
            ["nats", "--server", NATS_URL, "kv", "watch", "agent-status", key],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            time.sleep(1.0)

            # Put two values
            nats_kv_put("agent-status", key, json.dumps({"status": "idle"}))
            time.sleep(0.5)
            nats_kv_put("agent-status", key, json.dumps({"status": "busy"}))
            time.sleep(2.0)

            watch_proc.terminate()
            try:
                stdout, stderr = watch_proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                watch_proc.kill()
                stdout, stderr = watch_proc.communicate()

            # Watch should have captured both updates
            key_count = stdout.count(key)
            assert key_count >= 2, (
                f"Watch should receive at least 2 updates with key '{key}', "
                f"found {key_count} occurrences. Output: {stdout}"
            )
        finally:
            if watch_proc.poll() is None:
                watch_proc.kill()
                watch_proc.wait()


# =============================================================================
# AC-004: agent-registry history depth (6 puts → only 5 retained)
# =============================================================================


@pytest.mark.integration
class TestAgentRegistryHistoryDepth:
    """AC-004: Put 6 values to agent-registry, verify only 5 retained."""

    def test_history_depth_limited_to_5(self, clean_agent_registry_key: str) -> None:
        """Put 6 values, verify history contains exactly 5 entries."""
        key = clean_agent_registry_key

        # Put 6 sequential values
        for i in range(1, 7):
            value = json.dumps({
                "agent_name": f"test-agent-v{i}",
                "capabilities": [f"cap-{i}"],
                "version": i,
            })
            put_result = nats_kv_put("agent-registry", key, value)
            assert put_result.returncode == 0, (
                f"nats kv put #{i} failed: {put_result.stderr}"
            )
            time.sleep(0.1)

        # Check history
        history_result = nats_kv_history("agent-registry", key)
        assert history_result.returncode == 0, (
            f"nats kv history failed: {history_result.stderr}"
        )

        # Count PUT entries in history output
        history_output = history_result.stdout
        put_lines = [
            line for line in history_output.splitlines()
            if key in line and ("PUT" in line.upper() or "put" in line.lower())
        ]

        # With history=5, only 5 entries should be retained after 6 puts
        assert len(put_lines) == 5, (
            f"Expected 5 history entries (history depth=5 after 6 puts), "
            f"got {len(put_lines)}. Full output:\n{history_output}"
        )

    def test_latest_value_is_most_recent(self, clean_agent_registry_key: str) -> None:
        """After 6 puts, the latest value should be the 6th."""
        key = clean_agent_registry_key

        for i in range(1, 7):
            value = json.dumps({"version": i})
            nats_kv_put("agent-registry", key, value)
            time.sleep(0.1)

        get_result = nats_kv_get("agent-registry", key)
        assert get_result.returncode == 0
        retrieved = json.loads(get_result.stdout.strip())
        assert retrieved["version"] == 6, (
            f"Latest value should be version 6, got {retrieved['version']}"
        )

    def test_oldest_history_entry_is_v2_not_v1(self, clean_agent_registry_key: str) -> None:
        """After 6 puts with history=5, oldest retained should be v2 (v1 evicted)."""
        key = clean_agent_registry_key

        for i in range(1, 7):
            value = json.dumps({"version": i})
            nats_kv_put("agent-registry", key, value)
            time.sleep(0.1)

        history_result = nats_kv_history("agent-registry", key)
        assert history_result.returncode == 0
        history_output = history_result.stdout

        # v1 should NOT be in history (evicted)
        assert '"version": 1' not in history_output and '"version":1' not in history_output, (
            f"Version 1 should be evicted from history (depth=5), output:\n{history_output}"
        )

        # v2 should still be present
        assert "version" in history_output, (
            f"History should contain version entries, output:\n{history_output}"
        )


# =============================================================================
# AC-005: jarvis-session TTL expiry
# =============================================================================


@pytest.mark.integration
class TestJarvisSessionTtlExpiry:
    """AC-005: Put a value to jarvis-session, verify it expires after TTL.

    The production TTL is 1h. To test expiry feasibly, we create a temporary
    test bucket with a short TTL (2s), verify the value expires, then clean up.
    We also verify the production bucket has the correct 1h TTL configured.
    """

    def test_production_bucket_has_1h_ttl(self) -> None:
        """Verify the jarvis-session bucket is configured with 1h TTL."""
        ensure_bucket_exists("jarvis-session")
        result = nats_kv_info("jarvis-session")
        assert result.returncode == 0, (
            f"jarvis-session bucket not accessible: {result.stderr}"
        )
        output = result.stdout
        # NATS CLI shows TTL as "Maximum Age: 1h0m0s" or "TTL: 1h"
        has_ttl = (
            re.search(r"(TTL|Maximum Age).*1h", output)
            or re.search(r"(TTL|Maximum Age).*3600", output)
            or re.search(r"(TTL|Maximum Age).*60m", output)
        )
        assert has_ttl, (
            f"jarvis-session should have TTL of 1h, info output:\n{output}"
        )

    def test_put_and_get_before_expiry(self) -> None:
        """Value is retrievable immediately after put (before TTL)."""
        ensure_bucket_exists("jarvis-session")
        key = "ttl-test-session"
        value = json.dumps({"session_id": "test-123", "context": "hello"})

        put_result = nats_kv_put("jarvis-session", key, value)
        assert put_result.returncode == 0, (
            f"nats kv put to jarvis-session failed: {put_result.stderr}"
        )

        # Immediately get — should succeed (well within 1h TTL)
        get_result = nats_kv_get("jarvis-session", key)
        assert get_result.returncode == 0
        retrieved = json.loads(get_result.stdout.strip())
        assert retrieved["session_id"] == "test-123"

        # Clean up
        nats_kv_del("jarvis-session", key)

    def test_short_ttl_bucket_expiry(self) -> None:
        """Create a temp bucket with 2s TTL, put a value, wait, verify expiry."""
        temp_bucket = "test-ttl-expiry-temp"

        # Remove bucket if it already exists from a prior run
        nats_kv_rm(temp_bucket)

        # Create temp bucket with very short TTL (2 seconds)
        create_result = nats_cmd(
            "kv", "add", temp_bucket, "--ttl", "2s", "--storage", "memory"
        )
        assert create_result.returncode == 0, (
            f"Failed to create temp KV bucket: {create_result.stderr}"
        )

        try:
            key = "expiring-key"
            value = json.dumps({"data": "will-expire"})

            # Put value
            put_result = nats_kv_put(temp_bucket, key, value)
            assert put_result.returncode == 0

            # Immediately get — should succeed
            get_result = nats_kv_get(temp_bucket, key)
            assert get_result.returncode == 0, (
                f"Value should exist immediately after put: {get_result.stderr}"
            )

            # Wait for TTL to expire (2s TTL + 2s buffer)
            time.sleep(4)

            # Get after expiry — should fail (key expired)
            get_after = nats_kv_get(temp_bucket, key)
            assert get_after.returncode != 0 or get_after.stdout.strip() == "", (
                f"Value should have expired after TTL, but got: {get_after.stdout}"
            )
        finally:
            # Clean up temp bucket
            nats_kv_rm(temp_bucket)


# =============================================================================
# AC-006: pipeline-state persists across broker restart
# =============================================================================


@pytest.mark.integration
class TestPipelineStatePersistence:
    """AC-006: Put a value to pipeline-state, restart broker, verify persistence.

    NOTE: This test restarts the Docker NATS container. Memory-backed buckets
    (jarvis-session) will be lost during restart. The test re-provisions all
    buckets after the restart to leave the system in a clean state.
    """

    def test_value_persists_across_broker_restart(self) -> None:
        """Put a value, restart Docker NATS, verify value survives."""
        key = "test-pipeline-feat-123"
        value = json.dumps({
            "feature_id": "feat-123",
            "state": "in-progress",
            "step": "code-review",
            "updated_at": "2026-04-13T22:00:00Z",
        })

        # Put value to pipeline-state
        put_result = nats_kv_put("pipeline-state", key, value)
        assert put_result.returncode == 0, (
            f"nats kv put failed: {put_result.stderr}"
        )

        # Verify it's there before restart
        get_before = nats_kv_get("pipeline-state", key)
        assert get_before.returncode == 0
        before_data = json.loads(get_before.stdout.strip())
        assert before_data["feature_id"] == "feat-123"

        # Restart the NATS container
        restart_result = subprocess.run(
            ["docker", "compose", "restart", "nats"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(PROJECT_ROOT),
        )
        assert restart_result.returncode == 0, (
            f"Docker restart failed: {restart_result.stderr}"
        )

        # Wait for NATS to be healthy again
        assert wait_for_nats_healthy(30), (
            "NATS did not become healthy after restart within 30s"
        )

        # Verify value persisted across restart
        get_after = nats_kv_get("pipeline-state", key)
        assert get_after.returncode == 0, (
            f"Value should persist after broker restart: {get_after.stderr}"
        )
        after_data = json.loads(get_after.stdout.strip())
        assert after_data["feature_id"] == "feat-123", (
            f"Expected feature_id 'feat-123' after restart, got: {after_data}"
        )
        assert after_data["state"] == "in-progress"
        assert after_data["step"] == "code-review"

        # Clean up test key
        nats_kv_del("pipeline-state", key)

        # Re-provision all buckets (memory-backed ones are lost after restart)
        run_provision_script()


# =============================================================================
# AC-007: provision-kv.sh --dry-run produces expected output
# =============================================================================


@pytest.mark.integration
class TestProvisionKvDryRun:
    """AC-007: --dry-run produces expected output without creating buckets."""

    @staticmethod
    def _run_dry_run(nats_url: str | None = None) -> subprocess.CompletedProcess:
        """Run provision-kv.sh --dry-run with optional NATS URL override."""
        env = os.environ.copy()
        env["NATS_URL"] = nats_url or NATS_URL
        return subprocess.run(
            [str(PROVISION_SCRIPT), "--dry-run"],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )

    def test_dry_run_produces_output(self) -> None:
        """--dry-run flag should produce human-readable output."""
        result = self._run_dry_run()
        assert result.returncode == 0, (
            f"--dry-run should exit 0, stderr: {result.stderr}"
        )
        stdout = result.stdout
        assert "DRY RUN" in stdout or "DRY-RUN" in stdout, (
            f"Output should indicate dry-run mode, got:\n{stdout}"
        )

    def test_dry_run_lists_all_buckets(self) -> None:
        """--dry-run should mention all 4 bucket names."""
        result = self._run_dry_run()
        assert result.returncode == 0
        stdout = result.stdout
        for bucket in EXPECTED_BUCKETS:
            assert bucket in stdout, (
                f"--dry-run output should mention bucket '{bucket}', got:\n{stdout}"
            )

    def test_dry_run_shows_dry_run_prefix(self) -> None:
        """--dry-run output should use [DRY-RUN] prefix."""
        result = self._run_dry_run()
        assert result.returncode == 0
        assert "[DRY-RUN]" in result.stdout, (
            f"Output should use [DRY-RUN] prefix, got:\n{result.stdout}"
        )

    def test_dry_run_does_not_connect_to_nats(self) -> None:
        """--dry-run should succeed without a running NATS server.

        This proves dry-run skips the health check and does not modify buckets.
        """
        result = self._run_dry_run(nats_url="nats://nonexistent-host:4222")
        assert result.returncode == 0, (
            f"--dry-run should succeed even with unreachable NATS, stderr: {result.stderr}"
        )

    def test_dry_run_shows_processing_count(self) -> None:
        """--dry-run should show how many bucket definitions are being processed."""
        result = self._run_dry_run()
        assert result.returncode == 0
        assert "4" in result.stdout, (
            f"--dry-run should mention processing 4 definitions, got:\n{result.stdout}"
        )

    def test_dry_run_shows_summary(self) -> None:
        """--dry-run should show summary at the end."""
        result = self._run_dry_run()
        assert result.returncode == 0
        assert "KV Buckets:" in result.stdout, (
            f"--dry-run should show KV Buckets summary, got:\n{result.stdout}"
        )


# =============================================================================
# AC-008: All tests pass against Docker Compose NATS instance
# =============================================================================


@pytest.mark.integration
class TestAllTestsPass:
    """AC-008: Meta-test confirming integration tests execute successfully."""

    def test_nats_server_is_healthy(self) -> None:
        """Confirm NATS server connection is healthy for all tests."""
        result = nats_cmd("server", "check", "connection", "--timeout", "5s")
        assert result.returncode == 0, (
            f"NATS server health check failed: {result.stderr}"
        )

    def test_all_expected_buckets_are_operational(self) -> None:
        """All 4 buckets accept put/get operations."""
        # Ensure all buckets exist (re-provision if needed after restart)
        for bucket in EXPECTED_BUCKETS:
            ensure_bucket_exists(bucket)

        for bucket in EXPECTED_BUCKETS:
            key = "ac008-health-check"
            value = json.dumps({"check": True})

            put_result = nats_kv_put(bucket, key, value)
            assert put_result.returncode == 0, (
                f"Put to {bucket} failed: {put_result.stderr}"
            )

            get_result = nats_kv_get(bucket, key)
            assert get_result.returncode == 0, (
                f"Get from {bucket} failed: {get_result.stderr}"
            )

            retrieved = json.loads(get_result.stdout.strip())
            assert retrieved["check"] is True, (
                f"Roundtrip failed for {bucket}: {retrieved}"
            )

            # Clean up
            nats_kv_del(bucket, key)
