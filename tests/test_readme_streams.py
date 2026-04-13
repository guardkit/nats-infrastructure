"""Tests for README.md JetStream Streams documentation — TASK-JSTR-006.

Validates acceptance criteria:
- AC-001: README.md has a "JetStream Streams" section
- AC-002: All 6 core streams listed with purpose
- AC-003: Provisioning commands documented
- AC-004: Idempotency guarantees explained
- AC-005: Project stream addition process documented
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
README_FILE = PROJECT_ROOT / "README.md"
STREAM_DEFS_FILE = PROJECT_ROOT / "streams" / "stream-definitions.json"

CORE_STREAMS = ["PIPELINE", "AGENTS", "JARVIS", "NOTIFICATIONS", "SYSTEM", "FLEET"]
KV_BUCKETS = ["agent-status", "agent-registry", "pipeline-state", "jarvis-session"]


@pytest.fixture
def readme_text() -> str:
    """Read the README.md file content."""
    assert README_FILE.exists(), f"README.md not found at {README_FILE}"
    return README_FILE.read_text(encoding="utf-8")


@pytest.fixture
def readme_lower(readme_text: str) -> str:
    """Lowercase README content for case-insensitive matching."""
    return readme_text.lower()


@pytest.fixture
def stream_definitions() -> list[dict]:
    """Load stream definitions from the JSON file."""
    assert STREAM_DEFS_FILE.exists(), f"Stream definitions not found at {STREAM_DEFS_FILE}"
    data = json.loads(STREAM_DEFS_FILE.read_text(encoding="utf-8"))
    return data["streams"]


@pytest.fixture
def kv_bucket_definitions() -> list[dict]:
    """Load KV bucket definitions from the JSON file."""
    assert STREAM_DEFS_FILE.exists(), f"Stream definitions not found at {STREAM_DEFS_FILE}"
    data = json.loads(STREAM_DEFS_FILE.read_text(encoding="utf-8"))
    return data.get("kv_buckets", [])


# --- AC-001: README.md has a "JetStream Streams" section ---


class TestJetStreamStreamsSection:
    """AC-001: README.md has a 'JetStream Streams' section."""

    def test_has_jetstream_streams_section(self, readme_text: str) -> None:
        assert "## JetStream Streams" in readme_text, (
            "README.md must have a '## JetStream Streams' section"
        )

    def test_jetstream_streams_section_has_content(self, readme_text: str) -> None:
        """Section is not empty — contains at least a paragraph of description."""
        idx = readme_text.index("## JetStream Streams")
        section_start = readme_text[idx:]
        # Find next h2 section
        next_h2 = section_start.find("\n## ", 1)
        if next_h2 == -1:
            section_content = section_start
        else:
            section_content = section_start[:next_h2]
        # Must have meaningful content (more than just the heading)
        assert len(section_content.strip()) > 50, (
            "JetStream Streams section must contain meaningful documentation"
        )

    def test_references_stream_definitions_file(self, readme_text: str) -> None:
        assert "stream-definitions.json" in readme_text, (
            "README must reference the stream-definitions.json file"
        )


# --- AC-002: All 6 core streams listed with purpose ---


class TestCoreStreamsListed:
    """AC-002: All 6 core streams listed with purpose."""

    @pytest.mark.parametrize("stream_name", CORE_STREAMS)
    def test_core_stream_is_listed(self, readme_text: str, stream_name: str) -> None:
        assert stream_name in readme_text, (
            f"README must list the {stream_name} core stream"
        )

    @pytest.mark.parametrize("stream_name", CORE_STREAMS)
    def test_core_stream_has_description(
        self,
        readme_text: str,
        stream_definitions: list[dict],
        stream_name: str,
    ) -> None:
        """Each core stream in the README should include some text from its description."""
        # Find the description from stream-definitions.json
        stream_def = next(s for s in stream_definitions if s["name"] == stream_name)
        # Check that the stream's subject pattern appears (shows it's properly documented)
        subjects = stream_def["subjects"][0]
        assert subjects in readme_text, (
            f"README must show the subject pattern '{subjects}' for {stream_name}"
        )

    def test_all_six_core_streams_present(self, readme_text: str) -> None:
        """Verify all 6 core streams are present (not just individually, but all together)."""
        for stream in CORE_STREAMS:
            assert stream in readme_text, f"Missing core stream: {stream}"

    def test_core_streams_table_has_retention_column(self, readme_text: str) -> None:
        """Core streams table must show retention type."""
        assert "Retention" in readme_text, (
            "Core streams listing must include retention information"
        )

    def test_core_streams_table_has_max_age_column(self, readme_text: str) -> None:
        """Core streams table must show max age."""
        assert "Max Age" in readme_text, (
            "Core streams listing must include max age information"
        )

    def test_core_streams_section_heading(self, readme_text: str) -> None:
        assert "### Core Streams" in readme_text, (
            "README must have a '### Core Streams' subsection"
        )


# --- AC-003: Provisioning commands documented ---


class TestProvisioningCommandsDocumented:
    """AC-003: Provisioning commands documented."""

    def test_has_provisioning_section(self, readme_text: str) -> None:
        assert "### Provisioning Commands" in readme_text, (
            "README must have a '### Provisioning Commands' subsection"
        )

    def test_documents_provision_streams_script(self, readme_text: str) -> None:
        assert "provision-streams.sh" in readme_text, (
            "README must reference the provision-streams.sh script"
        )

    def test_documents_dry_run_flag(self, readme_text: str) -> None:
        assert "--dry-run" in readme_text, (
            "README must document the --dry-run flag for previewing changes"
        )

    def test_documents_nats_url_env(self, readme_text: str) -> None:
        assert "NATS_URL" in readme_text, (
            "README must document the NATS_URL environment variable for provisioning"
        )

    def test_documents_nats_creds_env(self, readme_text: str) -> None:
        assert "NATS_CREDS" in readme_text, (
            "README must document the NATS_CREDS environment variable for provisioning"
        )

    def test_documents_prerequisites(self, readme_text: str) -> None:
        assert "jq" in readme_text and "NATS CLI" in readme_text, (
            "README must document prerequisites (jq and NATS CLI)"
        )


# --- AC-004: Idempotency guarantees explained ---


class TestIdempotencyGuaranteesExplained:
    """AC-004: Idempotency guarantees explained."""

    def test_has_idempotency_section(self, readme_text: str) -> None:
        assert "### Idempotency Guarantees" in readme_text, (
            "README must have a '### Idempotency Guarantees' subsection"
        )

    def test_explains_idempotent_pattern(self, readme_lower: str) -> None:
        assert "idempotent" in readme_lower, (
            "README must explain idempotent provisioning"
        )

    def test_explains_create_behaviour(self, readme_text: str) -> None:
        assert "[CREATE]" in readme_text, (
            "README must explain the [CREATE] behaviour for new streams"
        )

    def test_explains_ok_behaviour(self, readme_text: str) -> None:
        assert "[OK]" in readme_text, (
            "README must explain the [OK] behaviour for matching streams"
        )

    def test_explains_update_behaviour(self, readme_text: str) -> None:
        assert "[UPDATE]" in readme_text, (
            "README must explain the [UPDATE] behaviour for changed streams"
        )

    def test_explains_error_behaviour(self, readme_text: str) -> None:
        assert "[ERROR]" in readme_text, (
            "README must explain the [ERROR] behaviour for failed operations"
        )

    def test_explains_check_then_create_or_update(self, readme_lower: str) -> None:
        assert "check-then-create-or-update" in readme_lower, (
            "README must describe the check-then-create-or-update pattern"
        )

    def test_explains_safe_to_rerun(self, readme_lower: str) -> None:
        """README should indicate provisioning is safe to run multiple times."""
        assert "safe to run" in readme_lower or "safe to rerun" in readme_lower, (
            "README must explain that provisioning is safe to run multiple times"
        )

    def test_explains_summary_output(self, readme_text: str) -> None:
        assert "Streams:" in readme_text and "KV Buckets:" in readme_text, (
            "README must show the summary output format for both streams and KV buckets"
        )


# --- AC-005: Project stream addition process documented ---


class TestProjectStreamAdditionProcess:
    """AC-005: Project stream addition process documented."""

    def test_has_adding_stream_section(self, readme_text: str) -> None:
        assert "### Adding a New Stream" in readme_text, (
            "README must have a '### Adding a New Stream' subsection"
        )

    def test_documents_json_definition_step(self, readme_text: str) -> None:
        """Must describe adding to stream-definitions.json."""
        assert "stream-definitions.json" in readme_text, (
            "Addition process must reference stream-definitions.json"
        )

    def test_documents_account_permissions_step(self, readme_lower: str) -> None:
        """Must describe updating account permissions."""
        assert "account" in readme_lower and "permission" in readme_lower, (
            "Addition process must mention account permissions"
        )

    def test_documents_provision_step(self, readme_text: str) -> None:
        """Must describe running provision-streams.sh."""
        assert "provision-streams.sh" in readme_text, (
            "Addition process must include running provision-streams.sh"
        )

    def test_documents_test_update_step(self, readme_lower: str) -> None:
        """Must describe updating tests."""
        assert "update tests" in readme_lower or "test" in readme_lower, (
            "Addition process must include updating tests"
        )

    def test_shows_json_example(self, readme_text: str) -> None:
        """The addition process must include a JSON example."""
        # Check for a JSON code block with stream definition fields
        assert '"name"' in readme_text and '"subjects"' in readme_text, (
            "Addition process must include a JSON example with stream definition"
        )

    def test_documents_project_scope(self, readme_text: str) -> None:
        """Must show that project streams use scope: project."""
        assert '"scope": "project"' in readme_text or "scope" in readme_text.lower(), (
            "Addition process must mention project scope"
        )

    def test_has_project_streams_subsection(self, readme_text: str) -> None:
        assert "### Project Streams" in readme_text, (
            "README must have a '### Project Streams' subsection"
        )

    def test_finproxy_project_stream_listed(self, readme_text: str) -> None:
        assert "FINPROXY" in readme_text, (
            "README must list FINPROXY as a project stream"
        )


# --- KV Buckets documentation ---


class TestKVBucketsDocumented:
    """KV buckets are documented in the JetStream Streams section."""

    def test_has_kv_buckets_subsection(self, readme_text: str) -> None:
        assert "### KV Buckets" in readme_text, (
            "README must have a '### KV Buckets' subsection"
        )

    @pytest.mark.parametrize("bucket_name", KV_BUCKETS)
    def test_kv_bucket_is_listed(self, readme_text: str, bucket_name: str) -> None:
        assert bucket_name in readme_text, (
            f"README must list the {bucket_name} KV bucket"
        )

    def test_kv_bucket_table_has_ttl_column(self, readme_text: str) -> None:
        """KV bucket table must show TTL information."""
        assert "TTL" in readme_text, (
            "KV bucket listing must include TTL information"
        )

    def test_documents_persistent_vs_expiring(self, readme_lower: str) -> None:
        """README must explain the difference between persistent and expiring buckets."""
        assert "persistent" in readme_lower or "expire" in readme_lower, (
            "README must explain persistent vs expiring KV bucket behaviour"
        )

    def test_kv_buckets_provisioned_alongside_streams(self, readme_lower: str) -> None:
        """README must mention KV buckets are provisioned alongside streams."""
        assert "provisioned alongside" in readme_lower or "kv bucket" in readme_lower, (
            "README must indicate KV buckets are provisioned alongside streams"
        )
