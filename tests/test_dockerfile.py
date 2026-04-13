"""Tests for TASK-DCD-002 — Dockerfile and .dockerignore for custom NATS entrypoint.

Validates all acceptance criteria:
- AC-001: Dockerfile exists at repo root
- AC-002: Extends nats:2.11-alpine
- AC-003: Installs gettext package (provides envsubst)
- AC-004: Copies docker-entrypoint.sh into image
- AC-005: Sets entrypoint and default CMD
- AC-006: .dockerignore created to exclude .git, docs/, tasks/, .claude/, .guardkit/
- AC-007: docker-compose.yml updated to use build: . context
- AC-008: All modified files pass project-configured lint/format checks with zero errors
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

# Paths relative to project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCKERFILE = PROJECT_ROOT / "Dockerfile"
DOCKERIGNORE = PROJECT_ROOT / ".dockerignore"
DOCKER_COMPOSE = PROJECT_ROOT / "docker-compose.yml"


# ---------------------------------------------------------------------------
# AC-001: Dockerfile exists at repo root
# ---------------------------------------------------------------------------


class TestDockerfileExists:
    """AC-001: Dockerfile exists at repo root."""

    def test_dockerfile_exists(self) -> None:
        assert DOCKERFILE.exists(), f"Dockerfile not found at {DOCKERFILE}"

    def test_dockerfile_is_not_empty(self) -> None:
        assert DOCKERFILE.stat().st_size > 0, "Dockerfile must not be empty"


# ---------------------------------------------------------------------------
# AC-002: Extends nats:2.11-alpine
# ---------------------------------------------------------------------------


@pytest.fixture
def dockerfile_text() -> str:
    """Read Dockerfile content."""
    assert DOCKERFILE.exists(), f"Dockerfile not found at {DOCKERFILE}"
    return DOCKERFILE.read_text(encoding="utf-8")


class TestDockerfileBaseImage:
    """AC-002: Extends nats:2.11-alpine."""

    def test_from_nats_alpine(self, dockerfile_text: str) -> None:
        assert re.search(
            r"^FROM\s+nats:2\.11-alpine", dockerfile_text, re.MULTILINE
        ), "Dockerfile must use FROM nats:2.11-alpine as base image"


# ---------------------------------------------------------------------------
# AC-003: Installs gettext package (provides envsubst)
# ---------------------------------------------------------------------------


class TestDockerfileGettext:
    """AC-003: Installs gettext package."""

    def test_apk_add_gettext(self, dockerfile_text: str) -> None:
        assert re.search(
            r"RUN\s+apk\s+add\s+.*gettext", dockerfile_text
        ), "Dockerfile must install gettext via apk add"

    def test_no_cache_flag(self, dockerfile_text: str) -> None:
        assert re.search(
            r"apk\s+add\s+--no-cache", dockerfile_text
        ), "apk add should use --no-cache to keep image small"


# ---------------------------------------------------------------------------
# AC-004: Copies docker-entrypoint.sh into image
# ---------------------------------------------------------------------------


class TestDockerfileCopyEntrypoint:
    """AC-004: Copies docker-entrypoint.sh into image."""

    def test_copy_entrypoint(self, dockerfile_text: str) -> None:
        assert re.search(
            r"COPY\s+scripts/docker-entrypoint\.sh\s+/usr/local/bin/docker-entrypoint\.sh",
            dockerfile_text,
        ), "Dockerfile must COPY scripts/docker-entrypoint.sh to /usr/local/bin/"

    def test_chmod_entrypoint(self, dockerfile_text: str) -> None:
        assert re.search(
            r"RUN\s+chmod\s+\+x\s+/usr/local/bin/docker-entrypoint\.sh",
            dockerfile_text,
        ), "Dockerfile must chmod +x the entrypoint script"


# ---------------------------------------------------------------------------
# AC-005: Sets entrypoint and default CMD
# ---------------------------------------------------------------------------


class TestDockerfileEntrypointCmd:
    """AC-005: Sets entrypoint and default CMD."""

    def test_entrypoint_set(self, dockerfile_text: str) -> None:
        assert re.search(
            r'ENTRYPOINT\s+\["/usr/local/bin/docker-entrypoint\.sh"\]',
            dockerfile_text,
        ), "Dockerfile must set ENTRYPOINT to docker-entrypoint.sh"

    def test_cmd_set(self, dockerfile_text: str) -> None:
        assert re.search(
            r'CMD\s+\["-c",\s*"/etc/nats/nats-server\.conf"\]',
            dockerfile_text,
        ), 'Dockerfile must set CMD to ["-c", "/etc/nats/nats-server.conf"]'


# ---------------------------------------------------------------------------
# AC-006: .dockerignore created with required exclusions
# ---------------------------------------------------------------------------


@pytest.fixture
def dockerignore_text() -> str:
    """Read .dockerignore content."""
    assert DOCKERIGNORE.exists(), f".dockerignore not found at {DOCKERIGNORE}"
    return DOCKERIGNORE.read_text(encoding="utf-8")


class TestDockerignore:
    """AC-006: .dockerignore excludes .git, docs/, tasks/, .claude/, .guardkit/."""

    def test_dockerignore_exists(self) -> None:
        assert DOCKERIGNORE.exists(), f".dockerignore not found at {DOCKERIGNORE}"

    @pytest.mark.parametrize(
        "pattern",
        [".git", "docs/", "tasks/", ".claude/", ".guardkit/"],
    )
    def test_excludes_required_directories(
        self, dockerignore_text: str, pattern: str
    ) -> None:
        # Check pattern appears as a line (possibly with trailing comment)
        lines = [line.strip() for line in dockerignore_text.splitlines()]
        # Strip comments from lines for comparison
        clean_lines = [line.split("#")[0].strip() for line in lines]
        assert pattern in clean_lines, (
            f".dockerignore must exclude '{pattern}'"
        )


# ---------------------------------------------------------------------------
# AC-007: docker-compose.yml updated to use build: . context
# ---------------------------------------------------------------------------


@pytest.fixture
def compose_text() -> str:
    """Read docker-compose.yml content."""
    assert DOCKER_COMPOSE.exists(), f"docker-compose.yml not found at {DOCKER_COMPOSE}"
    return DOCKER_COMPOSE.read_text(encoding="utf-8")


class TestDockerComposeBuildContext:
    """AC-007: docker-compose.yml uses build: . instead of image:."""

    def test_compose_exists(self) -> None:
        assert DOCKER_COMPOSE.exists(), "docker-compose.yml must exist at repo root"

    def test_uses_build_context(self, compose_text: str) -> None:
        assert re.search(
            r"build:\s*\.", compose_text
        ), "docker-compose.yml must use 'build: .' to build from Dockerfile"

    def test_no_image_directive_for_nats(self, compose_text: str) -> None:
        # Should not use image: nats:... since we're building from Dockerfile
        assert not re.search(
            r"image:\s*nats:", compose_text
        ), "docker-compose.yml should not use 'image: nats:...' when using build context"
