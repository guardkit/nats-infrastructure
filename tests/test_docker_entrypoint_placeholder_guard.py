"""Tests for TASK-MDF-ENVS — placeholder-credential guards in docker-entrypoint.sh.

Validates the post-incident safeguards that refuse to start the NATS
container when any of the four required password vars is missing, empty,
or equal to the literal placeholder value ``changeme``, and refuse to start
when the processed accounts config still contains ``changeme`` or an
unsubstituted ``${VAR}`` reference after envsubst runs.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENTRYPOINT_FILE = PROJECT_ROOT / "scripts" / "docker-entrypoint.sh"
ENV_EXAMPLE_FILE = PROJECT_ROOT / ".env.example"
VERIFY_SCRIPT_FILE = PROJECT_ROOT / "scripts" / "verify-nats.sh"

REQUIRED_VARS = [
    "RICH_NATS_PASSWORD",
    "JAMES_NATS_PASSWORD",
    "MARK_NATS_PASSWORD",
    "ADMIN_NATS_PASSWORD",
]


@pytest.fixture
def entrypoint_text() -> str:
    return ENTRYPOINT_FILE.read_text(encoding="utf-8")


@pytest.fixture
def env_example_text() -> str:
    return ENV_EXAMPLE_FILE.read_text(encoding="utf-8")


@pytest.fixture
def verify_script_text() -> str:
    return VERIFY_SCRIPT_FILE.read_text(encoding="utf-8")


# --- Static source-level assertions -----------------------------------------


class TestEntrypointDefinesPlaceholderConstant:
    """The entrypoint must define a placeholder constant it can guard against."""

    def test_defines_placeholder_value(self, entrypoint_text: str) -> None:
        assert re.search(
            r'^\s*PLACEHOLDER_VALUE\s*=\s*"changeme"',
            entrypoint_text,
            re.MULTILINE,
        ), "Entrypoint must define PLACEHOLDER_VALUE=\"changeme\""

    @pytest.mark.parametrize("var_name", REQUIRED_VARS)
    def test_each_required_var_is_validated(
        self, entrypoint_text: str, var_name: str
    ) -> None:
        assert var_name in entrypoint_text, (
            f"Entrypoint must validate {var_name}"
        )


class TestEntrypointRejectsPlaceholderPreSubstitution:
    """Pre-envsubst: reject any env var that equals the placeholder."""

    def test_compares_value_to_placeholder(self, entrypoint_text: str) -> None:
        assert re.search(
            r'\[\s+"\$val"\s+=\s+"\$PLACEHOLDER_VALUE"\s+\]',
            entrypoint_text,
        ), (
            "Entrypoint must compare each env var value against "
            "$PLACEHOLDER_VALUE and reject matches"
        )

    def test_error_message_mentions_placeholder(self, entrypoint_text: str) -> None:
        assert re.search(
            r'Placeholder password.*\$\{?PLACEHOLDER_VALUE\}?',
            entrypoint_text,
        ), "Error message must reference the placeholder value"

    def test_nonzero_exit_after_placeholder_check(
        self, entrypoint_text: str
    ) -> None:
        assert re.search(
            r'placeholder_vars.*\n(?:.*\n){0,10}?\s*exit\s+1',
            entrypoint_text,
        ), "Entrypoint must exit 1 when placeholder values are detected"


class TestEntrypointPostSubstitutionGuard:
    """Post-envsubst: grep output files for placeholder/unsubstituted refs."""

    def test_greps_processed_config_for_placeholder(
        self, entrypoint_text: str
    ) -> None:
        # Must grep at least one processed file for the placeholder value
        assert re.search(
            r'grep\s+-q\s+"\\"\$\{?PLACEHOLDER_VALUE\}?\\""',
            entrypoint_text,
        ), (
            "Entrypoint must grep processed config for the placeholder "
            "value after envsubst"
        )

    def test_greps_for_unsubstituted_variable_references(
        self, entrypoint_text: str
    ) -> None:
        assert re.search(
            r'grep\s+-qE\s+["\']\\\$\\\{\[A-Z_\]',
            entrypoint_text,
        ), (
            "Entrypoint must grep processed config for unsubstituted ${VAR} "
            "references"
        )

    def test_iterates_output_directory(self, entrypoint_text: str) -> None:
        assert re.search(
            r'for\s+\w+\s+in\s+"\$\{OUTPUT_DIR\}"',
            entrypoint_text,
        ), "Entrypoint must iterate over files in the processed OUTPUT_DIR"

    def test_greps_for_empty_password_value(
        self, entrypoint_text: str
    ) -> None:
        # Guard against envsubst silently substituting a missing env var
        # with an empty string and producing password: "".
        assert re.search(
            r'grep\s+-qE\s+[\'"]password\[?\[:space:\]?\]?\*:',
            entrypoint_text,
        ), (
            'Entrypoint must grep processed config for empty password '
            'values (password: "")'
        )


class TestEntrypointIdempotent:
    """Template processing must re-run on every container start."""

    def test_envsubst_runs_in_main_script_body(self, entrypoint_text: str) -> None:
        # The envsubst loop must appear unconditionally in the main script
        # body (no `if first-run` guard), so it re-executes on every restart.
        assert re.search(
            r"envsubst\s+'[^']*'\s*<\s*\"\$template\"", entrypoint_text
        ), (
            "Entrypoint must re-run envsubst (allow-listed vars, redirected from "
            '"$template") on every start for idempotence'
        )
        # Must NOT short-circuit on an existing processed file
        assert not re.search(
            r'if\s+\[\s+-f\s+"\$\{?output\}?"\s+\]\s*;\s*then\s*continue',
            entrypoint_text,
        ), (
            "Entrypoint must not skip processing if the output file already "
            "exists — this would break idempotence on .env edits"
        )


# --- Behavioural tests: actually run the script -----------------------------


@pytest.fixture
def entrypoint_sandbox(tmp_path: Path) -> dict:
    """Prepare a sandbox that makes the entrypoint runnable without Docker.

    Creates a fake /etc/nats layout under tmp_path, seeds a minimal template,
    and produces a nats-server shim that simply echoes its args (so exec at
    the end of the script succeeds).
    """
    config_root = tmp_path / "nats"
    template_dir = config_root / "config" / "accounts"
    template_dir.mkdir(parents=True)

    template = template_dir / "accounts.conf.template"
    template.write_text(
        'accounts {\n'
        '    APPMILLA { users: [ { user: "rich", password: "${RICH_NATS_PASSWORD}" } ] }\n'
        '    APPMILLA2 { users: [ { user: "james", password: "${JAMES_NATS_PASSWORD}" } ] }\n'
        '    FINPROXY { users: [ { user: "mark", password: "${MARK_NATS_PASSWORD}" } ] }\n'
        '    SYS { users: [ { user: "admin", password: "${ADMIN_NATS_PASSWORD}" } ] }\n'
        '}\n',
        encoding="utf-8",
    )

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    # Shim nats-server so `exec nats-server "$@"` succeeds instead of ENOENT.
    nats_shim = bin_dir / "nats-server"
    nats_shim.write_text('#!/bin/sh\necho "nats-server launched with: $*"\n', encoding="utf-8")
    nats_shim.chmod(0o755)

    # Log directory is created under /var/log/nats by the script. Sandbox
    # that via a writable target the script can mkdir.
    log_home = tmp_path / "var_log"
    log_home.mkdir()

    return {
        "config_root": config_root,
        "template_dir": template_dir,
        "bin_dir": bin_dir,
        "tmp_path": tmp_path,
    }


def _run_entrypoint(
    sandbox: dict,
    env: dict | None = None,
) -> subprocess.CompletedProcess:
    """Run the entrypoint with NATS_CONFIG_DIR redirected to the sandbox."""
    log_dir = sandbox["tmp_path"] / "log_nats"
    # Inherit the caller's PATH so envsubst (installed via gettext on macOS
    # or already on PATH in CI containers) is discoverable, then prepend
    # the sandbox bin dir so our nats-server shim takes precedence.
    inherited_path = os.environ.get("PATH", "/usr/bin:/bin:/usr/sbin:/sbin")
    full_env = {
        "PATH": f"{sandbox['bin_dir']}:{inherited_path}",
        "NATS_CONFIG_DIR": str(sandbox["config_root"]),
        "NATS_LOG_DIR": str(log_dir),
    }
    if env:
        full_env.update(env)

    return subprocess.run(
        ["/bin/sh", str(ENTRYPOINT_FILE)],
        env=full_env,
        capture_output=True,
        text=True,
        timeout=10,
    )


def _has_envsubst() -> bool:
    return shutil.which("envsubst") is not None


requires_envsubst = pytest.mark.skipif(
    not _has_envsubst(),
    reason="envsubst not available on this host",
)


class TestEntrypointBehaviourMissingVars:
    """The script must exit 1 and print a clear message for missing vars."""

    def test_exits_when_all_vars_missing(self, entrypoint_sandbox: dict) -> None:
        result = _run_entrypoint(entrypoint_sandbox, env={})
        assert result.returncode != 0
        assert "Missing or empty required environment variables" in result.stderr
        for var in REQUIRED_VARS:
            assert var in result.stderr, f"stderr must mention {var}"

    def test_exits_when_one_var_missing(self, entrypoint_sandbox: dict) -> None:
        env = {
            "RICH_NATS_PASSWORD": "real-rich-password-001",
            "JAMES_NATS_PASSWORD": "real-james-password-002",
            "MARK_NATS_PASSWORD": "real-mark-password-003",
            # ADMIN_NATS_PASSWORD intentionally absent
        }
        result = _run_entrypoint(entrypoint_sandbox, env=env)
        assert result.returncode != 0
        assert "ADMIN_NATS_PASSWORD" in result.stderr

    def test_exits_when_var_is_empty_string(self, entrypoint_sandbox: dict) -> None:
        env = {
            "RICH_NATS_PASSWORD": "",
            "JAMES_NATS_PASSWORD": "real-james-password-002",
            "MARK_NATS_PASSWORD": "real-mark-password-003",
            "ADMIN_NATS_PASSWORD": "real-admin-password-004",
        }
        result = _run_entrypoint(entrypoint_sandbox, env=env)
        assert result.returncode != 0
        assert "RICH_NATS_PASSWORD" in result.stderr


class TestEntrypointBehaviourPlaceholderRejected:
    """The script must exit 1 when any var is equal to ``changeme``."""

    @pytest.mark.parametrize("placeholder_var", REQUIRED_VARS)
    def test_exits_on_single_placeholder(
        self, entrypoint_sandbox: dict, placeholder_var: str
    ) -> None:
        env = {var: f"real-value-{var}" for var in REQUIRED_VARS}
        env[placeholder_var] = "changeme"
        result = _run_entrypoint(entrypoint_sandbox, env=env)
        assert result.returncode != 0, (
            f"Entrypoint should refuse to start when {placeholder_var}=changeme"
        )
        assert "Placeholder password 'changeme'" in result.stderr
        assert placeholder_var in result.stderr

    def test_exits_when_all_vars_are_placeholder(
        self, entrypoint_sandbox: dict
    ) -> None:
        env = {var: "changeme" for var in REQUIRED_VARS}
        result = _run_entrypoint(entrypoint_sandbox, env=env)
        assert result.returncode != 0
        for var in REQUIRED_VARS:
            assert var in result.stderr, (
                f"stderr should list {var} as a placeholder"
            )

    def test_message_is_actionable(self, entrypoint_sandbox: dict) -> None:
        env = {var: "changeme" for var in REQUIRED_VARS}
        result = _run_entrypoint(entrypoint_sandbox, env=env)
        # Mention .env so the operator knows where to fix the value
        assert ".env" in result.stderr


@requires_envsubst
class TestEntrypointBehaviourHappyPath:
    """With all real passwords, the entrypoint should succeed and invoke nats-server."""

    def test_processes_template_and_execs(
        self, entrypoint_sandbox: dict
    ) -> None:
        env = {var: f"strong-{var.lower()}-xyz" for var in REQUIRED_VARS}
        result = _run_entrypoint(entrypoint_sandbox, env=env)

        assert result.returncode == 0, (
            f"Expected success, got rc={result.returncode}\n"
            f"stdout={result.stdout}\nstderr={result.stderr}"
        )

        processed = (
            entrypoint_sandbox["config_root"] / "accounts" / "accounts.conf"
        )
        assert processed.exists(), "Processed config should have been written"
        text = processed.read_text(encoding="utf-8")

        # Every placeholder has been substituted
        assert "${" not in text, "No unsubstituted ${VAR} references expected"
        # No literal "changeme" leaked
        assert '"changeme"' not in text
        # Real values made it through
        for var in REQUIRED_VARS:
            assert f"strong-{var.lower()}-xyz" in text

        # nats-server shim was exec'd
        assert "nats-server launched with" in result.stdout

    def test_is_idempotent_across_runs(self, entrypoint_sandbox: dict) -> None:
        env_run1 = {var: "first-run-value-01" for var in REQUIRED_VARS}
        assert _run_entrypoint(entrypoint_sandbox, env=env_run1).returncode == 0

        env_run2 = {var: "second-run-value-02" for var in REQUIRED_VARS}
        assert _run_entrypoint(entrypoint_sandbox, env=env_run2).returncode == 0

        processed = (
            entrypoint_sandbox["config_root"] / "accounts" / "accounts.conf"
        )
        text = processed.read_text(encoding="utf-8")
        # Second run's values must have replaced the first run's values,
        # proving idempotent re-processing on restart.
        assert "second-run-value-02" in text
        assert "first-run-value-01" not in text


@requires_envsubst
class TestEntrypointBehaviourPostSubstitutionGuard:
    """The post-envsubst grep must fire when substitution leaves bad output."""

    def test_rejects_hardcoded_placeholder_in_template(
        self, entrypoint_sandbox: dict
    ) -> None:
        # Simulate the exact MacBook incident: the processed config somehow
        # ends up with the literal "changeme" by writing it directly into the
        # template (so envsubst has nothing to do for that user).
        template = entrypoint_sandbox["template_dir"] / "accounts.conf.template"
        template.write_text(
            'accounts {\n'
            '    APPMILLA { users: [ { user: "rich", password: "changeme" } ] }\n'
            '}\n',
            encoding="utf-8",
        )
        env = {var: "real-password-xyz-99" for var in REQUIRED_VARS}
        result = _run_entrypoint(entrypoint_sandbox, env=env)
        assert result.returncode != 0, (
            "Post-substitution guard must refuse to start when "
            "'changeme' survives in the processed config"
        )
        assert "Placeholder 'changeme' found in processed config" in result.stderr

    def test_rejects_empty_password_from_missing_var(
        self, entrypoint_sandbox: dict
    ) -> None:
        # envsubst silently substitutes an allow-listed-but-unset env var with
        # an empty string, producing password: "". The guard must treat that as
        # a failure — otherwise the server would start with an open account.
        # FORGE_NATS_PASSWORD is in the entrypoint's envsubst allow-list but is
        # intentionally NOT provided below, so it substitutes to "" (a var that
        # is NOT in the allow-list would instead survive as a literal ${VAR} and
        # trip the separate unsubstituted-reference guard).
        template = entrypoint_sandbox["template_dir"] / "accounts.conf.template"
        template.write_text(
            'accounts {\n'
            '    APPMILLA { users: [ { user: "forge", password: "${FORGE_NATS_PASSWORD}" } ] }\n'
            '}\n',
            encoding="utf-8",
        )
        env = {var: "real-password-abc-77" for var in REQUIRED_VARS}
        env.pop("FORGE_NATS_PASSWORD", None)

        result = _run_entrypoint(entrypoint_sandbox, env=env)
        assert result.returncode != 0, (
            "Entrypoint should refuse to start when a required template "
            "variable is missing (envsubst produces empty password)"
        )
        assert "Empty password value in processed config" in result.stderr


# --- .env.example documentation ---------------------------------------------


class TestEnvExampleWarnsAboutPlaceholder:
    """.env.example must warn that 'changeme' will be rejected."""

    def test_has_refusal_comment(self, env_example_text: str) -> None:
        assert re.search(
            r"(?i)refuse.*start.*changeme|changeme.*refuse.*start",
            env_example_text,
        ), ".env.example must document that 'changeme' causes startup refusal"

    def test_keeps_changeme_as_placeholder_value(
        self, env_example_text: str
    ) -> None:
        # The .env.example itself still ships with `changeme` values — the
        # warning is in the comments, not in the absence of the placeholder.
        for var in REQUIRED_VARS:
            assert re.search(
                rf"^{var}=changeme\s*$",
                env_example_text,
                re.MULTILINE,
            ), f"{var} in .env.example should still default to 'changeme'"


# --- verify-nats.sh regression check ----------------------------------------


class TestVerifyScriptChecksPlaceholderRejection:
    """verify-nats.sh must try rich:changeme and assert authentication fails."""

    def test_verify_script_probes_placeholder_credentials(
        self, verify_script_text: str
    ) -> None:
        # Must invoke nats pub with --password "changeme"
        assert re.search(
            r'--password\s+"changeme"',
            verify_script_text,
        ), (
            "verify-nats.sh must try authenticating with --password \"changeme\" "
            "to assert the placeholder is rejected"
        )

    def test_verify_script_reports_security_failure(
        self, verify_script_text: str
    ) -> None:
        assert re.search(
            r'SECURITY.*rich:changeme',
            verify_script_text,
        ), (
            "verify-nats.sh must clearly flag a SECURITY failure if "
            "'rich:changeme' authentication succeeds"
        )
