"""Tests for TASK-NATS-002 — account configuration and envsubst entrypoint.

Validates all acceptance criteria:
- AC-001: config/accounts/accounts.conf.template exists with all three accounts
- AC-002: Template uses ${VAR} syntax for all password fields
- AC-003: APPMILLA account: rich + james with full pub/sub, JetStream enabled
- AC-004: FINPROXY account: mark scoped to finproxy.> only, JetStream enabled
- AC-005: SYS account: admin user, designated as system_account
- AC-006: scripts/docker-entrypoint.sh runs envsubst then exec nats-server
- AC-007: No plaintext passwords committed to repository
"""
from __future__ import annotations

import re
import stat
from pathlib import Path

import pytest

# Paths relative to project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
ACCOUNTS_DIR = CONFIG_DIR / "accounts"
TEMPLATE_FILE = ACCOUNTS_DIR / "accounts.conf.template"
ENTRYPOINT_FILE = PROJECT_ROOT / "scripts" / "docker-entrypoint.sh"
GITIGNORE_FILE = PROJECT_ROOT / ".gitignore"


@pytest.fixture
def template_text() -> str:
    """Read the accounts template file content."""
    assert TEMPLATE_FILE.exists(), f"Template file not found at {TEMPLATE_FILE}"
    return TEMPLATE_FILE.read_text(encoding="utf-8")


@pytest.fixture
def entrypoint_text() -> str:
    """Read the docker entrypoint script content."""
    assert ENTRYPOINT_FILE.exists(), f"Entrypoint script not found at {ENTRYPOINT_FILE}"
    return ENTRYPOINT_FILE.read_text(encoding="utf-8")


@pytest.fixture
def gitignore_text() -> str:
    """Read the .gitignore file content."""
    assert GITIGNORE_FILE.exists(), f".gitignore not found at {GITIGNORE_FILE}"
    return GITIGNORE_FILE.read_text(encoding="utf-8")


def _extract_account_block(template_text: str, account_name: str) -> str:
    """Extract a named account block from the template, handling nested braces.

    Finds the account block by name (e.g. 'APPMILLA {') and returns
    everything from the account name through its closing brace, including
    all nested blocks.
    """
    # Mask ${VAR} references so braces inside them don't confuse counting.
    # The mask MUST be the same length as what it replaces: the brace scan
    # runs over `cleaned` but the final slice indexes back into the original
    # `template_text` (see below), so any length change would drift the offsets
    # and truncate the returned block.
    cleaned = re.sub(r"\$\{[^}]+\}", lambda m: "X" * len(m.group(0)), template_text)
    pattern = re.compile(rf"\b{account_name}\s*\{{")
    match = pattern.search(cleaned)
    if not match:
        return ""
    start = match.start()
    depth = 0
    for i in range(match.end() - 1, len(cleaned)):
        if cleaned[i] == "{":
            depth += 1
        elif cleaned[i] == "}":
            depth -= 1
            if depth == 0:
                # Return from the original text, not the cleaned version
                return template_text[start : i + 1]
    return template_text[start:]


# --- AC-001: accounts.conf.template exists with all three accounts ---


class TestTemplateFileExists:
    """AC-001: config/accounts/accounts.conf.template exists with all three accounts."""

    def test_template_file_exists(self) -> None:
        assert TEMPLATE_FILE.exists(), f"Expected template at {TEMPLATE_FILE}"

    def test_template_file_is_not_empty(self, template_text: str) -> None:
        assert len(template_text.strip()) > 0, "Template file must not be empty"

    def test_template_contains_appmilla_account(self, template_text: str) -> None:
        assert re.search(
            r"APPMILLA", template_text
        ), "Template must define APPMILLA account"

    def test_template_contains_finproxy_account(self, template_text: str) -> None:
        assert re.search(
            r"FINPROXY", template_text
        ), "Template must define FINPROXY account"

    def test_template_contains_sys_account(self, template_text: str) -> None:
        assert re.search(
            r"\bSYS\b", template_text
        ), "Template must define SYS account"


# --- AC-002: Template uses ${VAR} syntax for all password fields ---


class TestTemplateVariables:
    """AC-002: Template uses ${VAR} syntax for all password fields."""

    def test_rich_password_variable(self, template_text: str) -> None:
        assert "${RICH_NATS_PASSWORD}" in template_text, (
            "Template must use ${RICH_NATS_PASSWORD} for Rich's password"
        )

    def test_james_password_variable(self, template_text: str) -> None:
        assert "${JAMES_NATS_PASSWORD}" in template_text, (
            "Template must use ${JAMES_NATS_PASSWORD} for James's password"
        )

    def test_mark_password_variable(self, template_text: str) -> None:
        assert "${MARK_NATS_PASSWORD}" in template_text, (
            "Template must use ${MARK_NATS_PASSWORD} for Mark's password"
        )

    def test_admin_password_variable(self, template_text: str) -> None:
        assert "${ADMIN_NATS_PASSWORD}" in template_text, (
            "Template must use ${ADMIN_NATS_PASSWORD} for admin password"
        )

    def test_no_hardcoded_passwords(self, template_text: str) -> None:
        """Passwords must only appear as ${VAR} references, not hardcoded values."""
        # Find all password field values in the template
        password_fields = re.findall(
            r'password\s*:\s*"(\$\{[^}]+\}|[^"]*)"',
            template_text,
            re.IGNORECASE,
        )
        assert len(password_fields) > 0, "Template must contain password fields"
        for value in password_fields:
            assert value.startswith("${"), (
                f"Found hardcoded password value: '{value}' — must use ${{VAR}} syntax"
            )


# --- AC-003: APPMILLA account with rich + james, full pub/sub, JetStream ---


class TestAppmillaAccount:
    """AC-003: APPMILLA account: rich + james with full pub/sub, JetStream enabled."""

    def test_appmilla_has_rich_user(self, template_text: str) -> None:
        assert re.search(
            r"user\s*:\s*\"?rich\"?", template_text
        ), "APPMILLA account must have user 'rich'"

    def test_appmilla_has_james_user(self, template_text: str) -> None:
        assert re.search(
            r"user\s*:\s*\"?james\"?", template_text
        ), "APPMILLA account must have user 'james'"

    def test_appmilla_full_publish_access(self, template_text: str) -> None:
        """APPMILLA users must have publish permission to > (all subjects)."""
        appmilla_block = _extract_account_block(template_text, "APPMILLA")
        assert appmilla_block, "APPMILLA account block not found"
        assert re.search(
            r'publish\s*:\s*"?>"?', appmilla_block
        ), "APPMILLA must have publish permission to '>'"

    def test_appmilla_full_subscribe_access(self, template_text: str) -> None:
        """APPMILLA users must have subscribe permission to > (all subjects)."""
        appmilla_block = _extract_account_block(template_text, "APPMILLA")
        assert appmilla_block, "APPMILLA account block not found"
        assert re.search(
            r'subscribe\s*:\s*"?>"?', appmilla_block
        ), "APPMILLA must have subscribe permission to '>'"

    def test_appmilla_jetstream_enabled(self, template_text: str) -> None:
        """APPMILLA account must have JetStream enabled."""
        appmilla_block = _extract_account_block(template_text, "APPMILLA")
        assert appmilla_block, "APPMILLA account block not found"
        has_block = re.search(r"jetstream\s*\{", appmilla_block, re.IGNORECASE)
        has_inline = re.search(r"jetstream\s*:\s*enabled", appmilla_block, re.IGNORECASE)
        assert has_block or has_inline, "APPMILLA must have JetStream enabled"


# --- AC-004: FINPROXY account with mark, scoped to finproxy.> ---


class TestFinproxyAccount:
    """AC-004: FINPROXY account: mark scoped to finproxy.> only, JetStream enabled."""

    def test_finproxy_has_mark_user(self, template_text: str) -> None:
        assert re.search(
            r"user\s*:\s*\"?mark\"?", template_text
        ), "FINPROXY account must have user 'mark'"

    def test_finproxy_publish_scoped(self, template_text: str) -> None:
        """FINPROXY must have publish scoped to finproxy.> only."""
        finproxy_block = _extract_account_block(template_text, "FINPROXY")
        assert finproxy_block, "FINPROXY account block not found"
        assert re.search(
            r'publish\s*:\s*"?finproxy\.>"?', finproxy_block
        ), "FINPROXY must have publish scoped to 'finproxy.>'"

    def test_finproxy_subscribe_scoped(self, template_text: str) -> None:
        """FINPROXY must have subscribe scoped to finproxy.> only."""
        finproxy_block = _extract_account_block(template_text, "FINPROXY")
        assert finproxy_block, "FINPROXY account block not found"
        assert re.search(
            r'subscribe\s*:\s*"?finproxy\.>"?', finproxy_block
        ), "FINPROXY must have subscribe scoped to 'finproxy.>'"

    def test_finproxy_jetstream_enabled(self, template_text: str) -> None:
        """FINPROXY must have JetStream enabled."""
        finproxy_block = _extract_account_block(template_text, "FINPROXY")
        assert finproxy_block, "FINPROXY account block not found"
        has_block = re.search(r"jetstream\s*\{", finproxy_block, re.IGNORECASE)
        has_inline = re.search(r"jetstream\s*:\s*enabled", finproxy_block, re.IGNORECASE)
        assert has_block or has_inline, "FINPROXY must have JetStream enabled"


# --- AC-005: SYS account with admin, designated as system_account ---


class TestSysAccount:
    """AC-005: SYS account: admin user, designated as system_account."""

    def test_sys_has_admin_user(self, template_text: str) -> None:
        assert re.search(
            r"user\s*:\s*\"?admin\"?", template_text
        ), "SYS account must have user 'admin'"

    def test_sys_designated_as_system_account(self, template_text: str) -> None:
        """system_account: SYS must be declared at the top level."""
        assert re.search(
            r"system_account\s*:\s*\"?SYS\"?", template_text
        ), "Template must declare 'system_account: SYS'"


# --- AC-006: scripts/docker-entrypoint.sh runs envsubst then exec nats-server ---


class TestDockerEntrypoint:
    """AC-006: scripts/docker-entrypoint.sh runs envsubst then exec nats-server."""

    def test_entrypoint_file_exists(self) -> None:
        assert ENTRYPOINT_FILE.exists(), f"Expected entrypoint at {ENTRYPOINT_FILE}"

    def test_entrypoint_is_executable(self) -> None:
        """Entrypoint script must have executable permission."""
        mode = ENTRYPOINT_FILE.stat().st_mode
        assert mode & stat.S_IXUSR, "Entrypoint must be executable (chmod +x)"

    def test_entrypoint_has_shebang(self, entrypoint_text: str) -> None:
        assert entrypoint_text.startswith("#!/"), (
            "Entrypoint must start with a shebang line (#!/bin/sh or #!/bin/bash)"
        )

    def test_entrypoint_runs_envsubst(self, entrypoint_text: str) -> None:
        assert "envsubst" in entrypoint_text, (
            "Entrypoint must run envsubst to substitute template variables"
        )

    def test_entrypoint_execs_nats_server(self, entrypoint_text: str) -> None:
        """Entrypoint must exec nats-server (not run in background)."""
        assert re.search(
            r"exec\s+.*nats-server", entrypoint_text
        ), "Entrypoint must 'exec nats-server' as the final command"

    def test_entrypoint_processes_template(self, entrypoint_text: str) -> None:
        """Entrypoint must process .conf.template files."""
        assert re.search(
            r"\.conf\.template", entrypoint_text
        ), "Entrypoint must reference .conf.template files for envsubst processing"

    def test_entrypoint_is_not_empty(self, entrypoint_text: str) -> None:
        assert len(entrypoint_text.strip()) > 0, "Entrypoint must not be empty"


# --- AC-007: No plaintext passwords committed to repository ---


class TestNoPlaintextPasswords:
    """AC-007: No plaintext passwords committed to repository."""

    def test_env_file_in_gitignore(self, gitignore_text: str) -> None:
        """The .env file must be in .gitignore to prevent password leaks."""
        assert re.search(
            r"^\.env$", gitignore_text, re.MULTILINE
        ), ".env must be listed in .gitignore"

    def test_template_has_no_real_passwords(self, template_text: str) -> None:
        """Template must not contain any real password strings."""
        # All password values should be ${VAR} references
        password_values = re.findall(
            r'pass(?:word)?\s*:\s*"?([^"\s}]+)"?',
            template_text,
            re.IGNORECASE,
        )
        for value in password_values:
            # Each password value should start with ${ (envsubst variable)
            assert value.startswith("${") or value == "", (
                f"Found potential plaintext password value: '{value}'"
            )

    def test_no_generated_conf_committed(self) -> None:
        """Generated .conf files (from templates) should not exist in config/accounts/."""
        generated_confs = list(ACCOUNTS_DIR.glob("*.conf"))
        assert len(generated_confs) == 0, (
            f"Generated .conf files should not be committed: {generated_confs}"
        )


# --- Structural / Syntax Tests ---


class TestTemplateSyntax:
    """Verify template uses valid NATS configuration syntax."""

    def test_braces_balanced(self, template_text: str) -> None:
        """All braces in the template must be balanced."""
        stripped = re.sub(r"#.*", "", template_text)
        # Remove ${VAR} references before counting (they contain braces)
        stripped = re.sub(r"\$\{[^}]+\}", "", stripped)
        open_count = stripped.count("{")
        close_count = stripped.count("}")
        assert open_count == close_count, (
            f"Braces not balanced: {open_count} opening vs {close_count} closing"
        )

    def test_uses_nats_config_format(self, template_text: str) -> None:
        """Template should use NATS native key: value format."""
        kv_lines = re.findall(r"^\s*\w+\s*:", template_text, re.MULTILINE)
        assert len(kv_lines) >= 5, (
            "Template should use NATS native 'key: value' format throughout"
        )

    def test_has_explanatory_comments(self, template_text: str) -> None:
        """Template should have comments explaining each account section."""
        comment_lines = [
            line for line in template_text.splitlines() if line.strip().startswith("#")
        ]
        assert len(comment_lines) >= 3, (
            f"Template should have at least 3 comment lines, found {len(comment_lines)}"
        )

    def test_accounts_block_exists(self, template_text: str) -> None:
        """Template must have an accounts block wrapping the account definitions."""
        assert re.search(
            r"accounts\s*\{", template_text
        ) or re.search(
            r"accounts\s*:", template_text
        ), "Template must have an 'accounts' block"
