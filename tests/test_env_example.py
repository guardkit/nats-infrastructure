"""Tests for TASK-NATS-003 — .env.example with all configuration variables.

Validates all acceptance criteria:
- AC-001: .env.example exists at repository root
- AC-002: All 4 password variables documented with placeholder values
- AC-003: Comments explain each variable's purpose
- AC-004: .env is in .gitignore (already confirmed)
- AC-005: README or comments reference .env.example as setup guide
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

# Paths relative to project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_EXAMPLE_FILE = PROJECT_ROOT / ".env.example"
GITIGNORE_FILE = PROJECT_ROOT / ".gitignore"
README_FILE = PROJECT_ROOT / "README.md"

# The 4 required password variables
REQUIRED_VARS = [
    "RICH_NATS_PASSWORD",
    "JAMES_NATS_PASSWORD",
    "MARK_NATS_PASSWORD",
    "ADMIN_NATS_PASSWORD",
]


@pytest.fixture
def env_example_text() -> str:
    """Read the .env.example file content."""
    assert ENV_EXAMPLE_FILE.exists(), f".env.example not found at {ENV_EXAMPLE_FILE}"
    return ENV_EXAMPLE_FILE.read_text(encoding="utf-8")


@pytest.fixture
def gitignore_text() -> str:
    """Read the .gitignore file content."""
    assert GITIGNORE_FILE.exists(), f".gitignore not found at {GITIGNORE_FILE}"
    return GITIGNORE_FILE.read_text(encoding="utf-8")


@pytest.fixture
def readme_text() -> str:
    """Read the README.md file content."""
    assert README_FILE.exists(), f"README.md not found at {README_FILE}"
    return README_FILE.read_text(encoding="utf-8")


# --- AC-001: .env.example exists at repository root ---


class TestEnvExampleExists:
    """AC-001: .env.example exists at repository root."""

    def test_env_example_file_exists(self) -> None:
        assert ENV_EXAMPLE_FILE.exists(), (
            f"Expected .env.example at {ENV_EXAMPLE_FILE}"
        )

    def test_env_example_is_not_empty(self, env_example_text: str) -> None:
        assert len(env_example_text.strip()) > 0, ".env.example must not be empty"

    def test_env_example_at_repository_root(self) -> None:
        """The .env.example must be at the project root, not in a subdirectory."""
        assert ENV_EXAMPLE_FILE.parent == PROJECT_ROOT, (
            ".env.example must be at the repository root"
        )


# --- AC-002: All 4 password variables documented with placeholder values ---


class TestPasswordVariables:
    """AC-002: All 4 password variables documented with placeholder values."""

    @pytest.mark.parametrize("var_name", REQUIRED_VARS)
    def test_variable_is_present(
        self, env_example_text: str, var_name: str
    ) -> None:
        """Each required password variable must appear in .env.example."""
        assert var_name in env_example_text, (
            f"{var_name} must be defined in .env.example"
        )

    @pytest.mark.parametrize("var_name", REQUIRED_VARS)
    def test_variable_has_placeholder_value(
        self, env_example_text: str, var_name: str
    ) -> None:
        """Each variable must have a placeholder value (e.g. 'changeme'), not be empty."""
        pattern = rf"^{var_name}=(\S+)"
        match = re.search(pattern, env_example_text, re.MULTILINE)
        assert match, f"{var_name} must have an assigned value (not empty)"
        value = match.group(1)
        assert value == "changeme", (
            f"{var_name} should have placeholder value 'changeme', got '{value}'"
        )

    def test_all_four_variables_present(self, env_example_text: str) -> None:
        """Verify all 4 required variables are present in the file."""
        for var_name in REQUIRED_VARS:
            assert re.search(
                rf"^{var_name}=", env_example_text, re.MULTILINE
            ), f"Missing required variable: {var_name}"

    def test_no_real_passwords(self, env_example_text: str) -> None:
        """Placeholder values must not look like real passwords."""
        for var_name in REQUIRED_VARS:
            pattern = rf"^{var_name}=(\S+)"
            match = re.search(pattern, env_example_text, re.MULTILINE)
            if match:
                value = match.group(1)
                # Real passwords are typically long and complex
                assert len(value) < 20, (
                    f"{var_name} has a suspiciously long value — should be a placeholder"
                )


# --- AC-003: Comments explain each variable's purpose ---


class TestVariableComments:
    """AC-003: Comments explain each variable's purpose."""

    def test_has_comment_lines(self, env_example_text: str) -> None:
        """The file must have substantial comments explaining variables."""
        comment_lines = [
            line
            for line in env_example_text.splitlines()
            if line.strip().startswith("#")
        ]
        assert len(comment_lines) >= 8, (
            f"Expected at least 8 comment lines for thorough documentation, "
            f"found {len(comment_lines)}"
        )

    @pytest.mark.parametrize("var_name", REQUIRED_VARS)
    def test_variable_has_preceding_comment(
        self, env_example_text: str, var_name: str
    ) -> None:
        """Each variable must have a comment on the line(s) before it."""
        lines = env_example_text.splitlines()
        for i, line in enumerate(lines):
            if line.startswith(f"{var_name}="):
                # At least one of the preceding lines should be a comment
                preceding_comments = []
                j = i - 1
                while j >= 0 and (
                    lines[j].strip().startswith("#") or lines[j].strip() == ""
                ):
                    if lines[j].strip().startswith("#"):
                        preceding_comments.append(lines[j])
                    j -= 1
                assert len(preceding_comments) >= 1, (
                    f"{var_name} must have at least one comment line preceding it"
                )
                return
        pytest.fail(f"{var_name} not found as a variable assignment in .env.example")

    def test_comments_mention_account_names(self, env_example_text: str) -> None:
        """Comments should reference the NATS account names (APPMILLA, FINPROXY, SYS)."""
        assert "APPMILLA" in env_example_text, (
            "Comments should reference the APPMILLA account"
        )
        assert "FINPROXY" in env_example_text, (
            "Comments should reference the FINPROXY account"
        )
        assert "SYS" in env_example_text, (
            "Comments should reference the SYS account"
        )

    def test_comments_mention_no_default(self, env_example_text: str) -> None:
        """Comments should note that variables have no default value."""
        # At least one mention of no default
        assert re.search(
            r"[Nn]o default", env_example_text
        ), "Comments should note that password variables have no default value"


# --- AC-004: .env is in .gitignore ---


class TestGitignore:
    """AC-004: .env is in .gitignore (already confirmed)."""

    def test_env_in_gitignore(self, gitignore_text: str) -> None:
        """The .env file must be in .gitignore to prevent password leaks."""
        assert re.search(
            r"^\.env$", gitignore_text, re.MULTILINE
        ), ".env must be listed in .gitignore"

    def test_env_example_not_in_gitignore(self, gitignore_text: str) -> None:
        """The .env.example file must NOT be gitignored — it should be committed."""
        assert not re.search(
            r"^\.env\.example$", gitignore_text, re.MULTILINE
        ), ".env.example must NOT be in .gitignore — it is meant to be committed"


# --- AC-005: README or comments reference .env.example as setup guide ---


class TestSetupGuideReference:
    """AC-005: README or comments reference .env.example as setup guide."""

    def test_readme_references_env_example(self, readme_text: str) -> None:
        """README.md must reference .env.example."""
        assert ".env.example" in readme_text, (
            "README.md must reference .env.example as a setup guide"
        )

    def test_readme_mentions_copy_step(self, readme_text: str) -> None:
        """README should mention copying .env.example to .env."""
        assert re.search(
            r"cp\s+\.env\.example\s+\.env", readme_text
        ), "README should show 'cp .env.example .env' as a setup step"

    def test_env_example_self_documents_setup(self, env_example_text: str) -> None:
        """The .env.example file itself should reference its own usage as a setup guide."""
        assert re.search(
            r"[Cc]opy.*\.env", env_example_text
        ), ".env.example should mention copying itself to .env"


# --- Consistency Tests ---


class TestConsistencyWithTemplate:
    """Verify .env.example variables match those used in account templates."""

    def test_variables_match_template_references(
        self, env_example_text: str
    ) -> None:
        """Variables in .env.example must match those in accounts.conf.template."""
        template_file = PROJECT_ROOT / "config" / "accounts" / "accounts.conf.template"
        if not template_file.exists():
            pytest.skip("accounts.conf.template not found — skipping consistency check")
        template_text = template_file.read_text(encoding="utf-8")

        # Extract ${VAR} references from template
        template_vars = set(re.findall(r"\$\{(\w+_PASSWORD)\}", template_text))

        # Extract VAR= assignments from .env.example
        env_vars = set(re.findall(r"^(\w+_PASSWORD)=", env_example_text, re.MULTILINE))

        assert template_vars == env_vars, (
            f"Variable mismatch between template and .env.example.\n"
            f"In template but not .env.example: {template_vars - env_vars}\n"
            f"In .env.example but not template: {env_vars - template_vars}"
        )

    def test_variables_match_entrypoint_validation(
        self, env_example_text: str
    ) -> None:
        """Variables in .env.example must match those validated by docker-entrypoint.sh."""
        entrypoint_file = PROJECT_ROOT / "scripts" / "docker-entrypoint.sh"
        if not entrypoint_file.exists():
            pytest.skip("docker-entrypoint.sh not found — skipping consistency check")
        entrypoint_text = entrypoint_file.read_text(encoding="utf-8")

        # Extract variable names from the validation loop in the entrypoint
        entrypoint_vars = set(
            re.findall(r"\b(\w+_NATS_PASSWORD)\b", entrypoint_text)
        )

        # Extract VAR= assignments from .env.example
        env_vars = set(
            re.findall(r"^(\w+_NATS_PASSWORD)=", env_example_text, re.MULTILINE)
        )

        assert entrypoint_vars == env_vars, (
            f"Variable mismatch between entrypoint and .env.example.\n"
            f"In entrypoint but not .env.example: {entrypoint_vars - env_vars}\n"
            f"In .env.example but not entrypoint: {env_vars - entrypoint_vars}"
        )
