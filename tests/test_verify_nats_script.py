"""Tests for TASK-NATS-004 — verify-nats.sh startup verification script.

Validates all acceptance criteria:
- AC-001: scripts/verify-nats.sh exists and is executable
- AC-002: Script checks NATS server health via port 8222 healthcheck
- AC-003: Script verifies JetStream is enabled via /jsz endpoint
- AC-004: Script verifies server_name is 'ships-computer' via /varz endpoint
- AC-005: Script reports clear PASS/FAIL for each check
- AC-006: Script exits with non-zero code if any check fails
- AC-007: Script works both locally and in CI (uses curl, no nats CLI dependency)
"""
from __future__ import annotations

import re
import stat
from pathlib import Path

import pytest

# Paths relative to project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_FILE = PROJECT_ROOT / "scripts" / "verify-nats.sh"


@pytest.fixture
def script_text() -> str:
    """Read the verify-nats.sh script content."""
    assert SCRIPT_FILE.exists(), f"Script not found at {SCRIPT_FILE}"
    return SCRIPT_FILE.read_text(encoding="utf-8")


# --- AC-001: scripts/verify-nats.sh exists and is executable ---


class TestScriptExists:
    """AC-001: scripts/verify-nats.sh exists and is executable."""

    def test_script_file_exists(self) -> None:
        assert SCRIPT_FILE.exists(), f"Expected script at {SCRIPT_FILE}"

    def test_script_is_executable(self) -> None:
        """Script must have executable permission."""
        mode = SCRIPT_FILE.stat().st_mode
        assert mode & stat.S_IXUSR, "Script must be executable (chmod +x)"

    def test_script_has_shebang(self, script_text: str) -> None:
        assert script_text.startswith("#!/"), (
            "Script must start with a shebang line (#!/bin/sh or #!/bin/bash)"
        )

    def test_script_is_not_empty(self, script_text: str) -> None:
        assert len(script_text.strip()) > 0, "Script must not be empty"


# --- AC-002: Script checks NATS server health via port 8222 healthcheck ---


class TestHealthCheck:
    """AC-002: Script checks NATS server health via port 8222 healthcheck."""

    def test_checks_healthz_endpoint(self, script_text: str) -> None:
        """Script must check the /healthz endpoint on port 8222."""
        assert re.search(
            r"localhost:8222/healthz", script_text
        ), "Script must check http://localhost:8222/healthz"

    def test_uses_curl_for_healthcheck(self, script_text: str) -> None:
        """Script must use curl to check the health endpoint."""
        assert re.search(
            r"curl.*healthz", script_text, re.DOTALL
        ), "Script must use curl to check health endpoint"


# --- AC-003: Script verifies JetStream is enabled via /jsz endpoint ---


class TestJetStreamVerification:
    """AC-003: Script verifies JetStream is enabled via /jsz endpoint."""

    def test_checks_jsz_endpoint(self, script_text: str) -> None:
        """Script must check the /jsz endpoint on port 8222."""
        # Script may use a variable (e.g., ${NATS_MONITOR_URL}/jsz) or literal URL
        has_literal = re.search(r"localhost:8222/jsz", script_text)
        has_endpoint = re.search(r"/jsz", script_text)
        has_port_ref = re.search(r"8222", script_text)
        assert has_endpoint and has_port_ref, (
            "Script must check the /jsz endpoint on port 8222 (literal or via variable)"
        )
        # Verify the default monitor URL references port 8222
        assert has_literal or has_port_ref, (
            "Script must reference port 8222 for monitoring"
        )

    def test_uses_curl_for_jetstream(self, script_text: str) -> None:
        """Script must use curl to check JetStream status."""
        assert re.search(
            r"curl.*jsz", script_text, re.DOTALL
        ), "Script must use curl for JetStream check"

    def test_validates_jetstream_info(self, script_text: str) -> None:
        """Script must validate that JetStream info is returned (not just HTTP 200)."""
        # Should check for JetStream-related content in the response
        has_memory_check = re.search(r"memory|mem", script_text, re.IGNORECASE)
        has_storage_check = re.search(r"store|storage", script_text, re.IGNORECASE)
        has_jetstream_keyword = re.search(r"JetStream|jetstream", script_text)
        assert has_memory_check or has_storage_check or has_jetstream_keyword, (
            "Script must validate JetStream info content (memory, storage, or JetStream keyword)"
        )


# --- AC-004: Script verifies server_name is 'ships-computer' via /varz endpoint ---


class TestServerNameVerification:
    """AC-004: Script verifies server_name is 'ships-computer' via /varz endpoint."""

    def test_checks_varz_endpoint(self, script_text: str) -> None:
        """Script must check the /varz endpoint on port 8222."""
        # Script may use a variable (e.g., ${NATS_MONITOR_URL}/varz) or literal URL
        has_endpoint = re.search(r"/varz", script_text)
        has_port_ref = re.search(r"8222", script_text)
        assert has_endpoint and has_port_ref, (
            "Script must check the /varz endpoint on port 8222 (literal or via variable)"
        )

    def test_uses_curl_for_server_info(self, script_text: str) -> None:
        """Script must use curl to check server info."""
        assert re.search(
            r"curl.*varz", script_text, re.DOTALL
        ), "Script must use curl for server info check"

    def test_checks_server_name_ships_computer(self, script_text: str) -> None:
        """Script must verify server_name is 'ships-computer'."""
        assert re.search(
            r"ships-computer", script_text
        ), "Script must check for server_name 'ships-computer'"

    def test_checks_server_name_field(self, script_text: str) -> None:
        """Script must specifically check the server_name field."""
        assert re.search(
            r"server_name", script_text
        ), "Script must check 'server_name' field from /varz"


# --- AC-005: Script reports clear PASS/FAIL for each check ---


class TestPassFailReporting:
    """AC-005: Script reports clear PASS/FAIL for each check."""

    def test_reports_pass(self, script_text: str) -> None:
        """Script must output PASS for successful checks."""
        assert re.search(
            r"PASS", script_text
        ), "Script must report PASS for successful checks"

    def test_reports_fail(self, script_text: str) -> None:
        """Script must output FAIL for failed checks."""
        assert re.search(
            r"FAIL", script_text
        ), "Script must report FAIL for failed checks"

    def test_pass_and_fail_used_in_output(self, script_text: str) -> None:
        """PASS and FAIL should be used in echo/printf statements."""
        pass_in_output = re.search(r'(echo|printf).*PASS', script_text)
        fail_in_output = re.search(r'(echo|printf).*FAIL', script_text)
        assert pass_in_output, "PASS must appear in echo/printf output"
        assert fail_in_output, "FAIL must appear in echo/printf output"

    def test_reports_multiple_checks(self, script_text: str) -> None:
        """Script should report PASS/FAIL for each individual check."""
        # Count PASS/FAIL reporting via echo/printf or helper function calls
        # Helper functions like pass_check/fail_check that wrap echo also count
        pass_direct = len(re.findall(r'(echo|printf).*PASS', script_text))
        fail_direct = len(re.findall(r'(echo|printf).*FAIL', script_text))
        pass_calls = len(re.findall(r'pass_check\s+"', script_text))
        fail_calls = len(re.findall(r'fail_check\s+"', script_text))
        total_pass = pass_direct + pass_calls
        total_fail = fail_direct + fail_calls
        assert total_pass >= 3, (
            f"Script should have at least 3 PASS outputs for different checks, found {total_pass}"
        )
        assert total_fail >= 3, (
            f"Script should have at least 3 FAIL outputs for different checks, found {total_fail}"
        )


# --- AC-006: Script exits with non-zero code if any check fails ---


class TestExitCode:
    """AC-006: Script exits with non-zero code if any check fails."""

    def test_has_exit_with_non_zero(self, script_text: str) -> None:
        """Script must contain exit with non-zero code for failures."""
        assert re.search(
            r"exit\s+[1-9]", script_text
        ), "Script must exit with non-zero code on failure"

    def test_tracks_failure_state(self, script_text: str) -> None:
        """Script must track overall pass/fail state across checks."""
        # Should have a variable tracking failures
        has_failure_var = re.search(
            r"(fail|error|result|status|exit_code|rc)\s*=", script_text, re.IGNORECASE
        )
        assert has_failure_var, (
            "Script must track failure state with a variable (e.g., failures=0)"
        )

    def test_has_exit_zero_on_success(self, script_text: str) -> None:
        """Script must exit 0 when all checks pass."""
        # Script may use exit 0, exit "$var", or exit $var
        has_exit_zero = re.search(r"exit\s+0", script_text)
        has_exit_var = re.search(r'exit\s+[\$"]', script_text)
        assert has_exit_zero or has_exit_var, (
            "Script must have a success exit path (exit 0 or exit via variable)"
        )


# --- AC-007: Script works locally and in CI (uses curl, no nats CLI dependency) ---


class TestCurlBasedNoNatsCLI:
    """AC-007: Script works locally and in CI (uses curl, no nats CLI dependency)."""

    def test_uses_curl_command(self, script_text: str) -> None:
        """Script must use curl for HTTP checks."""
        assert re.search(
            r"\bcurl\b", script_text
        ), "Script must use curl for HTTP requests"

    def test_does_not_require_nats_cli(self, script_text: str) -> None:
        """Core checks must not require the nats CLI tool."""
        # The nats CLI may be used optionally for auth checks, but core checks must use curl
        # Count curl-based checks vs nats CLI requirements
        curl_checks = len(re.findall(r"\bcurl\b", script_text))
        assert curl_checks >= 3, (
            f"Script must use curl for at least 3 core checks (health, JetStream, server info), found {curl_checks}"
        )

    def test_optional_nats_cli_for_auth(self, script_text: str) -> None:
        """If nats CLI is used for auth, it must be optional with skip message."""
        # If the script mentions the nats CLI at all, it must have a skip/check pattern
        if re.search(r"\bnats\b.*\b(pub|sub|connect|req)\b", script_text):
            has_command_check = re.search(
                r"command\s+-v\s+nats|which\s+nats|type\s+nats", script_text
            )
            has_skip_message = re.search(
                r"(skip|not installed|not found|not available)", script_text, re.IGNORECASE
            )
            assert has_command_check or has_skip_message, (
                "nats CLI usage must be gated behind availability check with skip message"
            )


# --- Timeout and robustness ---


class TestTimeoutAndRobustness:
    """Script should handle timeouts and be robust."""

    def test_has_timeout_mechanism(self, script_text: str) -> None:
        """Script should have a timeout mechanism for NATS startup."""
        has_timeout = re.search(r"timeout|TIMEOUT|--max-time|--connect-timeout|-m\s+\d", script_text)
        assert has_timeout, (
            "Script must have a timeout mechanism (curl --max-time, --connect-timeout, or timeout variable)"
        )

    def test_has_set_options(self, script_text: str) -> None:
        """Script should use set -e or set -u for robustness."""
        has_set_e = re.search(r"set\s+-[eu]", script_text)
        # Note: set -e may conflict with failure tracking, so set -u alone is acceptable
        # Or the script may manually handle errors
        has_error_handling = re.search(
            r"set\s+-|trap\s+", script_text
        )
        assert has_error_handling, (
            "Script should use 'set' options or 'trap' for robustness"
        )

    def test_has_explanatory_comments(self, script_text: str) -> None:
        """Script should have comments explaining what it does."""
        comment_lines = [
            line for line in script_text.splitlines() if line.strip().startswith("#")
        ]
        assert len(comment_lines) >= 5, (
            f"Script should have at least 5 comment lines for clarity, found {len(comment_lines)}"
        )

    def test_uses_curl_silent_mode(self, script_text: str) -> None:
        """Script should use curl -s or -sS for clean output."""
        assert re.search(
            r"curl\s+.*-[sS]", script_text
        ) or re.search(
            r"curl\s+-[sS]", script_text
        ), "Script should use curl in silent mode (-s or -sS) for clean output"

    def test_reports_version(self, script_text: str) -> None:
        """Script should report the NATS server version."""
        assert re.search(
            r"version", script_text, re.IGNORECASE
        ), "Script should report the NATS server version"
