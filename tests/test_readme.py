"""Tests for README.md — validates deployment documentation for TASK-DCD-005.

Verifies all acceptance criteria:
- AC-001: Quick Start section reflects actual `docker compose` commands
- AC-002: Volume management section documents backup/restore/reset
- AC-003: Health check verification commands included
- AC-004: Clear WARNING about `docker compose down -v` data loss
- AC-005: Dockerfile and build context documented
"""
from __future__ import annotations

from pathlib import Path

import pytest

# Path to the README file relative to the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
README_FILE = PROJECT_ROOT / "README.md"


@pytest.fixture
def readme_text() -> str:
    """Read the README.md file content."""
    assert README_FILE.exists(), f"README.md not found at {README_FILE}"
    return README_FILE.read_text(encoding="utf-8")


@pytest.fixture
def readme_lower(readme_text: str) -> str:
    """Lowercase README content for case-insensitive matching."""
    return readme_text.lower()


# --- AC-001: Quick Start section reflects actual `docker compose` commands ---


class TestQuickStartSection:
    """AC-001: Quick Start section reflects actual docker compose commands."""

    def test_readme_exists(self) -> None:
        assert README_FILE.exists(), f"Expected README.md at {README_FILE}"

    def test_readme_is_not_empty(self, readme_text: str) -> None:
        assert len(readme_text.strip()) > 0, "README.md must not be empty"

    def test_has_quick_start_section(self, readme_text: str) -> None:
        assert "## Quick Start" in readme_text, (
            "README.md must have a '## Quick Start' section"
        )

    def test_quick_start_has_docker_compose_up(self, readme_text: str) -> None:
        assert "docker compose up -d" in readme_text, (
            "Quick Start must include 'docker compose up -d' command"
        )

    def test_quick_start_has_build_flag(self, readme_text: str) -> None:
        assert "docker compose up -d --build" in readme_text, (
            "Quick Start must include '--build' flag for initial build"
        )

    def test_quick_start_has_env_copy(self, readme_text: str) -> None:
        assert "cp .env.example .env" in readme_text, (
            "Quick Start must include 'cp .env.example .env' command"
        )

    def test_quick_start_has_verify_script(self, readme_text: str) -> None:
        assert "verify-nats.sh" in readme_text, (
            "Quick Start must reference the verify-nats.sh script"
        )

    def test_no_obsolete_setup_gb10_reference(self, readme_text: str) -> None:
        """Ensure obsolete scripts that don't exist are not referenced as commands."""
        # The old README referenced setup-gb10.sh which doesn't exist
        assert "setup-gb10.sh" not in readme_text, (
            "README should not reference non-existent setup-gb10.sh script"
        )

    def test_provision_streams_reference_in_streams_section(self, readme_text: str) -> None:
        """provision-streams.sh exists and is documented in the JetStream Streams section."""
        assert "provision-streams.sh" in readme_text, (
            "README should reference the provision-streams.sh script in the JetStream Streams section"
        )


# --- AC-002: Volume management section documents backup/restore/reset ---


class TestVolumeManagementSection:
    """AC-002: Volume management section documents backup/restore/reset."""

    def test_has_volume_management_section(self, readme_text: str) -> None:
        assert "## Volume Management" in readme_text, (
            "README.md must have a '## Volume Management' section"
        )

    def test_documents_nats_data_volume(self, readme_text: str) -> None:
        assert "nats-data" in readme_text, (
            "Volume management section must mention the 'nats-data' volume"
        )

    def test_documents_backup(self, readme_lower: str) -> None:
        assert "backup" in readme_lower, (
            "Volume management section must document backup procedure"
        )

    def test_documents_restore(self, readme_lower: str) -> None:
        assert "restore" in readme_lower, (
            "Volume management section must document restore procedure"
        )

    def test_documents_reset(self, readme_lower: str) -> None:
        # Reset is documented via "docker compose down -v" or explicit reset section
        assert "reset" in readme_lower or "down -v" in readme_lower, (
            "Volume management section must document reset/clean procedure"
        )

    def test_backup_includes_tar_command(self, readme_text: str) -> None:
        assert "tar" in readme_text, (
            "Backup section must include a tar-based backup command"
        )

    def test_restore_includes_tar_command(self, readme_text: str) -> None:
        # The restore section should also reference tar for extraction
        assert "tar xzf" in readme_text or "tar -xzf" in readme_text, (
            "Restore section must include a tar extraction command"
        )

    def test_documents_stopping_without_data_loss(self, readme_text: str) -> None:
        assert "docker compose down" in readme_text, (
            "Volume section must document 'docker compose down' for safe stop"
        )


# --- AC-003: Health check verification commands included ---


class TestHealthCheckVerification:
    """AC-003: Health check verification commands included."""

    def test_has_health_check_section(self, readme_text: str) -> None:
        assert "Health Check" in readme_text, (
            "README.md must have a health check section"
        )

    def test_documents_healthz_endpoint(self, readme_text: str) -> None:
        assert "healthz" in readme_text, (
            "README must document the /healthz health endpoint"
        )

    def test_documents_curl_healthz(self, readme_text: str) -> None:
        assert "curl" in readme_text and "healthz" in readme_text, (
            "README must include curl command for health check"
        )

    def test_documents_jsz_endpoint(self, readme_text: str) -> None:
        assert "/jsz" in readme_text, (
            "README must document the /jsz JetStream status endpoint"
        )

    def test_documents_varz_endpoint(self, readme_text: str) -> None:
        assert "/varz" in readme_text, (
            "README must document the /varz server info endpoint"
        )

    def test_documents_docker_compose_ps(self, readme_text: str) -> None:
        assert "docker compose ps" in readme_text, (
            "README must include 'docker compose ps' for checking container status"
        )

    def test_documents_health_check_config(self, readme_text: str) -> None:
        """Health check YAML config should be shown in README."""
        assert "interval:" in readme_text and "timeout:" in readme_text, (
            "README must show the health check configuration (interval, timeout)"
        )

    def test_documents_verify_nats_script(self, readme_text: str) -> None:
        assert "verify-nats.sh" in readme_text, (
            "README must reference the verify-nats.sh verification script"
        )


# --- AC-004: Clear WARNING about `docker compose down -v` data loss ---


class TestDataLossWarning:
    """AC-004: Clear WARNING about docker compose down -v data loss."""

    def test_has_warning_keyword(self, readme_text: str) -> None:
        assert "WARNING" in readme_text, (
            "README must contain a clear 'WARNING' about data loss"
        )

    def test_warns_about_down_v(self, readme_text: str) -> None:
        assert "docker compose down -v" in readme_text, (
            "README must explicitly mention 'docker compose down -v' in the warning"
        )

    def test_warns_about_data_destruction(self, readme_lower: str) -> None:
        assert "destroy" in readme_lower or "data loss" in readme_lower, (
            "WARNING must mention data destruction or data loss"
        )

    def test_warns_about_irreversibility(self, readme_lower: str) -> None:
        assert "irreversible" in readme_lower or "permanently" in readme_lower, (
            "WARNING must indicate the operation is irreversible or permanent"
        )

    def test_warns_about_jetstream_data(self, readme_lower: str) -> None:
        assert "jetstream" in readme_lower and (
            "destroy" in readme_lower or "data" in readme_lower
        ), (
            "WARNING must mention JetStream data being affected"
        )


# --- AC-005: Dockerfile and build context documented ---


class TestDockerfileBuildContext:
    """AC-005: Dockerfile and build context documented."""

    def test_has_dockerfile_section(self, readme_text: str) -> None:
        assert "Dockerfile" in readme_text, (
            "README must document the Dockerfile"
        )

    def test_documents_build_context(self, readme_lower: str) -> None:
        assert "build context" in readme_lower or "build: ." in readme_lower, (
            "README must document the Docker build context"
        )

    def test_documents_base_image(self, readme_text: str) -> None:
        assert "nats:2.11-alpine" in readme_text, (
            "README must document the base image (nats:2.11-alpine)"
        )

    def test_documents_envsubst(self, readme_text: str) -> None:
        assert "envsubst" in readme_text, (
            "README must explain the envsubst password injection mechanism"
        )

    def test_documents_entrypoint(self, readme_text: str) -> None:
        assert "docker-entrypoint.sh" in readme_text, (
            "README must reference the docker-entrypoint.sh script"
        )

    def test_documents_gettext_package(self, readme_text: str) -> None:
        assert "gettext" in readme_text, (
            "README must mention the gettext package that provides envsubst"
        )

    def test_documents_dockerignore(self, readme_text: str) -> None:
        assert ".dockerignore" in readme_text, (
            "README must mention the .dockerignore file"
        )

    def test_documents_password_injection_flow(self, readme_text: str) -> None:
        """README should explain the password injection workflow."""
        assert "accounts.conf.template" in readme_text or "conf.template" in readme_text, (
            "README must explain how .conf.template files are processed"
        )
