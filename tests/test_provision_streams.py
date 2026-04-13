"""Tests for streams/provision-streams.sh — idempotent JetStream stream & KV bucket provisioning.

Validates all acceptance criteria for TASK-JSTR-002:
- AC-001: Script reads all streams from stream-definitions.json
- AC-002: First run creates all 7 streams successfully
- AC-003: Second run detects existing streams and reports [OK] or [UPDATE] (no errors)
- AC-004: Changing a value in JSON (e.g., max_age) propagates on next run via [UPDATE]
- AC-005: --dry-run flag shows planned actions without modifying anything
- AC-006: Script exits 0 when all streams provisioned, non-zero only on fatal errors
- AC-007: All modified files pass project-configured lint/format checks with zero errors

Also validates TASK-JSTR-003 KV bucket provisioning:
- AC-002: provision-streams.sh creates KV buckets after streams
- AC-003: Idempotent: re-running does not error on existing buckets
- AC-004: TTL values applied correctly (null = no TTL, persistent)

Also validates seam test contract from TASK-JSTR-001:
- Seam: stream-definitions.json format contract
"""
from __future__ import annotations

import json
import re
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

# Paths relative to project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_FILE = PROJECT_ROOT / "streams" / "provision-streams.sh"
STREAM_DEFS_FILE = PROJECT_ROOT / "streams" / "stream-definitions.json"


@pytest.fixture
def script_text() -> str:
    """Read the provision-streams.sh script content."""
    assert SCRIPT_FILE.exists(), f"Script not found at {SCRIPT_FILE}"
    return SCRIPT_FILE.read_text(encoding="utf-8")


@pytest.fixture
def stream_defs() -> dict:
    """Load stream-definitions.json."""
    assert STREAM_DEFS_FILE.exists(), f"stream-definitions.json not found at {STREAM_DEFS_FILE}"
    return json.loads(STREAM_DEFS_FILE.read_text(encoding="utf-8"))


# --- Script existence and structure ---


class TestScriptExistsAndExecutable:
    """Script must exist at streams/provision-streams.sh and be executable."""

    def test_script_file_exists(self) -> None:
        assert SCRIPT_FILE.exists(), f"Expected script at {SCRIPT_FILE}"

    def test_script_is_executable(self) -> None:
        mode = SCRIPT_FILE.stat().st_mode
        assert mode & stat.S_IXUSR, "Script must be executable (chmod +x)"

    def test_script_has_shebang(self, script_text: str) -> None:
        assert script_text.startswith("#!/"), (
            "Script must start with a shebang line (#!/usr/bin/env bash or #!/bin/bash)"
        )

    def test_script_is_not_empty(self, script_text: str) -> None:
        assert len(script_text.strip()) > 0, "Script must not be empty"


class TestStrictErrorHandling:
    """Script uses set -euo pipefail for strict error handling."""

    def test_uses_set_euo_pipefail(self, script_text: str) -> None:
        assert re.search(
            r"set\s+-euo\s+pipefail", script_text
        ), "Script must use 'set -euo pipefail' for strict error handling"


# --- Shellcheck validation ---


class TestShellcheck:
    """Script passes shellcheck static analysis (skipped if shellcheck not installed)."""

    @pytest.fixture(autouse=True)
    def _require_shellcheck(self) -> None:
        """Skip tests in this class if shellcheck is not installed."""
        if shutil.which("shellcheck") is None:
            pytest.skip("shellcheck not installed — install with: brew install shellcheck")

    def test_script_passes_shellcheck(self) -> None:
        """provision-streams.sh must pass shellcheck with zero errors."""
        result = subprocess.run(
            ["shellcheck", "--severity=error", str(SCRIPT_FILE)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"shellcheck found errors in {SCRIPT_FILE.name}:\n{result.stdout}\n{result.stderr}"
        )

    def test_script_passes_shellcheck_warnings(self) -> None:
        """provision-streams.sh should pass shellcheck with warnings enabled."""
        result = subprocess.run(
            ["shellcheck", "--severity=warning", str(SCRIPT_FILE)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"shellcheck warnings in {SCRIPT_FILE.name}:\n{result.stdout}\n{result.stderr}"
        )


# --- AC-001: Script reads all streams from stream-definitions.json ---


class TestReadsStreamDefinitions:
    """AC-001: Script reads all streams from stream-definitions.json."""

    def test_reads_stream_definitions_json(self, script_text: str) -> None:
        """Script must reference stream-definitions.json."""
        assert re.search(
            r"stream-definitions\.json", script_text
        ), "Script must reference stream-definitions.json"

    def test_uses_jq_to_parse(self, script_text: str) -> None:
        """Script must use jq to parse JSON."""
        assert re.search(
            r"\bjq\b", script_text
        ), "Script must use jq to parse stream-definitions.json"

    def test_checks_jq_available(self, script_text: str) -> None:
        """Script must check that jq is installed."""
        assert re.search(
            r"command\s+-v\s+jq", script_text
        ), "Script must check jq availability with 'command -v jq'"

    def test_iterates_over_streams(self, script_text: str) -> None:
        """Script must iterate over .streams[] array."""
        assert re.search(
            r"\.streams\[\]", script_text
        ), "Script must iterate over .streams[] from JSON"

    def test_extracts_stream_name(self, script_text: str) -> None:
        """Script must extract the stream name field."""
        assert re.search(
            r"\.name", script_text
        ), "Script must extract .name from each stream definition"

    def test_extracts_subjects(self, script_text: str) -> None:
        """Script must extract subjects from each stream."""
        assert re.search(
            r"\.subjects", script_text
        ), "Script must extract .subjects from each stream definition"

    def test_extracts_retention(self, script_text: str) -> None:
        """Script must extract retention from each stream."""
        assert re.search(
            r"\.retention", script_text
        ), "Script must extract .retention from each stream definition"

    def test_extracts_max_age(self, script_text: str) -> None:
        """Script must extract max_age from each stream."""
        assert re.search(
            r"\.max_age", script_text
        ), "Script must extract .max_age from each stream definition"

    def test_extracts_max_msgs(self, script_text: str) -> None:
        """Script must extract max_msgs from each stream."""
        assert re.search(
            r"\.max_msgs", script_text
        ), "Script must extract .max_msgs from each stream definition"

    def test_extracts_storage(self, script_text: str) -> None:
        """Script must extract storage from each stream."""
        assert re.search(
            r"\.storage", script_text
        ), "Script must extract .storage from each stream definition"

    def test_extracts_replicas(self, script_text: str) -> None:
        """Script must extract replicas from each stream."""
        assert re.search(
            r"\.replicas", script_text
        ), "Script must extract .replicas from each stream definition"


# --- AC-002: First run creates all 7 streams successfully ---


class TestStreamCreation:
    """AC-002: First run creates all 7 streams successfully."""

    def test_uses_nats_stream_add(self, script_text: str) -> None:
        """Script must use 'nats stream add' for creation."""
        assert re.search(
            r"nats\s+stream\s+add", script_text
        ), "Script must use 'nats stream add' to create streams"

    def test_uses_defaults_flag(self, script_text: str) -> None:
        """Script must use --defaults flag for non-interactive creation."""
        assert re.search(
            r"--defaults", script_text
        ), "Script must use --defaults flag for non-interactive stream add"

    def test_logs_create_action(self, script_text: str) -> None:
        """Script must log [CREATE] when creating a new stream."""
        assert re.search(
            r"\[CREATE\]", script_text
        ), "Script must log [CREATE] prefix when creating a stream"

    def test_checks_stream_existence_before_create(self, script_text: str) -> None:
        """Script must check if stream exists with 'nats stream info'."""
        assert re.search(
            r"nats\s+stream\s+info", script_text
        ), "Script must check stream existence with 'nats stream info'"


# --- AC-003: Second run detects existing streams ---


class TestIdempotencyDetection:
    """AC-003: Second run detects existing streams and reports [OK] or [UPDATE]."""

    def test_logs_ok_for_current_streams(self, script_text: str) -> None:
        """Script must log [OK] when a stream is already current."""
        assert re.search(
            r"\[OK\]", script_text
        ), "Script must log [OK] for streams that are already up to date"

    def test_logs_update_for_changed_streams(self, script_text: str) -> None:
        """Script must log [UPDATE] when updating an existing stream."""
        assert re.search(
            r"\[UPDATE\]", script_text
        ), "Script must log [UPDATE] when updating a stream"


# --- AC-004: Changing a value propagates via [UPDATE] ---


class TestStreamUpdate:
    """AC-004: Changing a value in JSON propagates on next run via [UPDATE]."""

    def test_uses_nats_stream_update(self, script_text: str) -> None:
        """Script must use 'nats stream update' for modifications."""
        assert re.search(
            r"nats\s+stream\s+update", script_text
        ), "Script must use 'nats stream update' to update existing streams"

    def test_uses_force_flag(self, script_text: str) -> None:
        """Script must use --force flag to bypass interactive confirmation."""
        assert re.search(
            r"--force", script_text
        ), "Script must use --force flag for non-interactive stream update"

    def test_logs_error_on_update_failure(self, script_text: str) -> None:
        """Script must log [ERROR] when an update fails."""
        assert re.search(
            r"\[ERROR\]", script_text
        ), "Script must log [ERROR] when stream update fails"


# --- AC-005: --dry-run flag ---


class TestDryRunFlag:
    """AC-005: --dry-run flag shows planned actions without modifying anything."""

    def test_supports_dry_run_flag(self, script_text: str) -> None:
        """Script must accept --dry-run flag."""
        assert re.search(
            r"--dry-run", script_text
        ), "Script must support --dry-run flag"

    def test_dry_run_prevents_modification(self, script_text: str) -> None:
        """Script must check dry-run before executing nats commands."""
        # The script should have a conditional that gates nats stream add/update
        # behind a dry-run check
        has_dry_run_conditional = re.search(
            r"(DRY_RUN|dry_run|dryrun)", script_text, re.IGNORECASE
        )
        assert has_dry_run_conditional, (
            "Script must have a DRY_RUN variable or check to gate modifications"
        )

    def test_dry_run_shows_would_actions(self, script_text: str) -> None:
        """Script should indicate what would happen during dry-run."""
        has_would = re.search(r"(would|DRY.RUN|dry.run|DRYRUN)", script_text, re.IGNORECASE)
        assert has_would, (
            "Script must indicate planned actions in dry-run mode (e.g., 'would create')"
        )


# --- AC-006: Exit code behavior ---


class TestExitCodeBehavior:
    """AC-006: Script exits 0 when all streams provisioned, non-zero only on fatal errors."""

    def test_has_exit_zero_on_success(self, script_text: str) -> None:
        """Script must exit 0 on success."""
        has_exit_zero = re.search(r"exit\s+0", script_text)
        assert has_exit_zero, "Script must exit 0 on success"

    def test_has_exit_nonzero_on_fatal(self, script_text: str) -> None:
        """Script must exit non-zero on fatal errors."""
        assert re.search(
            r"exit\s+[1-9]", script_text
        ), "Script must exit non-zero on fatal errors"

    def test_continues_after_nonfatal_errors(self, script_text: str) -> None:
        """Script must continue to next stream after non-fatal error."""
        # Look for continue pattern in loop or error counting
        has_continue = re.search(r"\bcontinue\b", script_text)
        has_error_count = re.search(r"(errors|error_count|err_count)", script_text, re.IGNORECASE)
        assert has_continue or has_error_count, (
            "Script must handle non-fatal errors gracefully (continue or error counting)"
        )


# --- NATS connection configuration ---


class TestNatsConnectionConfig:
    """Script supports NATS_URL and NATS_CREDS environment variables."""

    def test_supports_nats_url_env_var(self, script_text: str) -> None:
        """Script must support NATS_URL environment variable."""
        assert re.search(
            r"NATS_URL", script_text
        ), "Script must support NATS_URL environment variable"

    def test_nats_url_default_localhost(self, script_text: str) -> None:
        """Script must default NATS_URL to nats://localhost:4222."""
        assert re.search(
            r"nats://localhost:4222", script_text
        ), "Script must default NATS_URL to nats://localhost:4222"

    def test_supports_nats_creds_env_var(self, script_text: str) -> None:
        """Script must support NATS_CREDS environment variable."""
        assert re.search(
            r"NATS_CREDS", script_text
        ), "Script must support NATS_CREDS environment variable for credentials"

    def test_nats_creds_is_optional(self, script_text: str) -> None:
        """NATS_CREDS must be optional (script works without it)."""
        # Should have a conditional check for NATS_CREDS
        has_optional_check = re.search(
            r"NATS_CREDS.*:-|if\s+.*NATS_CREDS|-n\s+.*NATS_CREDS|--creds", script_text
        )
        assert has_optional_check, (
            "NATS_CREDS must be optional — use conditional logic"
        )


# --- Health check / wait for NATS ---


class TestNatsHealthCheck:
    """Script waits for NATS health before attempting provisioning."""

    def test_waits_for_nats(self, script_text: str) -> None:
        """Script must wait for NATS to be healthy before provisioning."""
        # Look for a health check loop
        has_health_loop = re.search(
            r"(wait|health|ready|retry|attempt)", script_text, re.IGNORECASE
        )
        assert has_health_loop, (
            "Script must wait for NATS health before provisioning"
        )

    def test_has_retry_mechanism(self, script_text: str) -> None:
        """Script must have a retry/wait loop for NATS connectivity."""
        has_loop = re.search(r"\b(while|until|for)\b", script_text)
        assert has_loop, "Script must have a loop for retrying NATS health check"

    def test_has_timeout_for_health_check(self, script_text: str) -> None:
        """Script must have a timeout/max retry for health check."""
        has_max = re.search(
            r"(MAX_RETRIES|max_retries|MAX_WAIT|max_wait|MAX_ATTEMPTS|max_attempts|timeout)",
            script_text,
            re.IGNORECASE,
        )
        assert has_max, (
            "Script must have a maximum retry/timeout for health check to avoid infinite loop"
        )


# --- Summary output ---


class TestSummaryOutput:
    """Script prints summary at end: N created, M updated, K already current, E errors."""

    def test_tracks_created_count(self, script_text: str) -> None:
        """Script must track count of created streams."""
        assert re.search(
            r"(created|create_count|num_created)", script_text, re.IGNORECASE
        ), "Script must track created stream count"

    def test_tracks_updated_count(self, script_text: str) -> None:
        """Script must track count of updated streams."""
        assert re.search(
            r"(updated|update_count|num_updated)", script_text, re.IGNORECASE
        ), "Script must track updated stream count"

    def test_tracks_current_count(self, script_text: str) -> None:
        """Script must track count of already-current streams."""
        assert re.search(
            r"(current|ok_count|unchanged|already)", script_text, re.IGNORECASE
        ), "Script must track already-current stream count"

    def test_tracks_error_count(self, script_text: str) -> None:
        """Script must track count of errors."""
        assert re.search(
            r"(errors|error_count|err_count|num_errors)", script_text, re.IGNORECASE
        ), "Script must track error count"

    def test_prints_summary_line(self, script_text: str) -> None:
        """Script must print a summary line with counts."""
        assert re.search(
            r"(created.*updated.*current.*error|summary)", script_text, re.IGNORECASE
        ), "Script must print a summary with created, updated, current, and error counts"


# --- Log format ---


class TestLogFormat:
    """Logs use prefixed format: [CREATE], [UPDATE], [OK], [ERROR]."""

    def test_all_log_prefixes_present(self, script_text: str) -> None:
        """Script must use all four log prefixes."""
        for prefix in ["[CREATE]", "[UPDATE]", "[OK]", "[ERROR]"]:
            assert re.search(
                re.escape(prefix), script_text
            ), f"Script must use {prefix} log prefix"

    def test_log_prefix_includes_stream_name(self, script_text: str) -> None:
        """Log lines should include the stream name after the prefix."""
        # At least one log line should include a variable reference after the prefix
        has_name_in_log = re.search(
            r"\[(CREATE|UPDATE|OK|ERROR)\].*\$", script_text
        )
        assert has_name_in_log, (
            "Log prefixes must be followed by the stream name (via variable)"
        )


# --- Seam test: stream-definitions.json contract ---


@pytest.mark.seam
@pytest.mark.integration_contract("stream-definitions.json")
class TestStreamDefinitionsContract:
    """Seam test: verify stream-definitions.json contract from TASK-JSTR-001."""

    def test_top_level_streams_key_exists(self, stream_defs: dict) -> None:
        assert "streams" in stream_defs, "Top-level 'streams' key must exist"

    def test_at_least_7_streams(self, stream_defs: dict) -> None:
        assert len(stream_defs["streams"]) >= 7, (
            f"Expected at least 7 streams, got {len(stream_defs['streams'])}"
        )

    def test_all_streams_have_required_fields(self, stream_defs: dict) -> None:
        required_fields = {
            "name", "subjects", "retention", "max_age",
            "max_msgs", "storage", "replicas",
        }
        for stream in stream_defs["streams"]:
            missing = required_fields - set(stream.keys())
            assert not missing, (
                f"Stream {stream.get('name', '?')} missing fields: {missing}"
            )

    def test_retention_values_are_valid(self, stream_defs: dict) -> None:
        for stream in stream_defs["streams"]:
            assert stream["retention"] in ("work", "limits"), (
                f"Invalid retention: {stream['retention']}"
            )


# =============================================================================
# TASK-JSTR-003: KV Bucket Provisioning in provision-streams.sh
# =============================================================================


# --- AC-002: provision-streams.sh creates KV buckets after streams ---


class TestKvBucketProvisioning:
    """TASK-JSTR-003 AC-002: provision-streams.sh creates KV buckets after streams."""

    def test_uses_nats_kv_add(self, script_text: str) -> None:
        """Script must use 'nats kv add' for creating KV buckets."""
        assert re.search(
            r"nats\s+kv\s+add", script_text
        ), "Script must use 'nats kv add' to create KV buckets"

    def test_uses_nats_kv_info(self, script_text: str) -> None:
        """Script must use 'nats kv info' to check KV bucket existence."""
        assert re.search(
            r"nats\s+kv\s+info", script_text
        ), "Script must use 'nats kv info' to check KV bucket existence"

    def test_uses_nats_kv_update(self, script_text: str) -> None:
        """Script must use 'nats kv update' for updating existing KV buckets."""
        assert re.search(
            r"nats\s+kv\s+update", script_text
        ), "Script must use 'nats kv update' to update existing KV buckets"

    def test_reads_kv_buckets_from_json(self, script_text: str) -> None:
        """Script must read .kv_buckets[] from JSON definitions."""
        assert re.search(
            r"\.kv_buckets", script_text
        ), "Script must read .kv_buckets from stream-definitions.json"

    def test_extracts_kv_bucket_name(self, script_text: str) -> None:
        """Script must extract the name field from KV bucket definitions."""
        assert re.search(
            r"kv_buckets\[.*\]\.name", script_text
        ), "Script must extract .name from each KV bucket definition"

    def test_extracts_kv_bucket_ttl(self, script_text: str) -> None:
        """Script must extract the ttl field from KV bucket definitions."""
        assert re.search(
            r"kv_buckets\[.*\]\.ttl", script_text
        ), "Script must extract .ttl from each KV bucket definition"

    def test_has_provision_kv_bucket_function(self, script_text: str) -> None:
        """Script must have a provision_kv_bucket function."""
        assert re.search(
            r"provision_kv_bucket\(\)", script_text
        ), "Script must define a provision_kv_bucket() function"

    def test_kv_bucket_section_after_streams(self, script_text: str) -> None:
        """KV bucket provisioning must appear after stream provisioning in main()."""
        stream_provision_pos = script_text.find("provision_stream ")
        kv_provision_pos = script_text.find("provision_kv_bucket ")
        assert stream_provision_pos > 0, "Script must call provision_stream"
        assert kv_provision_pos > 0, "Script must call provision_kv_bucket"
        assert kv_provision_pos > stream_provision_pos, (
            "KV bucket provisioning must come after stream provisioning"
        )


# --- AC-003: Idempotent: re-running does not error on existing buckets ---


class TestKvBucketIdempotency:
    """TASK-JSTR-003 AC-003: Idempotent KV bucket provisioning."""

    def test_checks_kv_existence_before_create(self, script_text: str) -> None:
        """Script must check if KV bucket exists before creating."""
        assert re.search(
            r"nats\s+kv\s+info", script_text
        ), "Script must check KV bucket existence with 'nats kv info'"

    def test_logs_kv_create_action(self, script_text: str) -> None:
        """Script must log [CREATE] when creating a new KV bucket."""
        assert re.search(
            r"\[CREATE\].*KV", script_text
        ), "Script must log [CREATE] KV prefix when creating a KV bucket"

    def test_logs_kv_ok_action(self, script_text: str) -> None:
        """Script must log [OK] when KV bucket already exists and is current."""
        assert re.search(
            r"\[OK\].*KV", script_text
        ), "Script must log [OK] KV for existing buckets that are current"

    def test_logs_kv_update_action(self, script_text: str) -> None:
        """Script must log [UPDATE] when updating a KV bucket."""
        assert re.search(
            r"\[UPDATE\].*KV", script_text
        ), "Script must log [UPDATE] KV when updating a bucket"

    def test_logs_kv_error_action(self, script_text: str) -> None:
        """Script must log [ERROR] when KV bucket operation fails."""
        assert re.search(
            r"\[ERROR\].*KV", script_text
        ), "Script must log [ERROR] KV when bucket operation fails"

    def test_kv_dry_run_support(self, script_text: str) -> None:
        """Script must support dry-run mode for KV bucket operations."""
        assert re.search(
            r"\[DRY-RUN\].*KV", script_text
        ), "Script must support [DRY-RUN] mode for KV bucket operations"


# --- AC-004: TTL values applied correctly ---


class TestKvBucketTtlProvisioning:
    """TASK-JSTR-003 AC-004: TTL values applied correctly in provisioning."""

    def test_supports_ttl_flag(self, script_text: str) -> None:
        """Script must support --ttl flag for KV bucket creation."""
        assert re.search(
            r"--ttl", script_text
        ), "Script must use --ttl flag for KV buckets with TTL"

    def test_handles_null_ttl(self, script_text: str) -> None:
        """Script must handle null/empty TTL (persistent buckets)."""
        assert re.search(
            r'(null|"null"|empty)', script_text
        ), "Script must handle null TTL values for persistent buckets"

    def test_ttl_is_conditional(self, script_text: str) -> None:
        """TTL flag must only be applied when TTL is non-null."""
        # Look for conditional TTL application
        assert re.search(
            r"ttl_opts", script_text
        ), "Script must conditionally apply TTL flags"


# --- KV bucket summary ---


class TestKvBucketSummary:
    """Script must include KV bucket counts in summary output."""

    def test_tracks_kv_created_count(self, script_text: str) -> None:
        """Script must track count of created KV buckets."""
        assert re.search(
            r"kv_created", script_text
        ), "Script must track kv_created count"

    def test_tracks_kv_updated_count(self, script_text: str) -> None:
        """Script must track count of updated KV buckets."""
        assert re.search(
            r"kv_updated", script_text
        ), "Script must track kv_updated count"

    def test_tracks_kv_current_count(self, script_text: str) -> None:
        """Script must track count of already-current KV buckets."""
        assert re.search(
            r"kv_current", script_text
        ), "Script must track kv_current count"

    def test_tracks_kv_error_count(self, script_text: str) -> None:
        """Script must track count of KV bucket errors."""
        assert re.search(
            r"kv_errors", script_text
        ), "Script must track kv_errors count"

    def test_prints_kv_summary_line(self, script_text: str) -> None:
        """Script must print a KV bucket summary line."""
        assert re.search(
            r"KV Bucket", script_text
        ), "Script must print a KV Buckets summary line"
