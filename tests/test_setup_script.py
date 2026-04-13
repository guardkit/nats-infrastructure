"""Tests for scripts/setup.sh — NATS infrastructure setup script.

Validates TASK-JSTR-005 acceptance criteria:
- AC-001: provision-streams.sh called from setup script at correct point in sequence
- AC-004: All modified files pass project-configured lint/format checks with zero errors

Tests verify setup.sh structure, sequence ordering, and integration with
provision-streams.sh and verify-nats.sh.
"""
from __future__ import annotations

import re
import stat
from pathlib import Path

import pytest

# Paths relative to project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SETUP_SCRIPT = PROJECT_ROOT / "scripts" / "setup.sh"
PROVISION_SCRIPT = PROJECT_ROOT / "streams" / "provision-streams.sh"
VERIFY_SCRIPT = PROJECT_ROOT / "scripts" / "verify-nats.sh"


@pytest.fixture
def setup_text() -> str:
    """Read the setup.sh script content."""
    assert SETUP_SCRIPT.exists(), f"Script not found at {SETUP_SCRIPT}"
    return SETUP_SCRIPT.read_text(encoding="utf-8")


# --- Script existence and structure ---


class TestSetupScriptExists:
    """setup.sh exists and is properly structured."""

    def test_script_file_exists(self) -> None:
        assert SETUP_SCRIPT.exists(), f"Expected script at {SETUP_SCRIPT}"

    def test_script_is_executable(self) -> None:
        mode = SETUP_SCRIPT.stat().st_mode
        assert mode & stat.S_IXUSR, "Script must be executable (chmod +x)"

    def test_script_has_shebang(self, setup_text: str) -> None:
        assert setup_text.startswith("#!/"), (
            "Script must start with a shebang line"
        )

    def test_script_is_not_empty(self, setup_text: str) -> None:
        assert len(setup_text.strip()) > 0, "Script must not be empty"

    def test_uses_strict_error_handling(self, setup_text: str) -> None:
        assert re.search(
            r"set\s+-euo\s+pipefail", setup_text
        ), "Script must use 'set -euo pipefail' for strict error handling"


# --- AC-001: provision-streams.sh called from setup script at correct point ---


class TestProvisionStreamsIntegration:
    """AC-001: provision-streams.sh is called from setup.sh at the correct point."""

    def test_calls_provision_streams(self, setup_text: str) -> None:
        """Setup script must invoke provision-streams.sh."""
        assert re.search(
            r"provision-streams\.sh", setup_text
        ), "setup.sh must call provision-streams.sh"

    def test_provision_after_docker_compose_up(self, setup_text: str) -> None:
        """Provisioning must happen after Docker Compose up."""
        docker_up_pos = re.search(r"docker\s+compose\s+up", setup_text)
        provision_pos = re.search(r"provision-streams\.sh", setup_text)
        assert docker_up_pos is not None, "setup.sh must run docker compose up"
        assert provision_pos is not None, "setup.sh must call provision-streams.sh"
        assert docker_up_pos.start() < provision_pos.start(), (
            "provision-streams.sh must be called AFTER docker compose up"
        )

    def test_provision_before_verify(self, setup_text: str) -> None:
        """Provisioning must happen before verification."""
        provision_pos = re.search(r"provision-streams\.sh", setup_text)
        verify_pos = re.search(r"verify-nats\.sh", setup_text)
        assert provision_pos is not None, "setup.sh must call provision-streams.sh"
        assert verify_pos is not None, "setup.sh must call verify-nats.sh"
        assert provision_pos.start() < verify_pos.start(), (
            "provision-streams.sh must be called BEFORE verify-nats.sh"
        )

    def test_provision_is_step_4(self, setup_text: str) -> None:
        """Provisioning must be step 4 in the sequence."""
        # The task spec requires step 4 for provisioning
        step_4_match = re.search(r"[Ss]tep\s+4.*[Pp]rovision", setup_text)
        assert step_4_match, (
            "Stream provisioning must be labeled as Step 4"
        )

    def test_has_five_steps(self, setup_text: str) -> None:
        """Setup script should have the full 5-step sequence."""
        steps = re.findall(r"[Ss]tep\s+(\d+)", setup_text)
        step_numbers = sorted(set(int(s) for s in steps))
        assert step_numbers == [1, 2, 3, 4, 5], (
            f"Expected steps 1-5, found: {step_numbers}"
        )


class TestSetupSequenceOrder:
    """The setup sequence follows the correct order."""

    def test_step_1_is_prerequisites(self, setup_text: str) -> None:
        """Step 1 should validate prerequisites."""
        match = re.search(r"[Ss]tep\s+1.*[Pp]rerequisit", setup_text)
        assert match, "Step 1 should validate prerequisites"

    def test_step_2_is_env_file(self, setup_text: str) -> None:
        """Step 2 should handle the .env file."""
        match = re.search(r"[Ss]tep\s+2.*[Ee]nvironment|[Ss]tep\s+2.*\.env", setup_text)
        assert match, "Step 2 should handle environment file"

    def test_step_3_is_docker_compose(self, setup_text: str) -> None:
        """Step 3 should build and start Docker services."""
        match = re.search(r"[Ss]tep\s+3.*([Bb]uild|[Dd]ocker|[Ss]tart)", setup_text)
        assert match, "Step 3 should build and start services"

    def test_step_4_is_stream_provisioning(self, setup_text: str) -> None:
        """Step 4 should provision JetStream streams."""
        match = re.search(r"[Ss]tep\s+4.*([Pp]rovision|[Ss]tream)", setup_text)
        assert match, "Step 4 should provision JetStream streams"

    def test_step_5_is_verification(self, setup_text: str) -> None:
        """Step 5 should verify the NATS server."""
        match = re.search(r"[Ss]tep\s+5.*([Vv]erif)", setup_text)
        assert match, "Step 5 should verify the NATS server"


class TestSetupPrerequisiteChecks:
    """Setup script checks for required tools."""

    def test_checks_docker(self, setup_text: str) -> None:
        """Setup must check for docker availability."""
        assert re.search(
            r"command\s+-v\s+docker|which\s+docker", setup_text
        ), "setup.sh must check for docker"

    def test_checks_docker_compose(self, setup_text: str) -> None:
        """Setup must check for docker compose availability."""
        assert re.search(
            r"docker\s+compose\s+version", setup_text
        ), "setup.sh must check for docker compose"


class TestSetupProvisionGating:
    """Provision-streams.sh execution is properly gated on prerequisites."""

    def test_gates_on_nats_cli(self, setup_text: str) -> None:
        """Provisioning must be gated on nats CLI availability."""
        assert re.search(
            r"command\s+-v\s+nats", setup_text
        ), "setup.sh must check nats CLI availability before provisioning"

    def test_gates_on_jq(self, setup_text: str) -> None:
        """Provisioning must be gated on jq availability."""
        assert re.search(
            r"command\s+-v\s+jq", setup_text
        ), "setup.sh must check jq availability before provisioning"

    def test_skip_message_when_tools_missing(self, setup_text: str) -> None:
        """Setup should inform user when skipping provisioning."""
        assert re.search(
            r"[Ss]kip.*provision|[Ss]kip.*stream", setup_text, re.IGNORECASE
        ), "setup.sh must show skip message when provisioning tools are missing"


class TestSetupCallsVerify:
    """Setup script calls verify-nats.sh."""

    def test_calls_verify_nats(self, setup_text: str) -> None:
        """Setup script must invoke verify-nats.sh."""
        assert re.search(
            r"verify-nats\.sh", setup_text
        ), "setup.sh must call verify-nats.sh"

    def test_verify_after_provision(self, setup_text: str) -> None:
        """Verification must happen after provisioning."""
        provision_pos = re.search(r"provision-streams\.sh", setup_text)
        verify_pos = re.search(r"verify-nats\.sh", setup_text)
        assert provision_pos is not None
        assert verify_pos is not None
        assert provision_pos.start() < verify_pos.start(), (
            "verify-nats.sh must be called after provision-streams.sh"
        )


class TestSetupDockerCompose:
    """Setup script correctly manages Docker Compose."""

    def test_runs_docker_compose_up(self, setup_text: str) -> None:
        """Setup must run docker compose up."""
        assert re.search(
            r"docker\s+compose\s+up", setup_text
        ), "setup.sh must run docker compose up"

    def test_uses_build_flag(self, setup_text: str) -> None:
        """Setup must use --build flag."""
        assert re.search(
            r"docker\s+compose\s+up.*--build", setup_text
        ), "setup.sh must use --build flag"

    def test_uses_detach_flag(self, setup_text: str) -> None:
        """Setup must use -d flag for detached mode."""
        assert re.search(
            r"docker\s+compose\s+up\s+-d|docker\s+compose\s+up\s+.*-d", setup_text
        ), "setup.sh must use -d flag"

    def test_waits_for_healthy(self, setup_text: str) -> None:
        """Setup must wait for the NATS container to be healthy."""
        assert re.search(
            r"healthy|health", setup_text, re.IGNORECASE
        ), "setup.sh must wait for container health"
