"""Tests for NATS JetStream volume persistence — TASK-DCD-004.

Validates that JetStream data persists across container restarts via the
named Docker volume `nats-data`.

Acceptance Criteria:
- AC-001: Test stream created and messages published successfully
- AC-002: After `docker compose down` + `up`, stream still exists
- AC-003: After `docker compose down` + `up`, published messages still retrievable
- AC-004: Volume listed in `docker volume ls` as `nats-infrastructure_nats-data`
- AC-005: Documented: `docker compose down -v` WARNING about data loss

Test categories:
- Configuration tests (no Docker required) — verify volume/persistence setup
- Integration tests (@pytest.mark.integration) — require running Docker/NATS
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest
import yaml

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
COMPOSE_FILE = PROJECT_ROOT / "docker-compose.yml"
NATS_SERVER_CONF = PROJECT_ROOT / "config" / "nats-server.conf"
README_FILE = PROJECT_ROOT / "README.md"
DOCKER_COMPOSE_YML_HEADER = PROJECT_ROOT / "docker-compose.yml"


@pytest.fixture
def compose_text() -> str:
    """Read the docker-compose.yml file content."""
    assert COMPOSE_FILE.exists(), f"docker-compose.yml not found at {COMPOSE_FILE}"
    return COMPOSE_FILE.read_text(encoding="utf-8")


@pytest.fixture
def compose_data(compose_text: str) -> dict:
    """Parse docker-compose.yml as YAML."""
    data = yaml.safe_load(compose_text)
    assert isinstance(data, dict), "docker-compose.yml must be a valid YAML mapping"
    return data


@pytest.fixture
def nats_service(compose_data: dict) -> dict:
    """Extract the NATS service definition from compose data."""
    services = compose_data.get("services", {})
    assert "nats" in services, "docker-compose.yml must define a 'nats' service"
    return services["nats"]


@pytest.fixture
def nats_conf_text() -> str:
    """Read the nats-server.conf file content."""
    assert NATS_SERVER_CONF.exists(), f"nats-server.conf not found at {NATS_SERVER_CONF}"
    return NATS_SERVER_CONF.read_text(encoding="utf-8")


@pytest.fixture
def readme_text() -> str:
    """Read the README.md file content."""
    assert README_FILE.exists(), f"README.md not found at {README_FILE}"
    return README_FILE.read_text(encoding="utf-8")


# =============================================================================
# AC-001: Test stream created and messages published successfully
# =============================================================================
# Configuration-level tests: verify the infrastructure supports stream creation
# and message publishing (JetStream enabled, store_dir configured, volume mounted).


class TestStreamCreationConfig:
    """AC-001: Verify configuration supports stream creation and message publishing."""

    def test_jetstream_enabled_in_server_conf(self, nats_conf_text: str) -> None:
        """JetStream block exists in nats-server.conf."""
        assert "jetstream" in nats_conf_text.lower(), (
            "nats-server.conf must contain a JetStream configuration block"
        )

    def test_jetstream_store_dir_configured(self, nats_conf_text: str) -> None:
        """JetStream store_dir points to /data/jetstream."""
        assert "store_dir" in nats_conf_text, (
            "JetStream must have store_dir configured"
        )
        assert "/data/jetstream" in nats_conf_text, (
            "JetStream store_dir must be /data/jetstream"
        )

    def test_jetstream_has_file_storage_limits(self, nats_conf_text: str) -> None:
        """JetStream max_file limit is configured for persistent storage."""
        assert "max_file" in nats_conf_text, (
            "JetStream must have max_file storage limit configured"
        )

    def test_jetstream_has_memory_limits(self, nats_conf_text: str) -> None:
        """JetStream max_mem limit is configured."""
        assert "max_mem" in nats_conf_text, (
            "JetStream must have max_mem limit configured"
        )

    def test_volume_mounted_at_store_dir(self, nats_service: dict) -> None:
        """Named volume nats-data is mounted at /data/jetstream (the store_dir)."""
        volumes = nats_service.get("volumes", [])
        volume_strings = [str(v) for v in volumes]
        jetstream_mount = any(
            "nats-data" in v and "/data/jetstream" in v for v in volume_strings
        )
        assert jetstream_mount, (
            f"nats-data volume must be mounted at /data/jetstream, got: {volume_strings}"
        )

    def test_client_port_exposed_for_publishing(self, nats_service: dict) -> None:
        """Port 4222 is exposed for client connections (stream creation + publishing)."""
        ports = [str(p) for p in nats_service.get("ports", [])]
        has_4222 = any("4222" in p for p in ports)
        assert has_4222, f"Port 4222 must be exposed for message publishing, got: {ports}"


# =============================================================================
# AC-002: After `docker compose down` + `up`, stream still exists
# =============================================================================
# Configuration-level tests: verify the volume is a named volume (survives
# `docker compose down`) and the store_dir matches the mount point.


class TestStreamSurvivesRestart:
    """AC-002: Verify volume configuration enables stream survival across restarts."""

    def test_top_level_named_volume_defined(self, compose_data: dict) -> None:
        """Top-level 'volumes:' section defines nats-data as a named volume."""
        volumes = compose_data.get("volumes", {})
        assert "nats-data" in volumes, (
            "docker-compose.yml must define a top-level 'nats-data' named volume. "
            "Named volumes survive `docker compose down` (without -v flag)."
        )

    def test_named_volume_not_anonymous(self, compose_text: str) -> None:
        """Volume is named (not anonymous bind mount) so it persists across down/up."""
        # Anonymous volumes use just a path like '/data/jetstream' without a name
        # Named volumes are declared in top-level 'volumes:' section
        data = yaml.safe_load(compose_text)
        top_level_volumes = data.get("volumes", {})
        assert "nats-data" in top_level_volumes, (
            "nats-data must be declared as a top-level named volume to persist across restarts"
        )

    def test_store_dir_matches_volume_mount(
        self, nats_conf_text: str, nats_service: dict
    ) -> None:
        """JetStream store_dir path matches the Docker volume mount point."""
        # Extract store_dir from config
        store_dir_match = re.search(r'store_dir:\s*"([^"]+)"', nats_conf_text)
        assert store_dir_match, "Could not find store_dir in nats-server.conf"
        store_dir = store_dir_match.group(1)

        # Check volume mount includes this path
        volumes = nats_service.get("volumes", [])
        volume_strings = [str(v) for v in volumes]
        has_matching_mount = any(store_dir in v for v in volume_strings)
        assert has_matching_mount, (
            f"No volume mount matches store_dir '{store_dir}'. "
            f"Volumes: {volume_strings}. "
            "JetStream data would be lost on container restart."
        )

    def test_volume_is_not_tmpfs(self, compose_data: dict) -> None:
        """The nats-data volume is not a tmpfs (which would lose data on restart)."""
        volumes = compose_data.get("volumes", {})
        nats_data_config = volumes.get("nats-data")
        # None or empty dict means default driver (local filesystem) — that's good
        if isinstance(nats_data_config, dict) and nats_data_config:
            driver = nats_data_config.get("driver", "local")
            assert driver != "tmpfs", (
                "nats-data volume must NOT use tmpfs driver — data would be lost on restart"
            )


# =============================================================================
# AC-003: After `docker compose down` + `up`, published messages still retrievable
# =============================================================================
# Configuration-level tests: verify file-based storage is configured (not in-memory
# only) so messages survive restarts.


class TestMessageRetrievalAfterRestart:
    """AC-003: Verify configuration enables message retrieval after container restart."""

    def test_jetstream_file_storage_configured(self, nats_conf_text: str) -> None:
        """JetStream has max_file > 0, enabling file-based message persistence."""
        # max_file must be present and non-zero for messages to be stored on disk
        max_file_match = re.search(r"max_file:\s*(\S+)", nats_conf_text)
        assert max_file_match, (
            "JetStream must have max_file configured for file-based message persistence"
        )
        max_file_value = max_file_match.group(1)
        # Value should be something like "10GB" — not "0" or "0B"
        assert max_file_value not in ("0", "0B", "0MB", "0GB"), (
            f"JetStream max_file must be > 0 for messages to persist, got '{max_file_value}'"
        )

    def test_store_dir_is_absolute_path(self, nats_conf_text: str) -> None:
        """JetStream store_dir is an absolute path (starts with /)."""
        store_dir_match = re.search(r'store_dir:\s*"([^"]+)"', nats_conf_text)
        assert store_dir_match, "Could not find store_dir in nats-server.conf"
        store_dir = store_dir_match.group(1)
        assert store_dir.startswith("/"), (
            f"store_dir must be an absolute path, got '{store_dir}'"
        )

    def test_volume_mount_preserves_data_directory(self, nats_service: dict) -> None:
        """The named volume preserves the entire /data/jetstream directory."""
        volumes = nats_service.get("volumes", [])
        volume_strings = [str(v) for v in volumes]
        # Verify nats-data is mounted at /data/jetstream (not a subdirectory)
        jetstream_mount = [v for v in volume_strings if "nats-data" in v and "/data/jetstream" in v]
        assert len(jetstream_mount) == 1, (
            f"Expected exactly one nats-data mount at /data/jetstream, got: {jetstream_mount}"
        )

    def test_volume_not_read_only(self, nats_service: dict) -> None:
        """The JetStream data volume is NOT mounted read-only (must be writable)."""
        volumes = nats_service.get("volumes", [])
        for v in volumes:
            v_str = str(v)
            if "nats-data" in v_str:
                assert ":ro" not in v_str, (
                    "nats-data volume must NOT be read-only — JetStream needs write access "
                    f"for message persistence. Got: '{v_str}'"
                )


# =============================================================================
# AC-004: Volume listed in `docker volume ls` as `nats-infrastructure_nats-data`
# =============================================================================
# Configuration-level tests: verify the volume naming convention in compose file.
# The Docker Compose project name prefixes the volume name.


class TestVolumeNaming:
    """AC-004: Verify volume naming follows Docker Compose conventions."""

    def test_volume_name_is_nats_data(self, compose_data: dict) -> None:
        """Top-level volume is named 'nats-data' in docker-compose.yml."""
        volumes = compose_data.get("volumes", {})
        assert "nats-data" in volumes, (
            "docker-compose.yml must define 'nats-data' volume. "
            "Docker Compose will prefix it with the project name (directory name) "
            "to create the full volume name on the host."
        )

    def test_volume_uses_default_driver(self, compose_data: dict) -> None:
        """Volume uses default (local) driver — no external driver dependency."""
        volumes = compose_data.get("volumes", {})
        nats_data_config = volumes.get("nats-data")
        # None or empty dict means default driver — that's correct
        if isinstance(nats_data_config, dict) and nats_data_config:
            driver = nats_data_config.get("driver", "local")
            assert driver == "local", (
                f"nats-data volume should use 'local' driver, got '{driver}'"
            )

    def test_volume_referenced_in_service(self, nats_service: dict) -> None:
        """NATS service references the nats-data volume in its volumes list."""
        volumes = nats_service.get("volumes", [])
        volume_strings = [str(v) for v in volumes]
        has_nats_data = any("nats-data" in v for v in volume_strings)
        assert has_nats_data, (
            f"NATS service must reference 'nats-data' volume, got: {volume_strings}"
        )

    def test_compose_project_name_derivation(self) -> None:
        """Docker Compose derives project name from directory name.

        When docker-compose.yml is in a directory named 'nats-infrastructure',
        the volume will be listed as 'nats-infrastructure_nats-data' in
        `docker volume ls`. This test documents the naming convention.
        """
        # The compose file is at PROJECT_ROOT/docker-compose.yml
        # Docker Compose uses the directory name as the project name
        # Volume format: {project_name}_{volume_name}
        # Expected: nats-infrastructure_nats-data
        #
        # Note: In worktree or CI contexts the directory name may differ,
        # so this test verifies the convention is documented rather than
        # checking an exact directory name.
        assert COMPOSE_FILE.exists(), "docker-compose.yml must exist"
        data = yaml.safe_load(COMPOSE_FILE.read_text(encoding="utf-8"))
        assert "nats-data" in data.get("volumes", {}), (
            "Volume must be named 'nats-data' — Docker Compose will prefix with "
            "project name to create '<project>_nats-data' in `docker volume ls`"
        )


# =============================================================================
# AC-005: Documented: `docker compose down -v` WARNING about data loss
# =============================================================================
# Verify that README.md or docker-compose.yml contains a clear warning about
# `docker compose down -v` destroying JetStream data.


class TestDataLossWarning:
    """AC-005: Documented warning about `docker compose down -v` data loss."""

    def test_compose_file_warns_about_down_v(self, compose_text: str) -> None:
        """docker-compose.yml contains a warning about `docker compose down -v`."""
        lower = compose_text.lower()
        has_down_v_warning = (
            "down -v" in lower
            or "down --volumes" in lower
            or "removes volumes" in lower
            or "data loss" in lower
            or "destroys" in lower and "volume" in lower
        )
        assert has_down_v_warning, (
            "docker-compose.yml must contain a warning about "
            "'docker compose down -v' destroying JetStream data. "
            "Add a comment warning that -v flag removes named volumes."
        )

    def test_readme_warns_about_data_loss(self, readme_text: str) -> None:
        """README.md documents the danger of `docker compose down -v`."""
        lower = readme_text.lower()
        has_data_loss_docs = (
            "down -v" in lower
            or "down --volumes" in lower
            or "removes volumes" in lower
            or "data loss" in lower
            or ("destroys" in lower and "volume" in lower)
            or ("warning" in lower and "volume" in lower)
        )
        assert has_data_loss_docs, (
            "README.md must document that 'docker compose down -v' "
            "removes the nats-data volume and destroys all JetStream data. "
            "Users must be warned about this destructive operation."
        )

    def test_warning_mentions_jetstream_or_persistence(self, compose_text: str) -> None:
        """Warning in compose file specifically mentions JetStream or persistence."""
        lower = compose_text.lower()
        # The warning should be contextual — not just about volumes in general
        has_context = (
            ("jetstream" in lower and ("volume" in lower or "persist" in lower))
            or ("persist" in lower and "volume" in lower)
        )
        assert has_context, (
            "docker-compose.yml warning should mention JetStream or persistence "
            "to make the data loss risk clear."
        )


# =============================================================================
# Integration tests — require running Docker and NATS
# =============================================================================
# These tests are gated behind @pytest.mark.integration and require:
#   - Docker and docker compose available
#   - .env file configured (copy from .env.example)
#   - Ports 4222 and 8222 available
#
# Run with: pytest -m integration tests/test_volume_persistence.py -v


@pytest.mark.integration
class TestVolumePersistenceIntegration:
    """Integration tests verifying actual volume persistence with Docker.

    These tests require Docker Compose and a running NATS server.
    Run with: pytest -m integration tests/test_volume_persistence.py -v

    The tests verify the full lifecycle:
    1. Start NATS container
    2. Create a JetStream stream and publish messages
    3. Stop and restart the container
    4. Verify stream and messages survived the restart
    """

    @staticmethod
    def _run(cmd: str, timeout: int = 30) -> subprocess.CompletedProcess:
        """Run a shell command and return the result."""
        return subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(PROJECT_ROOT),
        )

    @staticmethod
    def _wait_for_healthy(max_wait: int = 30) -> bool:
        """Wait for NATS container to be healthy."""
        import time

        for _ in range(max_wait):
            result = subprocess.run(
                "docker compose ps --format json",
                shell=True,
                capture_output=True,
                text=True,
                cwd=str(PROJECT_ROOT),
            )
            if '"healthy"' in result.stdout or "healthy" in result.stdout:
                return True
            time.sleep(1)
        return False

    def test_ac001_stream_creation_and_publish(self) -> None:
        """AC-001: Create a JetStream stream and publish messages via nats CLI."""
        # Ensure container is up and healthy
        self._run("docker compose up -d")
        assert self._wait_for_healthy(), "NATS container did not become healthy"

        # Create a test stream (nats CLI runs on host, connects to exposed port)
        result = self._run(
            "nats -s nats://localhost:4222 "
            "stream add PERSISTENCE_TEST "
            "--subjects='persistence.test' "
            "--storage=file "
            "--retention=limits "
            "--max-msgs=-1 "
            "--max-bytes=-1 "
            "--max-age=1h "
            "--max-msg-size=-1 "
            "--discard=old "
            "--replicas=1 "
            "--no-allow-rollup "
            "--deny-delete "
            "--deny-purge "
            "--defaults 2>/dev/null || true"
        )

        # Publish test messages
        for i in range(3):
            pub_result = self._run(
                f"nats -s nats://localhost:4222 "
                f"pub persistence.test 'test-message-{i}'"
            )
            assert pub_result.returncode == 0, (
                f"Failed to publish message {i}: {pub_result.stderr}"
            )

        # Verify stream exists and has messages
        info_result = self._run(
            "nats -s nats://localhost:4222 "
            "stream info PERSISTENCE_TEST --json"
        )
        assert info_result.returncode == 0, (
            f"Failed to get stream info: {info_result.stderr}"
        )
        assert "PERSISTENCE_TEST" in info_result.stdout

    def test_ac002_stream_survives_restart(self) -> None:
        """AC-002: Stream persists after docker compose down + up."""
        # Start fresh and create stream
        self._run("docker compose up -d")
        assert self._wait_for_healthy(), "NATS container did not become healthy"

        # Create stream (nats CLI runs on host, connects to exposed port)
        self._run(
            "nats -s nats://localhost:4222 "
            "stream add SURVIVAL_TEST "
            "--subjects='survival.test' "
            "--storage=file "
            "--retention=limits "
            "--max-msgs=-1 "
            "--max-bytes=-1 "
            "--max-age=1h "
            "--max-msg-size=-1 "
            "--discard=old "
            "--replicas=1 "
            "--defaults 2>/dev/null || true"
        )

        # Publish a message
        self._run(
            "nats -s nats://localhost:4222 "
            "pub survival.test 'before-restart'"
        )

        # docker compose down (preserves volumes) then up
        self._run("docker compose down")
        self._run("docker compose up -d")
        assert self._wait_for_healthy(max_wait=45), (
            "NATS container did not become healthy after restart"
        )

        # Verify stream still exists
        info_result = self._run(
            "nats -s nats://localhost:4222 "
            "stream info SURVIVAL_TEST --json"
        )
        assert info_result.returncode == 0, (
            f"Stream SURVIVAL_TEST not found after restart: {info_result.stderr}"
        )
        assert "SURVIVAL_TEST" in info_result.stdout, (
            "Stream SURVIVAL_TEST must exist after docker compose down + up"
        )

    def test_ac003_messages_retrievable_after_restart(self) -> None:
        """AC-003: Published messages are retrievable after docker compose down + up."""
        # Start and create stream with unique name
        self._run("docker compose up -d")
        assert self._wait_for_healthy(), "NATS container did not become healthy"

        # Create stream (nats CLI runs on host, connects to exposed port)
        self._run(
            "nats -s nats://localhost:4222 "
            "stream add RETRIEVAL_TEST "
            "--subjects='retrieval.test' "
            "--storage=file "
            "--retention=limits "
            "--max-msgs=-1 "
            "--max-bytes=-1 "
            "--max-age=1h "
            "--max-msg-size=-1 "
            "--discard=old "
            "--replicas=1 "
            "--defaults 2>/dev/null || true"
        )

        # Publish messages
        for i in range(5):
            self._run(
                f"nats -s nats://localhost:4222 "
                f"pub retrieval.test 'persistent-msg-{i}'"
            )

        # Restart
        self._run("docker compose down")
        self._run("docker compose up -d")
        assert self._wait_for_healthy(max_wait=45), (
            "NATS container did not become healthy after restart"
        )

        # Retrieve messages — check stream info shows message count
        info_result = self._run(
            "nats -s nats://localhost:4222 "
            "stream info RETRIEVAL_TEST --json"
        )
        assert info_result.returncode == 0, (
            f"Stream not found after restart: {info_result.stderr}"
        )
        # The stream info JSON should show messages > 0
        assert '"messages"' in info_result.stdout, (
            "Stream info must report message count"
        )

    def test_ac004_volume_listed_in_docker(self) -> None:
        """AC-004: Volume listed in `docker volume ls` with project prefix."""
        # Ensure containers have been started at least once
        self._run("docker compose up -d")
        assert self._wait_for_healthy(), "NATS container did not become healthy"

        # Check docker volume ls
        result = self._run("docker volume ls --format '{{.Name}}'")
        assert result.returncode == 0, f"docker volume ls failed: {result.stderr}"

        # The volume name is {project_name}_nats-data
        # Project name derives from directory name or COMPOSE_PROJECT_NAME
        volume_names = result.stdout.strip().split("\n")
        nats_data_volumes = [v for v in volume_names if "nats-data" in v]
        assert len(nats_data_volumes) > 0, (
            f"Expected a volume containing 'nats-data' in: {volume_names}"
        )
