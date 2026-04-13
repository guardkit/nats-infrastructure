"""Tests for verify-nats.sh Check 5 — JetStream stream verification.

Validates TASK-JSTR-005 acceptance criteria:
- AC-002: verify-nats.sh lists all expected streams with [OK]/[MISSING] status
- AC-003: Stream verification is gated on nats CLI availability (graceful skip)
- AC-004: All modified files pass project-configured lint/format checks with zero errors

Tests verify the stream verification section of verify-nats.sh, including
the expected stream list, [OK]/[MISSING] output format, and nats CLI gating.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

# Paths relative to project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
VERIFY_SCRIPT = PROJECT_ROOT / "scripts" / "verify-nats.sh"
STREAM_DEFS_FILE = PROJECT_ROOT / "streams" / "stream-definitions.json"


@pytest.fixture
def verify_text() -> str:
    """Read the verify-nats.sh script content."""
    assert VERIFY_SCRIPT.exists(), f"Script not found at {VERIFY_SCRIPT}"
    return VERIFY_SCRIPT.read_text(encoding="utf-8")


@pytest.fixture
def stream_defs() -> dict:
    """Load stream-definitions.json."""
    assert STREAM_DEFS_FILE.exists()
    return json.loads(STREAM_DEFS_FILE.read_text(encoding="utf-8"))


@pytest.fixture
def expected_stream_names(stream_defs: dict) -> list[str]:
    """Return expected stream names from stream-definitions.json."""
    return [s["name"] for s in stream_defs["streams"]]


# --- AC-002: verify-nats.sh lists all expected streams with [OK]/[MISSING] status ---


class TestStreamVerificationSection:
    """AC-002: verify-nats.sh has a stream verification section."""

    def test_has_check_5_section(self, verify_text: str) -> None:
        """Script must have a Check 5 section for stream verification."""
        assert re.search(
            r"Check\s+5.*[Ss]tream", verify_text
        ), "verify-nats.sh must have a Check 5 section for stream verification"

    def test_has_jetstream_streams_header(self, verify_text: str) -> None:
        """Script must have a header for JetStream stream checks."""
        assert re.search(
            r"JetStream\s+[Ss]tream", verify_text
        ), "verify-nats.sh must have a JetStream Streams section header"


class TestStreamListOutput:
    """AC-002: Script lists all expected streams with [OK]/[MISSING] status."""

    def test_uses_ok_status_marker(self, verify_text: str) -> None:
        """Script must use [OK] status for found streams."""
        assert re.search(
            r"\[OK\]", verify_text
        ), "verify-nats.sh must output [OK] for found streams"

    def test_uses_missing_status_marker(self, verify_text: str) -> None:
        """Script must use [MISSING] status for missing streams."""
        assert re.search(
            r"\[MISSING\]", verify_text
        ), "verify-nats.sh must output [MISSING] for missing streams"

    def test_ok_and_missing_in_echo(self, verify_text: str) -> None:
        """[OK] and [MISSING] must appear in echo/printf output statements."""
        ok_in_output = re.search(r'echo.*\[OK\]', verify_text)
        missing_in_output = re.search(r'echo.*\[MISSING\]', verify_text)
        assert ok_in_output, "[OK] must appear in echo output"
        assert missing_in_output, "[MISSING] must appear in echo output"

    def test_ok_includes_stream_name(self, verify_text: str) -> None:
        """[OK] output must include the stream name."""
        assert re.search(
            r'\[OK\].*\$', verify_text
        ), "[OK] output must include stream name via variable"

    def test_missing_includes_stream_name(self, verify_text: str) -> None:
        """[MISSING] output must include the stream name."""
        assert re.search(
            r'\[MISSING\].*\$', verify_text
        ), "[MISSING] output must include stream name via variable"


class TestExpectedStreamsCoverage:
    """AC-002: All expected streams from stream-definitions.json are checked."""

    def test_lists_pipeline_stream(self, verify_text: str) -> None:
        """Script must check the PIPELINE stream."""
        assert "PIPELINE" in verify_text, "Must check PIPELINE stream"

    def test_lists_agents_stream(self, verify_text: str) -> None:
        """Script must check the AGENTS stream."""
        assert "AGENTS" in verify_text, "Must check AGENTS stream"

    def test_lists_jarvis_stream(self, verify_text: str) -> None:
        """Script must check the JARVIS stream."""
        assert "JARVIS" in verify_text, "Must check JARVIS stream"

    def test_lists_notifications_stream(self, verify_text: str) -> None:
        """Script must check the NOTIFICATIONS stream."""
        assert "NOTIFICATIONS" in verify_text, "Must check NOTIFICATIONS stream"

    def test_lists_system_stream(self, verify_text: str) -> None:
        """Script must check the SYSTEM stream."""
        assert "SYSTEM" in verify_text, "Must check SYSTEM stream"

    def test_lists_fleet_stream(self, verify_text: str) -> None:
        """Script must check the FLEET stream."""
        assert "FLEET" in verify_text, "Must check FLEET stream"

    def test_lists_finproxy_stream(self, verify_text: str) -> None:
        """Script must check the FINPROXY stream."""
        assert "FINPROXY" in verify_text, "Must check FINPROXY stream"

    def test_all_defined_streams_are_checked(
        self, verify_text: str, expected_stream_names: list[str]
    ) -> None:
        """Every stream in stream-definitions.json must be checked by verify-nats.sh."""
        # Extract the EXPECTED_STREAMS variable value from the script
        expected_match = re.search(
            r'EXPECTED_STREAMS="([^"]*)"', verify_text
        )
        assert expected_match, (
            "verify-nats.sh must define EXPECTED_STREAMS variable"
        )
        script_streams = expected_match.group(1).split()

        for name in expected_stream_names:
            assert name in script_streams, (
                f"Stream {name} from stream-definitions.json is not in EXPECTED_STREAMS"
            )

    def test_expected_streams_count_matches(
        self, verify_text: str, expected_stream_names: list[str]
    ) -> None:
        """Number of expected streams in script matches stream-definitions.json."""
        expected_match = re.search(
            r'EXPECTED_STREAMS="([^"]*)"', verify_text
        )
        assert expected_match
        script_streams = expected_match.group(1).split()
        assert len(script_streams) == len(expected_stream_names), (
            f"Expected {len(expected_stream_names)} streams, "
            f"script has {len(script_streams)}: {script_streams}"
        )


class TestStreamCheckMechanism:
    """Script uses nats stream info to check each stream."""

    def test_uses_nats_stream_info(self, verify_text: str) -> None:
        """Script must use 'nats stream info' to check stream existence."""
        assert re.search(
            r"nats\s+stream\s+info", verify_text
        ), "verify-nats.sh must use 'nats stream info' for stream checks"

    def test_iterates_over_expected_streams(self, verify_text: str) -> None:
        """Script must iterate over expected streams in a loop."""
        assert re.search(
            r"for\s+\w+\s+in\s+\$EXPECTED_STREAMS", verify_text
        ), "verify-nats.sh must iterate over EXPECTED_STREAMS in a for loop"

    def test_reports_stream_counts(self, verify_text: str) -> None:
        """Script must report stream ok/missing counts."""
        has_ok_count = re.search(r"streams_ok|ok_count|found", verify_text, re.IGNORECASE)
        has_missing_count = re.search(
            r"streams_missing|missing_count", verify_text, re.IGNORECASE
        )
        assert has_ok_count, "Script must track count of found streams"
        assert has_missing_count, "Script must track count of missing streams"


# --- AC-003: Stream verification gated on nats CLI availability ---


class TestNatsCliGating:
    """AC-003: Stream verification is gated on nats CLI availability."""

    def test_check_5_gated_on_nats_cli(self, verify_text: str) -> None:
        """Check 5 must be gated on nats CLI availability."""
        # Find Check 5 section and verify it has a nats CLI check
        check_5_match = re.search(
            r"Check\s+5.*?(has_command\s+nats|command\s+-v\s+nats)",
            verify_text,
            re.DOTALL,
        )
        assert check_5_match, (
            "Check 5 must be gated on nats CLI via 'has_command nats' or 'command -v nats'"
        )

    def test_graceful_skip_when_no_nats_cli(self, verify_text: str) -> None:
        """Script must show SKIP message when nats CLI is not available."""
        # Find the Check 5 section and verify there's a SKIP message
        check_5_start = verify_text.find("Check 5")
        assert check_5_start != -1, "Must have Check 5 section"
        check_5_text = verify_text[check_5_start:]

        assert re.search(
            r"\[SKIP\].*stream", check_5_text, re.IGNORECASE
        ), "Must show [SKIP] message for stream checks when nats CLI is missing"

    def test_skip_suggests_install(self, verify_text: str) -> None:
        """Skip message should suggest how to install nats CLI."""
        check_5_start = verify_text.find("Check 5")
        check_5_text = verify_text[check_5_start:]
        assert re.search(
            r"natscli|nats-io", check_5_text, re.IGNORECASE
        ), "Skip message should include nats CLI install reference"

    def test_no_hard_failure_without_nats_cli(self, verify_text: str) -> None:
        """Missing nats CLI must not cause the script to fail."""
        # The Check 5 block should not call fail_check when nats CLI is missing
        check_5_start = verify_text.find("Check 5")
        summary_start = verify_text.find("Summary", check_5_start)
        check_5_text = verify_text[check_5_start:summary_start]

        # In the else branch (nats not available), there should be no fail_check
        else_branch = re.search(
            r"else\s*\n\s*echo.*\[SKIP\]", check_5_text
        )
        assert else_branch, (
            "When nats CLI is missing, script must SKIP (not FAIL) stream checks"
        )


class TestStreamCheckDoesNotAffectExitCode:
    """Stream check is informational — does not affect overall exit code."""

    def test_stream_check_does_not_fail_check(self, verify_text: str) -> None:
        """Missing streams should not call fail_check (they're informational)."""
        check_5_start = verify_text.find("Check 5")
        summary_start = verify_text.find("Summary", check_5_start)
        check_5_text = verify_text[check_5_start:summary_start]

        # Check 5 should not call fail_check for missing streams
        fail_in_check5 = re.search(r"fail_check", check_5_text)
        assert fail_in_check5 is None, (
            "Check 5 should not call fail_check — missing streams are informational, "
            "not failures. Provisioning is a separate step."
        )


# --- AC-003: verify-nats.sh still passes existing tests ---


class TestExistingChecksSurvive:
    """Existing checks 1-4 must still be present and intact."""

    def test_check_1_health_still_present(self, verify_text: str) -> None:
        """Check 1: Health endpoint must still be present."""
        assert re.search(r"Check\s+1.*Health", verify_text)

    def test_check_2_jetstream_still_present(self, verify_text: str) -> None:
        """Check 2: JetStream status must still be present."""
        assert re.search(r"Check\s+2.*JetStream", verify_text)

    def test_check_3_server_info_still_present(self, verify_text: str) -> None:
        """Check 3: Server info must still be present."""
        assert re.search(r"Check\s+3.*Server", verify_text)

    def test_check_4_auth_still_present(self, verify_text: str) -> None:
        """Check 4: Account authentication must still be present."""
        assert re.search(r"Check\s+4.*Account|Check\s+4.*Auth", verify_text)

    def test_summary_still_present(self, verify_text: str) -> None:
        """Summary section must still be present."""
        assert re.search(r"Results:.*passed.*failed", verify_text)

    def test_check_5_after_check_4(self, verify_text: str) -> None:
        """Check 5 must come after Check 4."""
        check_4_pos = re.search(r"Check\s+4", verify_text)
        check_5_pos = re.search(r"Check\s+5", verify_text)
        assert check_4_pos is not None
        assert check_5_pos is not None
        assert check_4_pos.start() < check_5_pos.start(), (
            "Check 5 must appear after Check 4"
        )

    def test_check_5_before_summary(self, verify_text: str) -> None:
        """Check 5 must come before the Summary section."""
        check_5_pos = re.search(r"Check\s+5", verify_text)
        summary_pos = re.search(r"# Summary", verify_text)
        assert check_5_pos is not None
        assert summary_pos is not None
        assert check_5_pos.start() < summary_pos.start(), (
            "Check 5 must appear before Summary"
        )


class TestProvisionHintForMissingStreams:
    """Script suggests running provision-streams.sh when streams are missing."""

    def test_suggests_provision_script(self, verify_text: str) -> None:
        """Script should suggest running provision-streams.sh for missing streams."""
        check_5_start = verify_text.find("Check 5")
        check_5_text = verify_text[check_5_start:]
        assert re.search(
            r"provision-streams\.sh", check_5_text
        ), "Should suggest running provision-streams.sh when streams are missing"
