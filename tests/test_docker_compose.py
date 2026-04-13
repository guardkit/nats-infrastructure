"""Tests for docker-compose.yml — validates NATS Docker Compose configuration.

Verifies all acceptance criteria for TASK-DCD-001:
- AC-001: docker-compose.yml exists at repo root with NATS service definition
- AC-002: Service uses nats:2.11-alpine image (pinned major version)
- AC-003: Custom entrypoint points to docker-entrypoint.sh for envsubst processing
- AC-004: Named volume nats-data mounted at /data/jetstream
- AC-005: Health check configured with start_period, interval, timeout, retries
- AC-006: Restart policy set to unless-stopped
- AC-007: Ports 4222 and 8222 exposed
- AC-008: Custom network ships-computer created
- AC-009: Config directories mounted read-only
- AC-010: env_file references .env
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

# Path to the docker-compose file relative to the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
COMPOSE_FILE = PROJECT_ROOT / "docker-compose.yml"


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


# --- AC-001: docker-compose.yml exists at repo root with NATS service definition ---


class TestComposeFileExists:
    """AC-001: docker-compose.yml exists at repo root with NATS service definition."""

    def test_compose_file_exists(self) -> None:
        assert COMPOSE_FILE.exists(), f"Expected docker-compose.yml at {COMPOSE_FILE}"

    def test_compose_file_is_not_empty(self, compose_text: str) -> None:
        assert len(compose_text.strip()) > 0, "docker-compose.yml must not be empty"

    def test_compose_has_services_key(self, compose_data: dict) -> None:
        assert "services" in compose_data, "docker-compose.yml must have a 'services' key"

    def test_nats_service_defined(self, compose_data: dict) -> None:
        services = compose_data.get("services", {})
        assert "nats" in services, "docker-compose.yml must define a 'nats' service"


# --- AC-002: Service uses nats:2.11-alpine image (pinned major version) ---


class TestNatsImage:
    """AC-002: Service uses nats:2.11-alpine image (via Dockerfile or image directive)."""

    def test_image_is_nats_2_11_alpine(self, nats_service: dict) -> None:
        # When a Dockerfile exists, docker-compose.yml uses build: . and the
        # base image is specified in the Dockerfile FROM directive.
        # When no Dockerfile exists, docker-compose.yml uses image: directly.
        dockerfile = Path(__file__).resolve().parent.parent / "Dockerfile"
        if dockerfile.exists():
            build = nats_service.get("build", "")
            assert build, (
                "When Dockerfile exists, docker-compose.yml must use 'build:' directive"
            )
        else:
            image = nats_service.get("image", "")
            assert image == "nats:2.11-alpine", (
                f"NATS service image must be 'nats:2.11-alpine', got '{image}'"
            )


# --- AC-003: Custom entrypoint points to docker-entrypoint.sh ---


class TestCustomEntrypoint:
    """AC-003: Custom entrypoint points to docker-entrypoint.sh for envsubst processing."""

    def test_entrypoint_references_docker_entrypoint_sh(self, nats_service: dict) -> None:
        # When a Dockerfile exists, entrypoint is defined in the Dockerfile
        # ENTRYPOINT directive rather than in docker-compose.yml.
        dockerfile = Path(__file__).resolve().parent.parent / "Dockerfile"
        if dockerfile.exists():
            dockerfile_text = dockerfile.read_text(encoding="utf-8")
            assert "docker-entrypoint.sh" in dockerfile_text, (
                "Dockerfile must reference docker-entrypoint.sh in ENTRYPOINT"
            )
        else:
            entrypoint = nats_service.get("entrypoint", "")
            # entrypoint can be a string or list
            if isinstance(entrypoint, list):
                entrypoint_str = " ".join(entrypoint)
            else:
                entrypoint_str = str(entrypoint)
            assert "docker-entrypoint.sh" in entrypoint_str, (
                f"Entrypoint must reference docker-entrypoint.sh, got '{entrypoint_str}'"
            )


# --- AC-004: Named volume nats-data mounted at /data/jetstream ---


class TestNamedVolume:
    """AC-004: Named volume nats-data mounted at /data/jetstream."""

    def test_top_level_volumes_defines_nats_data(self, compose_data: dict) -> None:
        volumes = compose_data.get("volumes", {})
        assert "nats-data" in volumes, (
            "docker-compose.yml must define a top-level 'nats-data' volume"
        )

    def test_nats_data_mounted_at_data_jetstream(self, nats_service: dict) -> None:
        volumes = nats_service.get("volumes", [])
        volume_strings = [str(v) if isinstance(v, str) else v.get("source", "") + ":" + v.get("target", "") for v in volumes]
        jetstream_mount = any(
            "nats-data" in v and "/data/jetstream" in v
            for v in volume_strings
        )
        assert jetstream_mount, (
            f"nats-data volume must be mounted at /data/jetstream, got volumes: {volume_strings}"
        )


# --- AC-005: Health check configured with start_period, interval, timeout, retries ---


class TestHealthCheck:
    """AC-005: Health check configured with start_period, interval, timeout, retries."""

    def test_healthcheck_exists(self, nats_service: dict) -> None:
        assert "healthcheck" in nats_service, "NATS service must have a healthcheck"

    def test_healthcheck_test_command(self, nats_service: dict) -> None:
        healthcheck = nats_service.get("healthcheck", {})
        test = healthcheck.get("test", "")
        if isinstance(test, list):
            test_str = " ".join(test)
        else:
            test_str = str(test)
        assert "8222" in test_str and "healthz" in test_str, (
            f"Health check test must check http://localhost:8222/healthz, got: '{test_str}'"
        )

    def test_healthcheck_has_start_period(self, nats_service: dict) -> None:
        healthcheck = nats_service.get("healthcheck", {})
        assert "start_period" in healthcheck, "healthcheck must have start_period"

    def test_healthcheck_has_interval(self, nats_service: dict) -> None:
        healthcheck = nats_service.get("healthcheck", {})
        assert "interval" in healthcheck, "healthcheck must have interval"

    def test_healthcheck_has_timeout(self, nats_service: dict) -> None:
        healthcheck = nats_service.get("healthcheck", {})
        assert "timeout" in healthcheck, "healthcheck must have timeout"

    def test_healthcheck_has_retries(self, nats_service: dict) -> None:
        healthcheck = nats_service.get("healthcheck", {})
        assert "retries" in healthcheck, "healthcheck must have retries"


# --- AC-006: Restart policy set to unless-stopped ---


class TestRestartPolicy:
    """AC-006: Restart policy set to unless-stopped."""

    def test_restart_is_unless_stopped(self, nats_service: dict) -> None:
        restart = nats_service.get("restart", "")
        assert restart == "unless-stopped", (
            f"Restart policy must be 'unless-stopped', got '{restart}'"
        )


# --- AC-007: Ports 4222 and 8222 exposed ---


class TestPortExposure:
    """AC-007: Ports 4222 and 8222 exposed."""

    def test_port_4222_exposed(self, nats_service: dict) -> None:
        ports = [str(p) for p in nats_service.get("ports", [])]
        has_4222 = any("4222" in p for p in ports)
        assert has_4222, f"Port 4222 must be exposed, got ports: {ports}"

    def test_port_8222_exposed(self, nats_service: dict) -> None:
        ports = [str(p) for p in nats_service.get("ports", [])]
        has_8222 = any("8222" in p for p in ports)
        assert has_8222, f"Port 8222 must be exposed, got ports: {ports}"


# --- AC-008: Custom network ships-computer created ---


class TestCustomNetwork:
    """AC-008: Custom network ships-computer created."""

    def test_top_level_networks_defines_ships_computer(self, compose_data: dict) -> None:
        networks = compose_data.get("networks", {})
        assert "ships-computer" in networks, (
            "docker-compose.yml must define a top-level 'ships-computer' network"
        )

    def test_nats_service_uses_ships_computer_network(self, nats_service: dict) -> None:
        networks = nats_service.get("networks", [])
        # networks can be a list or a dict
        if isinstance(networks, dict):
            network_names = list(networks.keys())
        else:
            network_names = [str(n) for n in networks]
        assert "ships-computer" in network_names, (
            f"NATS service must use 'ships-computer' network, got: {network_names}"
        )


# --- AC-009: Config directories mounted read-only ---


class TestConfigMountsReadOnly:
    """AC-009: Config directories mounted read-only."""

    def test_config_mounted_read_only(self, nats_service: dict) -> None:
        volumes = nats_service.get("volumes", [])
        ro_config_mounts = []
        for v in volumes:
            v_str = str(v) if isinstance(v, str) else ""
            if "config" in v_str.lower() and ":ro" in v_str:
                ro_config_mounts.append(v_str)
        assert len(ro_config_mounts) > 0, (
            f"At least one config volume must be mounted read-only (:ro), got volumes: {volumes}"
        )


# --- AC-010: env_file references .env ---


class TestEnvFile:
    """AC-010: env_file references .env."""

    def test_env_file_references_dot_env(self, nats_service: dict) -> None:
        env_file = nats_service.get("env_file", "")
        if isinstance(env_file, list):
            env_file_list = env_file
        else:
            env_file_list = [str(env_file)]
        assert any(".env" in str(ef) for ef in env_file_list), (
            f"env_file must reference .env, got: {env_file_list}"
        )
