"""Tests for config/nats-server.conf — validates NATS server configuration.

Verifies all acceptance criteria for TASK-NATS-001:
- AC-001: Config file exists with all required settings
- AC-002: JetStream block with store_dir, max_mem, max_file
- AC-003: Server listens on 0.0.0.0:4222 (client) and 0.0.0.0:8222 (monitoring)
- AC-004: Include directive references accounts/*.conf
- AC-005: Config file has clear comments explaining each section
- AC-006: Config syntax is valid NATS server configuration format
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

# Path to the config file relative to the project root
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
CONFIG_FILE = CONFIG_DIR / "nats-server.conf"


@pytest.fixture
def config_text() -> str:
    """Read the NATS server config file content."""
    assert CONFIG_FILE.exists(), f"Config file not found at {CONFIG_FILE}"
    return CONFIG_FILE.read_text(encoding="utf-8")


# --- AC-001: config/nats-server.conf exists with all settings from requirements ---


class TestConfigFileExists:
    """AC-001: config/nats-server.conf exists with all settings from requirements."""

    def test_config_file_exists(self) -> None:
        assert CONFIG_FILE.exists(), f"Expected config file at {CONFIG_FILE}"

    def test_config_file_is_not_empty(self, config_text: str) -> None:
        assert len(config_text.strip()) > 0, "Config file must not be empty"

    def test_server_name_is_ships_computer(self, config_text: str) -> None:
        assert re.search(
            r'server_name\s*:\s*"?ships-computer"?', config_text
        ), "server_name must be 'ships-computer'"

    def test_max_payload_is_1mb(self, config_text: str) -> None:
        # 1MB = 1048576 bytes
        assert re.search(
            r"max_payload\s*:\s*1048576\b", config_text
        ) or re.search(
            r"max_payload\s*:\s*1MB\b", config_text
        ), "max_payload must be 1MB (1048576 bytes or 1MB)"

    def test_debug_disabled(self, config_text: str) -> None:
        assert re.search(
            r"debug\s*:\s*false", config_text
        ), "debug must be disabled (false)"

    def test_trace_disabled(self, config_text: str) -> None:
        assert re.search(
            r"trace\s*:\s*false", config_text
        ), "trace must be disabled (false)"


# --- AC-002: JetStream block configured with store_dir, max_mem, max_file ---


class TestJetStreamConfiguration:
    """AC-002: JetStream block configured with store_dir, max_mem, max_file."""

    def test_jetstream_block_exists(self, config_text: str) -> None:
        assert re.search(
            r"jetstream\s*\{", config_text
        ), "JetStream configuration block must exist"

    def test_jetstream_store_dir(self, config_text: str) -> None:
        assert re.search(
            r'store_dir\s*:\s*"?/data/jetstream"?', config_text
        ), "JetStream store_dir must be '/data/jetstream'"

    def test_jetstream_max_mem(self, config_text: str) -> None:
        assert re.search(
            r"max_mem\s*:\s*1GB?\b", config_text, re.IGNORECASE
        ) or re.search(
            r"max_mem\s*:\s*1073741824\b", config_text
        ), "JetStream max_mem must be 1GB"

    def test_jetstream_max_file(self, config_text: str) -> None:
        assert re.search(
            r"max_file\s*:\s*10GB?\b", config_text, re.IGNORECASE
        ) or re.search(
            r"max_file\s*:\s*10737418240\b", config_text
        ), "JetStream max_file must be 10GB"


# --- AC-003: Server listens on 0.0.0.0:4222 (client) and 0.0.0.0:8222 (monitoring) ---


class TestNetworkBindings:
    """AC-003: Server listens on 0.0.0.0:4222 and 0.0.0.0:8222."""

    def test_client_port_4222(self, config_text: str) -> None:
        assert re.search(
            r"port\s*:\s*4222\b", config_text
        ), "Client port must be 4222"

    def test_client_listen_address(self, config_text: str) -> None:
        # Either host: "0.0.0.0" or listen: "0.0.0.0:4222"
        has_host = re.search(r'host\s*:\s*"?0\.0\.0\.0"?', config_text)
        has_listen = re.search(r'listen\s*:\s*"?0\.0\.0\.0:4222"?', config_text)
        assert has_host or has_listen, (
            "Client must bind to 0.0.0.0 (via host or listen directive)"
        )

    def test_monitoring_port_8222(self, config_text: str) -> None:
        assert re.search(
            r"http_port\s*:\s*8222\b", config_text
        ) or re.search(
            r"http\s*:\s*"
            r'"?0\.0\.0\.0:8222"?',
            config_text,
        ), "Monitoring HTTP port must be 8222"

    def test_monitoring_bind_address(self, config_text: str) -> None:
        # http: "0.0.0.0:8222" or http_port with separate host
        has_http_full = re.search(r'http\s*:\s*"?0\.0\.0\.0:8222"?', config_text)
        has_http_port = re.search(r"http_port\s*:\s*8222\b", config_text)
        assert has_http_full or has_http_port, (
            "Monitoring must be accessible on 0.0.0.0:8222"
        )


# --- AC-004: Include directive references accounts/*.conf ---


class TestIncludeDirective:
    """AC-004: Include directive references accounts/*.conf."""

    def test_include_accounts_conf(self, config_text: str) -> None:
        assert re.search(
            r'include\s+["\']?.*accounts/\*\.conf["\']?', config_text
        ), "Must include 'accounts/*.conf' via include directive"


# --- AC-005: Config file has clear comments explaining each section ---


class TestConfigComments:
    """AC-005: Config file has clear comments explaining each section."""

    def test_has_comment_lines(self, config_text: str) -> None:
        comment_lines = [
            line for line in config_text.splitlines() if line.strip().startswith("#")
        ]
        assert len(comment_lines) >= 5, (
            f"Config should have at least 5 comment lines for clarity, found {len(comment_lines)}"
        )

    def test_has_jetstream_section_comment(self, config_text: str) -> None:
        assert re.search(
            r"#.*[Jj]et[Ss]tream", config_text
        ), "JetStream section should have an explanatory comment"

    def test_has_logging_section_comment(self, config_text: str) -> None:
        assert re.search(
            r"#.*[Ll]og", config_text
        ), "Logging section should have an explanatory comment"


# --- AC-006: Config syntax is valid NATS server configuration format ---


class TestConfigSyntax:
    """AC-006: Config syntax is valid NATS server configuration format."""

    def test_braces_balanced(self, config_text: str) -> None:
        # Strip comments and check brace balance
        stripped = re.sub(r"#.*", "", config_text)
        open_count = stripped.count("{")
        close_count = stripped.count("}")
        assert open_count == close_count, (
            f"Braces not balanced: {open_count} opening vs {close_count} closing"
        )

    def test_no_json_syntax(self, config_text: str) -> None:
        """NATS native config does not use JSON commas between fields."""
        # Strip comments first
        stripped = re.sub(r"#.*", "", config_text)
        # NATS config uses newlines, not commas, to separate fields
        # A line ending with a comma (outside of a value) indicates JSON syntax
        json_commas = re.findall(r'^\s*\w+\s*:.*,\s*$', stripped, re.MULTILINE)
        assert len(json_commas) == 0, (
            f"Config should use NATS native format, not JSON. Found lines with trailing commas: {json_commas}"
        )

    def test_uses_nats_config_format(self, config_text: str) -> None:
        """Verify key: value format (NATS native), not key = value."""
        # At least some lines should use key: value format
        kv_lines = re.findall(r"^\s*\w+\s*:", config_text, re.MULTILINE)
        assert len(kv_lines) >= 3, (
            "Config should use NATS native 'key: value' format"
        )


# --- Logging Configuration ---


class TestLoggingConfiguration:
    """Verify logging configuration from requirements."""

    def test_log_file_path(self, config_text: str) -> None:
        assert re.search(
            r'log_file\s*:\s*"?/var/log/nats/nats-server\.log"?', config_text
        ), "log_file must be '/var/log/nats/nats-server.log'"

    def test_logtime_enabled(self, config_text: str) -> None:
        assert re.search(
            r"logtime\s*:\s*true", config_text
        ), "logtime must be enabled (true) for timestamps"
