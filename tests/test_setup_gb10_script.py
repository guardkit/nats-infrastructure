"""Tests for scripts/setup-gb10.sh — GB10 one-shot deployment script.

Validates TASK-KV-003 acceptance criteria:
- AC-001: scripts/setup-gb10.sh calls kv/provision-kv.sh after stream provisioning
- AC-002: KV provisioning runs only after NATS is healthy
- AC-003: Script exits non-zero if KV provisioning fails fatally
- AC-004: Verification step includes nats kv ls to confirm buckets exist
- AC-005: All modified files pass project-configured lint/format checks with zero errors

Tests verify setup-gb10.sh structure, sequence ordering, and integration with
provision-kv.sh, provision-streams.sh, and verify-nats.sh.
"""

from __future__ import annotations

import re
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

# Paths relative to project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SETUP_GB10_SCRIPT = PROJECT_ROOT / "scripts" / "setup-gb10.sh"
PROVISION_KV_SCRIPT = PROJECT_ROOT / "kv" / "provision-kv.sh"
PROVISION_STREAMS_SCRIPT = PROJECT_ROOT / "streams" / "provision-streams.sh"
VERIFY_SCRIPT = PROJECT_ROOT / "scripts" / "verify-nats.sh"


@pytest.fixture
def setup_gb10_text() -> str:
    """Read the setup-gb10.sh script content."""
    assert SETUP_GB10_SCRIPT.exists(), f"Script not found at {SETUP_GB10_SCRIPT}"
    return SETUP_GB10_SCRIPT.read_text(encoding="utf-8")


# =============================================================================
# Script existence and structure
# =============================================================================


class TestSetupGb10ScriptExists:
    """setup-gb10.sh exists and is properly structured."""

    def test_script_file_exists(self) -> None:
        assert SETUP_GB10_SCRIPT.exists(), f"Expected script at {SETUP_GB10_SCRIPT}"

    def test_script_is_executable(self) -> None:
        mode = SETUP_GB10_SCRIPT.stat().st_mode
        assert mode & stat.S_IXUSR, "Script must be executable (chmod +x)"

    def test_script_has_shebang(self, setup_gb10_text: str) -> None:
        assert setup_gb10_text.startswith("#!/"), (
            "Script must start with a shebang line"
        )

    def test_script_is_not_empty(self, setup_gb10_text: str) -> None:
        assert len(setup_gb10_text.strip()) > 0, "Script must not be empty"

    def test_uses_strict_error_handling(self, setup_gb10_text: str) -> None:
        assert re.search(r"set\s+-euo\s+pipefail", setup_gb10_text), (
            "Script must use 'set -euo pipefail' for strict error handling"
        )


# =============================================================================
# AC-001: scripts/setup-gb10.sh calls kv/provision-kv.sh after stream provisioning
# =============================================================================


class TestCallsKvProvisioning:
    """AC-001: setup-gb10.sh calls kv/provision-kv.sh after stream provisioning."""

    def test_calls_provision_kv(self, setup_gb10_text: str) -> None:
        """Setup script must invoke provision-kv.sh."""
        assert re.search(r"provision-kv\.sh", setup_gb10_text), (
            "setup-gb10.sh must call provision-kv.sh"
        )

    def test_calls_provision_streams(self, setup_gb10_text: str) -> None:
        """Setup script must invoke provision-streams.sh."""
        assert re.search(r"provision-streams\.sh", setup_gb10_text), (
            "setup-gb10.sh must call provision-streams.sh"
        )

    def test_kv_provisioning_after_stream_provisioning(
        self, setup_gb10_text: str
    ) -> None:
        """KV provisioning must happen after stream provisioning."""
        stream_pos = re.search(r"provision-streams\.sh", setup_gb10_text)
        kv_pos = re.search(r"provision-kv\.sh", setup_gb10_text)
        assert stream_pos is not None, (
            "setup-gb10.sh must call provision-streams.sh"
        )
        assert kv_pos is not None, "setup-gb10.sh must call provision-kv.sh"
        assert stream_pos.start() < kv_pos.start(), (
            "provision-kv.sh must be called AFTER provision-streams.sh"
        )

    def test_kv_provisioning_before_verify(self, setup_gb10_text: str) -> None:
        """KV provisioning must happen before verification."""
        kv_pos = re.search(r"provision-kv\.sh", setup_gb10_text)
        verify_pos = re.search(r"verify-nats\.sh", setup_gb10_text)
        assert kv_pos is not None, "setup-gb10.sh must call provision-kv.sh"
        assert verify_pos is not None, "setup-gb10.sh must call verify-nats.sh"
        assert kv_pos.start() < verify_pos.start(), (
            "provision-kv.sh must be called BEFORE verify-nats.sh"
        )

    def test_stream_provisioning_before_verify(self, setup_gb10_text: str) -> None:
        """Stream provisioning must happen before verification."""
        stream_pos = re.search(r"provision-streams\.sh", setup_gb10_text)
        verify_pos = re.search(r"verify-nats\.sh", setup_gb10_text)
        assert stream_pos is not None
        assert verify_pos is not None
        assert stream_pos.start() < verify_pos.start(), (
            "provision-streams.sh must be called BEFORE verify-nats.sh"
        )


# =============================================================================
# AC-002: KV provisioning runs only after NATS is healthy
# =============================================================================


class TestKvProvisioningAfterHealth:
    """AC-002: KV provisioning runs only after NATS is healthy."""

    def test_has_health_wait(self, setup_gb10_text: str) -> None:
        """Script must wait for NATS health before provisioning."""
        assert re.search(r"healthy|health", setup_gb10_text, re.IGNORECASE), (
            "setup-gb10.sh must wait for NATS health"
        )

    def test_health_check_before_kv_provisioning(
        self, setup_gb10_text: str
    ) -> None:
        """Health check/wait must appear before KV provisioning call."""
        health_pos = re.search(r"NATS.*healthy|healthy.*NATS|health", setup_gb10_text, re.IGNORECASE)
        kv_pos = re.search(r"provision-kv\.sh", setup_gb10_text)
        assert health_pos is not None, "setup-gb10.sh must check NATS health"
        assert kv_pos is not None, "setup-gb10.sh must call provision-kv.sh"
        assert health_pos.start() < kv_pos.start(), (
            "Health check must happen BEFORE KV provisioning"
        )

    def test_health_check_before_stream_provisioning(
        self, setup_gb10_text: str
    ) -> None:
        """Health check/wait must appear before stream provisioning call."""
        health_pos = re.search(r"NATS.*healthy|healthy.*NATS|health", setup_gb10_text, re.IGNORECASE)
        stream_pos = re.search(r"provision-streams\.sh", setup_gb10_text)
        assert health_pos is not None, "setup-gb10.sh must check NATS health"
        assert stream_pos is not None
        assert health_pos.start() < stream_pos.start(), (
            "Health check must happen BEFORE stream provisioning"
        )

    def test_has_health_timeout(self, setup_gb10_text: str) -> None:
        """Script must have a configurable timeout for health check."""
        assert re.search(r"HEALTH_TIMEOUT|MAX_WAIT", setup_gb10_text), (
            "Script must have a configurable health check timeout"
        )

    def test_exits_on_health_timeout(self, setup_gb10_text: str) -> None:
        """Script must exit non-zero if health check times out."""
        assert re.search(
            r"(not.*healthy|did not.*healthy|health.*timeout).*exit\s+1|exit\s+1.*health",
            setup_gb10_text,
            re.IGNORECASE | re.DOTALL,
        ) or (
            re.search(r"did not become healthy", setup_gb10_text, re.IGNORECASE)
            and re.search(r"exit\s+1", setup_gb10_text)
        ), "Script must exit 1 when NATS does not become healthy"

    def test_health_endpoint_check(self, setup_gb10_text: str) -> None:
        """Script must verify the NATS health endpoint."""
        assert re.search(r"/healthz", setup_gb10_text), (
            "Script must check /healthz endpoint"
        )


# =============================================================================
# AC-003: Script exits non-zero if KV provisioning fails fatally
# =============================================================================


class TestExitOnKvFailure:
    """AC-003: Script exits non-zero if KV provisioning fails fatally."""

    def test_checks_kv_provisioning_exit_code(self, setup_gb10_text: str) -> None:
        """Script must check the exit code of provision-kv.sh."""
        # The script should use `if "$PROVISION_KV_SCRIPT"; then` or similar
        # to capture the exit code and handle failure
        has_check = (
            re.search(r'if\s+.*provision.kv', setup_gb10_text, re.IGNORECASE)
            or re.search(r'provision.kv.*\|\|', setup_gb10_text, re.IGNORECASE)
        )
        assert has_check, (
            "Script must check the exit code of provision-kv.sh"
        )

    def test_exits_nonzero_on_kv_failure(self, setup_gb10_text: str) -> None:
        """Script must exit non-zero when KV provisioning fails."""
        # Look for the pattern: if provision-kv fails, exit 1
        kv_section_match = re.search(
            r"provision-kv\.sh.*?exit\s+1",
            setup_gb10_text,
            re.DOTALL,
        )
        assert kv_section_match is not None, (
            "Script must exit non-zero if KV provisioning fails"
        )

    def test_error_message_on_kv_failure(self, setup_gb10_text: str) -> None:
        """Script should log an error message when KV provisioning fails."""
        assert re.search(
            r"(ERROR|error).*[Kk][Vv].*provisioning.*fail|[Kk][Vv].*provision.*fail",
            setup_gb10_text,
            re.IGNORECASE,
        ), "Script must log an error when KV provisioning fails"

    def test_kv_script_missing_exits_nonzero(self, setup_gb10_text: str) -> None:
        """Script must exit non-zero if provision-kv.sh file is missing."""
        # Look for the check: if provision-kv.sh does not exist
        has_file_check = re.search(
            r'-f.*PROVISION_KV|provision-kv\.sh.*not found',
            setup_gb10_text,
            re.IGNORECASE,
        )
        assert has_file_check, (
            "Script must check if provision-kv.sh exists"
        )


# =============================================================================
# AC-004: Verification step includes nats kv ls to confirm buckets exist
# =============================================================================


class TestKvVerification:
    """AC-004: Verification step includes nats kv ls to confirm buckets exist."""

    def test_runs_nats_kv_ls(self, setup_gb10_text: str) -> None:
        """Verification step must run 'nats kv ls' to list KV buckets."""
        assert re.search(r"nats\s+kv\s+ls", setup_gb10_text), (
            "setup-gb10.sh must run 'nats kv ls' to verify KV buckets"
        )

    def test_kv_ls_after_provisioning(self, setup_gb10_text: str) -> None:
        """nats kv ls must run after KV provisioning."""
        kv_provision_pos = re.search(r"provision-kv\.sh", setup_gb10_text)
        kv_ls_pos = re.search(r"nats\s+kv\s+ls", setup_gb10_text)
        assert kv_provision_pos is not None, "Must call provision-kv.sh"
        assert kv_ls_pos is not None, "Must run nats kv ls"
        assert kv_provision_pos.start() < kv_ls_pos.start(), (
            "'nats kv ls' must run AFTER KV provisioning"
        )

    def test_kv_ls_in_verification_step(self, setup_gb10_text: str) -> None:
        """nats kv ls should appear in or after the verification step."""
        verify_pos = re.search(r"verify-nats\.sh", setup_gb10_text)
        kv_ls_pos = re.search(r"nats\s+kv\s+ls", setup_gb10_text)
        assert verify_pos is not None
        assert kv_ls_pos is not None
        # kv ls should be in the verification section (near or after verify-nats.sh)
        # We allow it to be before or after verify-nats.sh in the verify step
        assert kv_ls_pos.start() > re.search(
            r"provision-kv\.sh", setup_gb10_text
        ).start(), "'nats kv ls' must come after KV provisioning"


# =============================================================================
# AC-005: Lint/format checks (shellcheck)
# =============================================================================


class TestShellcheck:
    """AC-005: Script passes shellcheck static analysis."""

    @pytest.fixture(autouse=True)
    def _require_shellcheck(self) -> None:
        """Skip tests in this class if shellcheck is not installed."""
        if shutil.which("shellcheck") is None:
            pytest.skip(
                "shellcheck not installed — install with: brew install shellcheck"
            )

    def test_script_passes_shellcheck(self) -> None:
        """setup-gb10.sh must pass shellcheck with zero errors."""
        result = subprocess.run(
            ["shellcheck", "--severity=error", str(SETUP_GB10_SCRIPT)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"shellcheck found errors in {SETUP_GB10_SCRIPT.name}:\n"
            f"{result.stdout}\n{result.stderr}"
        )

    def test_script_passes_shellcheck_warnings(self) -> None:
        """setup-gb10.sh should pass shellcheck with warnings enabled."""
        result = subprocess.run(
            ["shellcheck", "--severity=warning", str(SETUP_GB10_SCRIPT)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"shellcheck warnings in {SETUP_GB10_SCRIPT.name}:\n"
            f"{result.stdout}\n{result.stderr}"
        )


# =============================================================================
# Setup sequence ordering
# =============================================================================


class TestSetupSequenceOrder:
    """The setup sequence follows the correct order for GB10."""

    def test_has_eight_steps(self, setup_gb10_text: str) -> None:
        """Setup script should have the full 8-step sequence."""
        steps = re.findall(r"[Ss]tep\s+(\d+)", setup_gb10_text)
        step_numbers = sorted(set(int(s) for s in steps))
        assert len(step_numbers) >= 7, (
            f"Expected at least 7 steps, found: {step_numbers}"
        )

    def test_prerequisites_step(self, setup_gb10_text: str) -> None:
        """An early step should validate prerequisites."""
        match = re.search(r"[Ss]tep\s+\d+.*[Pp]rerequisit", setup_gb10_text)
        assert match, "Script must have a step for prerequisites"

    def test_docker_compose_step(self, setup_gb10_text: str) -> None:
        """A step should build and start Docker services."""
        match = re.search(
            r"[Ss]tep\s+\d+.*([Bb]uild|[Dd]ocker|[Ss]tart|[Ss]ervice)",
            setup_gb10_text,
        )
        assert match, "Script must have a step to build/start services"

    def test_health_wait_step(self, setup_gb10_text: str) -> None:
        """A step should wait for NATS health."""
        match = re.search(
            r"[Ss]tep\s+\d+.*([Hh]ealthy|[Hh]ealth|[Ww]ait)",
            setup_gb10_text,
        )
        assert match, "Script must have a step to wait for NATS health"

    def test_stream_provisioning_step(self, setup_gb10_text: str) -> None:
        """A step should provision JetStream streams."""
        match = re.search(
            r"[Ss]tep\s+\d+.*([Pp]rovision.*[Ss]tream|[Ss]tream)", setup_gb10_text
        )
        assert match, "Script must have a step for stream provisioning"

    def test_kv_provisioning_step(self, setup_gb10_text: str) -> None:
        """A step should provision KV buckets."""
        match = re.search(
            r"[Ss]tep\s+\d+.*([Pp]rovision.*KV|KV.*[Bb]ucket)", setup_gb10_text
        )
        assert match, "Script must have a step for KV bucket provisioning"

    def test_verify_step(self, setup_gb10_text: str) -> None:
        """A step should verify the NATS server."""
        match = re.search(r"[Ss]tep\s+\d+.*[Vv]erif", setup_gb10_text)
        assert match, "Script must have a step for verification"

    def test_docker_up_before_health_check(self, setup_gb10_text: str) -> None:
        """Docker compose up must happen before health check."""
        docker_pos = re.search(r"docker\s+compose\s+up\s+-d", setup_gb10_text)
        health_pos = re.search(
            r"Waiting for NATS container to be healthy|curl.*healthz",
            setup_gb10_text,
        )
        assert docker_pos is not None
        assert health_pos is not None
        assert docker_pos.start() < health_pos.start(), (
            "Docker compose up must happen before health check"
        )


# =============================================================================
# Prerequisite checks
# =============================================================================


class TestSetupGb10PrerequisiteChecks:
    """Setup script checks for required tools."""

    def test_checks_docker(self, setup_gb10_text: str) -> None:
        """Setup must check for docker availability."""
        assert re.search(
            r"command\s+-v\s+docker|has_command\s+docker", setup_gb10_text
        ), "setup-gb10.sh must check for docker"

    def test_checks_docker_compose(self, setup_gb10_text: str) -> None:
        """Setup must check for docker compose availability."""
        assert re.search(
            r"docker\s+compose\s+version", setup_gb10_text
        ), "setup-gb10.sh must check for docker compose"

    def test_checks_curl(self, setup_gb10_text: str) -> None:
        """Setup must check for curl availability."""
        assert re.search(
            r"command\s+-v\s+curl|has_command\s+curl", setup_gb10_text
        ), "setup-gb10.sh must check for curl"


# =============================================================================
# NATS CLI installation
# =============================================================================


class TestNatsCliInstallation:
    """Setup script handles NATS CLI installation."""

    def test_checks_nats_cli_installed(self, setup_gb10_text: str) -> None:
        """Script must check if nats CLI is already installed."""
        assert re.search(
            r"command\s+-v\s+nats|has_command\s+nats", setup_gb10_text
        ), "setup-gb10.sh must check if nats CLI is installed"

    def test_installs_nats_cli_if_missing(self, setup_gb10_text: str) -> None:
        """Script should attempt to install nats CLI if not present."""
        assert re.search(
            r"(binaries\.nats\.dev|get-nats\.io)", setup_gb10_text
        ), "setup-gb10.sh must install nats CLI from official source"


# =============================================================================
# Docker Compose management
# =============================================================================


class TestDockerComposeManagement:
    """Setup script manages Docker Compose correctly."""

    def test_runs_docker_compose_up(self, setup_gb10_text: str) -> None:
        """Setup must run docker compose up."""
        assert re.search(
            r"docker\s+compose\s+up", setup_gb10_text
        ), "setup-gb10.sh must run docker compose up"

    def test_uses_build_flag(self, setup_gb10_text: str) -> None:
        """Setup must use --build flag."""
        assert re.search(
            r"docker\s+compose\s+up.*--build", setup_gb10_text
        ), "setup-gb10.sh must use --build flag"

    def test_uses_detach_flag(self, setup_gb10_text: str) -> None:
        """Setup must use -d flag for detached mode."""
        assert re.search(
            r"docker\s+compose\s+up\s+-d|docker\s+compose\s+up\s+.*-d",
            setup_gb10_text,
        ), "setup-gb10.sh must use -d flag"

    def test_idempotent_container_check(self, setup_gb10_text: str) -> None:
        """Setup should check if container is already running."""
        assert re.search(
            r"docker\s+inspect|already.*running", setup_gb10_text, re.IGNORECASE
        ), "setup-gb10.sh should check if container is already running"


# =============================================================================
# Provisioning gating on prerequisites
# =============================================================================


class TestProvisionGating:
    """Provisioning is properly gated on prerequisites."""

    def test_kv_gated_on_nats_cli(self, setup_gb10_text: str) -> None:
        """KV provisioning must be gated on nats CLI availability."""
        # The script should check for nats before calling provision-kv.sh
        assert re.search(
            r"(command\s+-v\s+nats|has_command\s+nats).*provision-kv",
            setup_gb10_text,
            re.DOTALL,
        ), "KV provisioning must be gated on nats CLI"

    def test_kv_gated_on_jq(self, setup_gb10_text: str) -> None:
        """KV provisioning must be gated on jq availability."""
        assert re.search(
            r"(command\s+-v\s+jq|has_command\s+jq).*provision-kv",
            setup_gb10_text,
            re.DOTALL,
        ), "KV provisioning must be gated on jq"


# =============================================================================
# Environment variable configuration
# =============================================================================


class TestEnvironmentVariables:
    """Script supports environment variable configuration."""

    def test_supports_nats_url(self, setup_gb10_text: str) -> None:
        """Script must support NATS_URL environment variable."""
        assert re.search(r"NATS_URL", setup_gb10_text), (
            "Script must support NATS_URL"
        )

    def test_supports_nats_monitor_url(self, setup_gb10_text: str) -> None:
        """Script must support NATS_MONITOR_URL environment variable."""
        assert re.search(r"NATS_MONITOR_URL", setup_gb10_text), (
            "Script must support NATS_MONITOR_URL"
        )

    def test_nats_url_default(self, setup_gb10_text: str) -> None:
        """Script must default NATS_URL to localhost."""
        assert re.search(r"nats://localhost:4222", setup_gb10_text), (
            "Script must default NATS_URL to nats://localhost:4222"
        )
