"""Tests for kv/provision-kv.sh — idempotent KV bucket provisioning.

Validates all acceptance criteria for TASK-KV-002:
- AC-001: kv/provision-kv.sh exists and is executable
- AC-002: Reads bucket definitions from kv/kv-definitions.json
- AC-003: Supports --dry-run flag for preview without modification
- AC-004: Idempotent: safe to run multiple times (checks if bucket exists before creating)
- AC-005: Waits for NATS health before provisioning (same pattern as streams)
- AC-006: Supports NATS_URL and NATS_CREDS environment variables
- AC-007: Prints summary: created/updated/current/errors counts
- AC-008: Prerequisite checks for jq and nats CLI
- AC-009: All modified files pass project-configured lint/format checks with zero errors
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
SCRIPT_FILE = PROJECT_ROOT / "kv" / "provision-kv.sh"
KV_DEFS_FILE = PROJECT_ROOT / "kv" / "kv-definitions.json"


@pytest.fixture
def script_text() -> str:
    """Read the provision-kv.sh script content."""
    assert SCRIPT_FILE.exists(), f"Script not found at {SCRIPT_FILE}"
    return SCRIPT_FILE.read_text(encoding="utf-8")


@pytest.fixture
def kv_defs() -> dict:
    """Load kv-definitions.json."""
    assert KV_DEFS_FILE.exists(), (
        f"kv-definitions.json not found at {KV_DEFS_FILE}"
    )
    return json.loads(KV_DEFS_FILE.read_text(encoding="utf-8"))


# =============================================================================
# AC-001: kv/provision-kv.sh exists and is executable
# =============================================================================


class TestScriptExistsAndExecutable:
    """AC-001: Script must exist at kv/provision-kv.sh and be executable."""

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

    def test_uses_set_euo_pipefail(self, script_text: str) -> None:
        assert re.search(r"set\s+-euo\s+pipefail", script_text), (
            "Script must use 'set -euo pipefail' for strict error handling"
        )


# =============================================================================
# AC-002: Reads bucket definitions from kv/kv-definitions.json
# =============================================================================


class TestReadsKvDefinitions:
    """AC-002: Script reads bucket definitions from kv/kv-definitions.json."""

    def test_reads_kv_definitions_json(self, script_text: str) -> None:
        """Script must reference kv-definitions.json."""
        assert re.search(r"kv-definitions\.json", script_text), (
            "Script must reference kv-definitions.json"
        )

    def test_uses_jq_to_parse(self, script_text: str) -> None:
        """Script must use jq to parse JSON."""
        assert re.search(r"\bjq\b", script_text), (
            "Script must use jq to parse kv-definitions.json"
        )

    def test_iterates_over_kv_buckets(self, script_text: str) -> None:
        """Script must iterate over .kv_buckets[] array."""
        assert re.search(r"\.kv_buckets", script_text), (
            "Script must iterate over .kv_buckets from JSON"
        )

    def test_extracts_bucket_name(self, script_text: str) -> None:
        """Script must extract the name field from each bucket definition."""
        assert re.search(r"kv_buckets\[.*\]\.name", script_text), (
            "Script must extract .name from each KV bucket definition"
        )

    def test_extracts_bucket_ttl(self, script_text: str) -> None:
        """Script must extract the ttl field from each bucket definition."""
        assert re.search(r"kv_buckets\[.*\]\.ttl", script_text), (
            "Script must extract .ttl from each KV bucket definition"
        )

    def test_extracts_bucket_storage(self, script_text: str) -> None:
        """Script must extract the storage field from each bucket definition."""
        assert re.search(r"kv_buckets\[.*\]\.storage", script_text), (
            "Script must extract .storage from each KV bucket definition"
        )

    def test_extracts_bucket_history(self, script_text: str) -> None:
        """Script must extract the history field from each bucket definition."""
        assert re.search(r"kv_buckets\[.*\]\.history", script_text), (
            "Script must extract .history from each KV bucket definition"
        )

    def test_extracts_bucket_max_value_size(self, script_text: str) -> None:
        """Script must extract the max_value_size field from each bucket definition."""
        assert re.search(r"kv_buckets\[.*\]\.max_value_size", script_text), (
            "Script must extract .max_value_size from each KV bucket definition"
        )

    def test_extracts_bucket_replicas(self, script_text: str) -> None:
        """Script must extract the replicas field from each bucket definition."""
        assert re.search(r"kv_buckets\[.*\]\.replicas", script_text), (
            "Script must extract .replicas from each KV bucket definition"
        )


# =============================================================================
# AC-003: Supports --dry-run flag for preview without modification
# =============================================================================


class TestDryRunFlag:
    """AC-003: --dry-run flag shows planned actions without modifying anything."""

    def test_supports_dry_run_flag(self, script_text: str) -> None:
        """Script must accept --dry-run flag."""
        assert re.search(r"--dry-run", script_text), (
            "Script must support --dry-run flag"
        )

    def test_dry_run_prevents_modification(self, script_text: str) -> None:
        """Script must check dry-run before executing nats commands."""
        has_dry_run_conditional = re.search(
            r"(DRY_RUN|dry_run|dryrun)", script_text, re.IGNORECASE
        )
        assert has_dry_run_conditional, (
            "Script must have a DRY_RUN variable or check to gate modifications"
        )

    def test_dry_run_shows_would_actions(self, script_text: str) -> None:
        """Script should indicate what would happen during dry-run."""
        assert re.search(r"\[DRY-RUN\]", script_text), (
            "Script must use [DRY-RUN] prefix to indicate planned actions"
        )

    def test_dry_run_skips_nats_health_wait(self, script_text: str) -> None:
        """Script must skip NATS health wait in dry-run mode."""
        assert re.search(r"DRY_RUN.*true", script_text), (
            "Script must check DRY_RUN to skip health wait"
        )


# =============================================================================
# AC-004: Idempotent: safe to run multiple times
# =============================================================================


class TestIdempotency:
    """AC-004: Script checks if bucket exists before creating."""

    def test_uses_nats_kv_info(self, script_text: str) -> None:
        """Script must use 'nats kv info' to check bucket existence."""
        assert re.search(r"nats\s+kv\s+info", script_text), (
            "Script must use 'nats kv info' to check KV bucket existence"
        )

    def test_uses_nats_kv_add(self, script_text: str) -> None:
        """Script must use 'nats kv add' for creating KV buckets."""
        assert re.search(r"nats\s+kv\s+add", script_text), (
            "Script must use 'nats kv add' to create KV buckets"
        )

    def test_uses_nats_kv_update(self, script_text: str) -> None:
        """Script must use 'nats kv update' for updating existing KV buckets."""
        assert re.search(r"nats\s+kv\s+update", script_text), (
            "Script must use 'nats kv update' to update existing KV buckets"
        )

    def test_has_provision_kv_bucket_function(self, script_text: str) -> None:
        """Script must have a provision_kv_bucket function."""
        assert re.search(r"provision_kv_bucket\(\)", script_text), (
            "Script must define a provision_kv_bucket() function"
        )

    def test_checks_existence_before_create(self, script_text: str) -> None:
        """nats kv info must appear before nats kv add in the provision function."""
        info_pos = script_text.find("nats kv info")
        add_pos = script_text.find("nats kv add")
        assert info_pos > 0, "Script must use 'nats kv info'"
        assert add_pos > 0, "Script must use 'nats kv add'"
        assert info_pos < add_pos, (
            "'nats kv info' check must come before 'nats kv add' in provision function"
        )


# =============================================================================
# AC-005: Waits for NATS health before provisioning
# =============================================================================


class TestNatsHealthCheck:
    """AC-005: Script waits for NATS health before provisioning."""

    def test_has_wait_for_nats_function(self, script_text: str) -> None:
        """Script must have a wait_for_nats function or health check loop."""
        assert re.search(r"wait_for_nats", script_text), (
            "Script must have a wait_for_nats function"
        )

    def test_has_retry_mechanism(self, script_text: str) -> None:
        """Script must have a retry/wait loop for NATS connectivity."""
        has_loop = re.search(r"\b(while|until)\b", script_text)
        assert has_loop, "Script must have a loop for retrying NATS health check"

    def test_has_timeout_for_health_check(self, script_text: str) -> None:
        """Script must have a timeout/max retry for health check."""
        assert re.search(r"MAX_RETRIES", script_text), (
            "Script must have a MAX_RETRIES limit to avoid infinite loop"
        )

    def test_uses_nats_server_check(self, script_text: str) -> None:
        """Script must use 'nats server check connection' for health check."""
        assert re.search(r"nats\s+server\s+check\s+connection", script_text), (
            "Script must use 'nats server check connection' for health check"
        )

    def test_fatal_exit_on_health_timeout(self, script_text: str) -> None:
        """Script must exit with error when health check times out."""
        assert re.search(r"\[FATAL\].*NATS.*not.*reachable", script_text), (
            "Script must log FATAL and exit when NATS is unreachable after retries"
        )


# =============================================================================
# AC-006: Supports NATS_URL and NATS_CREDS environment variables
# =============================================================================


class TestNatsConnectionConfig:
    """AC-006: Script supports NATS_URL and NATS_CREDS environment variables."""

    def test_supports_nats_url_env_var(self, script_text: str) -> None:
        """Script must support NATS_URL environment variable."""
        assert re.search(r"NATS_URL", script_text), (
            "Script must support NATS_URL environment variable"
        )

    def test_nats_url_default_localhost(self, script_text: str) -> None:
        """Script must default NATS_URL to nats://localhost:4222."""
        assert re.search(r"nats://localhost:4222", script_text), (
            "Script must default NATS_URL to nats://localhost:4222"
        )

    def test_supports_nats_creds_env_var(self, script_text: str) -> None:
        """Script must support NATS_CREDS environment variable."""
        assert re.search(r"NATS_CREDS", script_text), (
            "Script must support NATS_CREDS environment variable for credentials"
        )

    def test_nats_creds_is_optional(self, script_text: str) -> None:
        """NATS_CREDS must be optional (script works without it)."""
        has_optional_check = re.search(
            r"NATS_CREDS.*:-|if\s+.*NATS_CREDS|-n\s+.*NATS_CREDS|--creds", script_text
        )
        assert has_optional_check, "NATS_CREDS must be optional — use conditional logic"

    def test_builds_nats_opts_array(self, script_text: str) -> None:
        """Script must build a NATS_OPTS array for common CLI flags."""
        assert re.search(r"NATS_OPTS", script_text), (
            "Script must build a NATS_OPTS array for common CLI flags"
        )


# =============================================================================
# AC-007: Prints summary: created/updated/current/errors counts
# =============================================================================


class TestSummaryOutput:
    """AC-007: Script prints summary at end with counts."""

    def test_tracks_created_count(self, script_text: str) -> None:
        """Script must track count of created KV buckets."""
        assert re.search(r"\bcreated\b", script_text), (
            "Script must track created count"
        )

    def test_tracks_updated_count(self, script_text: str) -> None:
        """Script must track count of updated KV buckets."""
        assert re.search(r"\bupdated\b", script_text), (
            "Script must track updated count"
        )

    def test_tracks_current_count(self, script_text: str) -> None:
        """Script must track count of already-current KV buckets."""
        assert re.search(r"\bcurrent\b", script_text), (
            "Script must track already-current count"
        )

    def test_tracks_error_count(self, script_text: str) -> None:
        """Script must track count of errors."""
        assert re.search(r"\berrors\b", script_text), (
            "Script must track error count"
        )

    def test_prints_summary_line(self, script_text: str) -> None:
        """Script must print a summary line with all four counts."""
        assert re.search(
            r"created.*updated.*current.*error", script_text, re.IGNORECASE
        ), (
            "Script must print a summary with created, updated, current, and error counts"
        )

    def test_warns_on_errors(self, script_text: str) -> None:
        """Script must print a warning when errors occurred."""
        assert re.search(r"WARNING.*error", script_text, re.IGNORECASE), (
            "Script must warn when errors occurred"
        )


# =============================================================================
# AC-008: Prerequisite checks for jq and nats CLI
# =============================================================================


class TestPrerequisiteChecks:
    """AC-008: Script checks for jq and nats CLI prerequisites."""

    def test_checks_jq_available(self, script_text: str) -> None:
        """Script must check that jq is installed."""
        assert re.search(r"command\s+-v\s+jq", script_text), (
            "Script must check jq availability with 'command -v jq'"
        )

    def test_checks_nats_available(self, script_text: str) -> None:
        """Script must check that nats CLI is installed."""
        assert re.search(r"command\s+-v\s+nats", script_text), (
            "Script must check nats CLI availability with 'command -v nats'"
        )

    def test_fatal_exit_if_jq_missing(self, script_text: str) -> None:
        """Script must exit with FATAL error if jq is missing."""
        assert re.search(r"\[FATAL\].*jq", script_text), (
            "Script must log [FATAL] and exit if jq is not installed"
        )

    def test_fatal_exit_if_nats_missing(self, script_text: str) -> None:
        """Script must exit with FATAL error if nats CLI is missing."""
        assert re.search(r"\[FATAL\].*nats", script_text, re.IGNORECASE), (
            "Script must log [FATAL] and exit if nats CLI is not installed"
        )

    def test_checks_definitions_file_exists(self, script_text: str) -> None:
        """Script must check that kv-definitions.json exists."""
        assert re.search(r"-f.*KV_DEFS_FILE|KV_DEFS_FILE.*-f", script_text), (
            "Script must check kv-definitions.json file exists with -f test"
        )


# =============================================================================
# AC-009: Lint/format checks (shellcheck)
# =============================================================================


class TestShellcheck:
    """AC-009: Script passes shellcheck static analysis."""

    @pytest.fixture(autouse=True)
    def _require_shellcheck(self) -> None:
        """Skip tests in this class if shellcheck is not installed."""
        if shutil.which("shellcheck") is None:
            pytest.skip(
                "shellcheck not installed — install with: brew install shellcheck"
            )

    def test_script_passes_shellcheck(self) -> None:
        """provision-kv.sh must pass shellcheck with zero errors."""
        result = subprocess.run(
            ["shellcheck", "--severity=error", str(SCRIPT_FILE)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"shellcheck found errors in {SCRIPT_FILE.name}:\n{result.stdout}\n{result.stderr}"
        )

    def test_script_passes_shellcheck_warnings(self) -> None:
        """provision-kv.sh should pass shellcheck with warnings enabled."""
        result = subprocess.run(
            ["shellcheck", "--severity=warning", str(SCRIPT_FILE)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"shellcheck warnings in {SCRIPT_FILE.name}:\n{result.stdout}\n{result.stderr}"
        )


# =============================================================================
# Log format verification
# =============================================================================


class TestLogFormat:
    """Logs use prefixed format: [CREATE], [UPDATE], [OK], [ERROR], [DRY-RUN]."""

    def test_all_log_prefixes_present(self, script_text: str) -> None:
        """Script must use all standard log prefixes."""
        for prefix in ["[CREATE]", "[UPDATE]", "[OK]", "[ERROR]", "[DRY-RUN]"]:
            assert re.search(re.escape(prefix), script_text), (
                f"Script must use {prefix} log prefix"
            )

    def test_log_prefix_includes_bucket_name(self, script_text: str) -> None:
        """Log lines should include the bucket name after the prefix."""
        has_name_in_log = re.search(r"\[(CREATE|UPDATE|OK|ERROR)\].*\$", script_text)
        assert has_name_in_log, (
            "Log prefixes must be followed by the bucket name (via variable)"
        )


# =============================================================================
# KV-specific flag support
# =============================================================================


class TestKvFlagSupport:
    """Script supports all KV bucket configuration flags."""

    def test_supports_ttl_flag(self, script_text: str) -> None:
        """Script must support --ttl flag for KV bucket creation."""
        assert re.search(r"--ttl", script_text), (
            "Script must use --ttl flag for KV buckets with TTL"
        )

    def test_supports_history_flag(self, script_text: str) -> None:
        """Script must support --history flag for KV bucket creation."""
        assert re.search(r"--history", script_text), (
            "Script must use --history flag for KV bucket history"
        )

    def test_supports_storage_flag(self, script_text: str) -> None:
        """Script must support --storage flag for KV bucket creation."""
        assert re.search(r"--storage", script_text), (
            "Script must use --storage flag for KV bucket storage type"
        )

    def test_supports_max_value_size_flag(self, script_text: str) -> None:
        """Script must support --max-value-size flag."""
        assert re.search(r"--max-value-size", script_text), (
            "Script must use --max-value-size flag for KV bucket value size limit"
        )

    def test_supports_replicas_flag(self, script_text: str) -> None:
        """Script must support --replicas flag for KV bucket creation."""
        assert re.search(r"--replicas", script_text), (
            "Script must use --replicas flag for KV bucket replication"
        )

    def test_handles_empty_ttl(self, script_text: str) -> None:
        """Script must handle empty/null TTL (persistent buckets)."""
        assert re.search(r'(null|"null"|empty)', script_text), (
            "Script must handle null/empty TTL values for persistent buckets"
        )

    def test_ttl_is_conditional(self, script_text: str) -> None:
        """TTL flag must only be applied when TTL is non-empty."""
        assert re.search(r"ttl_opts", script_text), (
            "Script must conditionally apply TTL flags via ttl_opts array"
        )


# =============================================================================
# Script structure (matches provision-streams.sh pattern)
# =============================================================================


class TestScriptStructure:
    """Script follows the established pattern from provision-streams.sh."""

    def test_has_main_function(self, script_text: str) -> None:
        """Script must have a main() function."""
        assert re.search(r"\bmain\(\)", script_text), (
            "Script must define a main() function"
        )

    def test_calls_main_at_end(self, script_text: str) -> None:
        """Script must call main at the end."""
        lines = script_text.strip().splitlines()
        last_line = lines[-1].strip()
        assert last_line == "main", (
            f"Script must call main as the last line, got: '{last_line}'"
        )

    def test_has_exit_zero_on_success(self, script_text: str) -> None:
        """Script must exit 0 on success."""
        assert re.search(r"exit\s+0", script_text), "Script must exit 0 on success"

    def test_has_exit_nonzero_on_fatal(self, script_text: str) -> None:
        """Script must exit non-zero on fatal errors."""
        assert re.search(r"exit\s+[1-9]", script_text), (
            "Script must exit non-zero on fatal errors"
        )
