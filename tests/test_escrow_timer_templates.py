"""Tests for config/systemd/check-escrow-coverage.{service,timer}.template — the
DF-022 S3 escrow-coverage runner's systemd --user unit templates.

SPEC (binding): ai-transition
docs/ways-of-working/secrets-close-out-and-rotation-handoff.md §3-S3 + §4 "S3
coach". The templates are register tooling: they instantiate VERBATIM (no
envsubst) into ~/.config/systemd/user/ on GB10 and Node B, and every per-box
path rides a systemd %h specifier. Validated here:

- AC-001: both templates exist under config/systemd/ and parse as systemd INI
- AC-002: service is Type=oneshot running check-escrow-coverage.sh against the
          %h/.config/fleet-secrets root via %h specifiers (verbatim-portable)
- AC-003: minimal-PATH law — exactly one Environment= line, pinning
          PATH=/usr/bin:/bin, with ~/.local/bin deliberately absent
- AC-004: RED visibility — nothing masks the script's nonzero exit
          (no SuccessExitStatus / ExecStart=- prefix / Restart churn)
- AC-005: timer is OnCalendar=daily + Persistent=true, explicitly bound to the
          service, installable via timers.target; service itself has NO
          [Install] (timer-activated only)
- AC-006: refs-only hygiene — no credential material, no envsubst ${...}
          placeholders left to rot literally into an installed unit
"""

from __future__ import annotations

import configparser
import re
from pathlib import Path

import pytest

# Paths relative to project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SYSTEMD_DIR = PROJECT_ROOT / "config" / "systemd"
SERVICE_TEMPLATE = SYSTEMD_DIR / "check-escrow-coverage.service.template"
TIMER_TEMPLATE = SYSTEMD_DIR / "check-escrow-coverage.timer.template"


@pytest.fixture
def service_text() -> str:
    """Read the service template content."""
    assert SERVICE_TEMPLATE.exists(), f"Template not found at {SERVICE_TEMPLATE}"
    return SERVICE_TEMPLATE.read_text(encoding="utf-8")


@pytest.fixture
def timer_text() -> str:
    """Read the timer template content."""
    assert TIMER_TEMPLATE.exists(), f"Template not found at {TIMER_TEMPLATE}"
    return TIMER_TEMPLATE.read_text(encoding="utf-8")


def _parse_unit(text: str) -> configparser.ConfigParser:
    """Parse a systemd unit as INI (systemd units are INI-shaped; '#' comments).

    configparser is case-sensitive here (systemd keys are), and % must not be
    treated as interpolation syntax (systemd specifiers use it).
    """
    parser = configparser.ConfigParser(
        interpolation=None, delimiters=("=",), comment_prefixes=("#", ";")
    )
    parser.optionxform = str  # preserve key case, as systemd requires
    parser.read_string(text)
    return parser


# =============================================================================
# AC-001: existence + parseability
# =============================================================================


class TestTemplatesExist:
    """Both unit templates exist and parse as systemd-shaped INI."""

    def test_service_template_exists(self) -> None:
        assert SERVICE_TEMPLATE.exists(), f"Expected {SERVICE_TEMPLATE}"

    def test_timer_template_exists(self) -> None:
        assert TIMER_TEMPLATE.exists(), f"Expected {TIMER_TEMPLATE}"

    def test_service_parses_as_ini(self, service_text: str) -> None:
        unit = _parse_unit(service_text)
        assert unit.has_section("Unit"), "service must carry a [Unit] section"
        assert unit.has_section("Service"), "service must carry a [Service] section"

    def test_timer_parses_as_ini(self, timer_text: str) -> None:
        unit = _parse_unit(timer_text)
        assert unit.has_section("Unit"), "timer must carry a [Unit] section"
        assert unit.has_section("Timer"), "timer must carry a [Timer] section"
        assert unit.has_section("Install"), "timer must carry an [Install] section"

    def test_basenames_pair_service_with_timer(self) -> None:
        """Stripping .template yields a same-stem service/timer unit pair."""
        service_name = SERVICE_TEMPLATE.name.removesuffix(".template")
        timer_name = TIMER_TEMPLATE.name.removesuffix(".template")
        assert service_name.endswith(".service")
        assert timer_name.endswith(".timer")
        assert service_name.removesuffix(".service") == timer_name.removesuffix(
            ".timer"
        ), "service and timer templates must share a unit stem"


# =============================================================================
# AC-002: oneshot service shape, %h-portable
# =============================================================================


class TestServiceShape:
    """The service runs the coverage check as a oneshot, portable via %h."""

    def test_type_is_oneshot(self, service_text: str) -> None:
        unit = _parse_unit(service_text)
        assert unit.get("Service", "Type") == "oneshot"

    def test_execstart_runs_the_register_check_script(self, service_text: str) -> None:
        unit = _parse_unit(service_text)
        exec_start = unit.get("Service", "ExecStart")
        assert exec_start.startswith("%h/.local/bin/check-escrow-coverage.sh"), (
            "ExecStart must run the installed register check script via the %h "
            f"specifier, got: {exec_start}"
        )

    def test_execstart_states_the_secrets_root_explicitly(
        self, service_text: str
    ) -> None:
        unit = _parse_unit(service_text)
        exec_start = unit.get("Service", "ExecStart")
        argv = exec_start.split()
        assert argv[1:] == ["%h/.config/fleet-secrets"], (
            "ExecStart must pass the %h/.config/fleet-secrets root as the sole "
            f"argument (deterministic under the minimal environment), got: {argv[1:]}"
        )

    def test_per_box_paths_ride_specifiers_not_literals(
        self, service_text: str
    ) -> None:
        """No literal /home/... path: %h carries GB10 and Node B alike."""
        unit = _parse_unit(service_text)
        for key in ("ExecStart",):
            value = unit.get("Service", key)
            assert "/home/" not in value, (
                f"{key} must not hardcode a home directory (use %h): {value}"
            )

    def test_syslog_identifier_is_stable(self, service_text: str) -> None:
        unit = _parse_unit(service_text)
        assert unit.get("Service", "SyslogIdentifier") == "check-escrow-coverage"


# =============================================================================
# AC-003: minimal-PATH law
# =============================================================================


class TestMinimalPathLaw:
    """PATH is pinned minimal; ~/.local/bin deliberately absent (spec §3-S3)."""

    def test_exactly_one_environment_line(self, service_text: str) -> None:
        env_lines = [
            line
            for line in service_text.splitlines()
            if re.match(r"^\s*Environment\s*=", line)
        ]
        assert len(env_lines) == 1, (
            "the unit carries exactly ONE Environment= line (the pinned PATH); "
            f"found {len(env_lines)}: {env_lines}"
        )

    def test_path_pinned_to_usr_bin_bin(self, service_text: str) -> None:
        unit = _parse_unit(service_text)
        assert unit.get("Service", "Environment") == "PATH=/usr/bin:/bin"

    def test_local_bin_not_on_path(self, service_text: str) -> None:
        """Anything outside /usr/bin:/bin (sops, notably) needs an absolute path."""
        unit = _parse_unit(service_text)
        assert ".local/bin" not in unit.get("Service", "Environment")


# =============================================================================
# AC-004: RED visibility — the nonzero exit is the alarm, unmasked
# =============================================================================


class TestRedVisibility:
    """A coverage RED (exit 1) / root error (exit 2) must fail the unit."""

    def test_execstart_does_not_ignore_failure(self, service_text: str) -> None:
        unit = _parse_unit(service_text)
        exec_start = unit.get("Service", "ExecStart")
        assert not exec_start.startswith("-"), (
            "ExecStart=- would mask the check's nonzero exit (the RED alarm)"
        )

    def test_no_success_exit_status_laundering(self, service_text: str) -> None:
        unit = _parse_unit(service_text)
        assert not unit.has_option("Service", "SuccessExitStatus"), (
            "SuccessExitStatus would launder the RED/usage exits into green"
        )

    def test_no_restart_churn(self, service_text: str) -> None:
        """A oneshot check must not auto-restart (journal spam, alarm churn)."""
        unit = _parse_unit(service_text)
        assert not unit.has_option("Service", "Restart")


# =============================================================================
# AC-005: timer shape — daily, persistent, timer-activated only
# =============================================================================


class TestTimerShape:
    """Daily persistent timer, explicitly bound, enabled via timers.target."""

    def test_oncalendar_daily(self, timer_text: str) -> None:
        unit = _parse_unit(timer_text)
        assert unit.get("Timer", "OnCalendar") == "daily"

    def test_persistent_catch_up(self, timer_text: str) -> None:
        unit = _parse_unit(timer_text)
        assert unit.get("Timer", "Persistent") == "true"

    def test_timer_binds_the_service_explicitly(self, timer_text: str) -> None:
        unit = _parse_unit(timer_text)
        assert unit.get("Timer", "Unit") == "check-escrow-coverage.service"

    def test_install_wanted_by_timers_target(self, timer_text: str) -> None:
        unit = _parse_unit(timer_text)
        assert unit.get("Install", "WantedBy") == "timers.target"

    def test_service_has_no_install_section(self, service_text: str) -> None:
        """The service is timer-activated only — enabling it directly must fail."""
        unit = _parse_unit(service_text)
        assert not unit.has_section("Install")


# =============================================================================
# AC-006: refs-only hygiene — no credentials, no stray envsubst placeholders
# =============================================================================


class TestRefsOnlyHygiene:
    """Register tooling stays refs-only; instantiation is a verbatim copy."""

    @pytest.mark.parametrize(
        "template", [SERVICE_TEMPLATE, TIMER_TEMPLATE], ids=["service", "timer"]
    )
    def test_no_envsubst_placeholders(self, template: Path) -> None:
        """A ${VAR} would land LITERALLY in the installed unit (no envsubst step)."""
        text = template.read_text(encoding="utf-8")
        assert "${" not in text, (
            f"{template.name} carries an envsubst-style placeholder, but S3 "
            "instantiation is a verbatim copy — per-box variance rides %h"
        )

    @pytest.mark.parametrize(
        "template", [SERVICE_TEMPLATE, TIMER_TEMPLATE], ids=["service", "timer"]
    )
    def test_no_credential_material(self, template: Path) -> None:
        text = template.read_text(encoding="utf-8")
        for needle in ("PASSWORD", "AGE-SECRET-KEY", "_TOKEN", "SOPS_AGE_KEY"):
            assert needle not in text, (
                f"{template.name} must never carry credential-shaped content "
                f"(found {needle!r})"
            )
