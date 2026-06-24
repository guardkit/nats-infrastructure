"""Tests for streams/stream-definitions.json — validates JetStream stream definitions.

Verifies all acceptance criteria for TASK-JSTR-001:
- AC-001: File created at streams/stream-definitions.json
- AC-002: All 6 core streams defined with exact spec values
- AC-003: FINPROXY project stream included with scope=project and reasonable defaults (24h, 5000)
- AC-004: All required fields present: name, subjects, retention, max_age, max_msgs, storage, replicas
- AC-005: JSON is valid (parseable)
- AC-006: Retention values use NATS CLI format: work (WorkQueue) or limits (Limits)

Also verifies TASK-JSTR-003 KV bucket definitions:
- AC-001: All 4 KV buckets defined in stream-definitions.json
- AC-003: TTL values applied correctly (null = no TTL, persistent)
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

# Path to the stream definitions file relative to the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
STREAM_DEFS_FILE = PROJECT_ROOT / "streams" / "stream-definitions.json"

# Required fields for each stream definition
REQUIRED_FIELDS = {
    "name",
    "subjects",
    "retention",
    "max_age",
    "max_msgs",
    "storage",
    "replicas",
}

# Valid retention values in NATS CLI format
VALID_RETENTION_VALUES = {"work", "limits"}

# Required fields for each KV bucket definition
KV_REQUIRED_FIELDS = {"name", "ttl", "description"}

# Expected KV buckets from the system spec (Feature 6)
EXPECTED_KV_BUCKETS = {
    "agent-status": {
        "ttl": None,
        "description_contains": "status",
    },
    "agent-registry": {
        "ttl": None,
        "description_contains": "routing",
    },
    "pipeline-state": {
        "ttl": "7d",
        "description_contains": "pipeline",
    },
    "jarvis-session": {
        "ttl": "1h",
        "description_contains": "session",
    },
}

# Valid NATS duration pattern for TTL values
NATS_DURATION_PATTERN = re.compile(r"^\d+[smhd]$")

# Expected core streams from the system spec (Feature 3)
EXPECTED_CORE_STREAMS = {
    "PIPELINE": {
        "subjects": ["pipeline.>"],
        "retention": "work",
        "max_age": "7d",
        "max_msgs": 10000,
        "storage": "file",
        "replicas": 1,
    },
    "AGENTS": {
        "subjects": ["agents.>"],
        "retention": "limits",
        "max_age": "24h",
        "max_msgs": 5000,
        "storage": "file",
        "replicas": 1,
    },
    "JARVIS": {
        "subjects": ["jarvis.>"],
        "retention": "limits",
        "max_age": "1h",
        "max_msgs": 1000,
        "storage": "file",
        "replicas": 1,
    },
    "NOTIFICATIONS": {
        "subjects": ["notifications.>"],
        "retention": "work",
        "max_age": "24h",
        "max_msgs": 1000,
        "storage": "file",
        "replicas": 1,
    },
    "SYSTEM": {
        "subjects": ["system.>"],
        "retention": "limits",
        "max_age": "1h",
        "max_msgs": 500,
        "storage": "file",
        "replicas": 1,
    },
    "FLEET": {
        "subjects": ["fleet.>"],
        "retention": "limits",
        "max_age": "1h",
        "max_msgs": 5000,
        "storage": "file",
        "replicas": 1,
    },
}


@pytest.fixture
def stream_defs_text() -> str:
    """Read the stream-definitions.json file content."""
    assert STREAM_DEFS_FILE.exists(), (
        f"stream-definitions.json not found at {STREAM_DEFS_FILE}"
    )
    return STREAM_DEFS_FILE.read_text(encoding="utf-8")


@pytest.fixture
def stream_defs(stream_defs_text: str) -> dict:
    """Parse stream-definitions.json as JSON."""
    data = json.loads(stream_defs_text)
    assert isinstance(data, dict), "stream-definitions.json must be a valid JSON object"
    return data


@pytest.fixture
def streams_list(stream_defs: dict) -> list[dict]:
    """Extract the streams array from the definitions."""
    assert "streams" in stream_defs, "stream-definitions.json must have a 'streams' key"
    streams = stream_defs["streams"]
    assert isinstance(streams, list), "'streams' must be a JSON array"
    return streams


@pytest.fixture
def streams_by_name(streams_list: list[dict]) -> dict[str, dict]:
    """Index streams by name for easy lookup."""
    return {s["name"]: s for s in streams_list}


# --- AC-001: File created at streams/stream-definitions.json ---


class TestStreamDefsFileExists:
    """AC-001: File created at streams/stream-definitions.json."""

    def test_file_exists(self) -> None:
        assert STREAM_DEFS_FILE.exists(), (
            f"Expected stream-definitions.json at {STREAM_DEFS_FILE}"
        )

    def test_file_is_not_empty(self, stream_defs_text: str) -> None:
        assert len(stream_defs_text.strip()) > 0, (
            "stream-definitions.json must not be empty"
        )

    def test_file_in_streams_directory(self) -> None:
        streams_dir = PROJECT_ROOT / "streams"
        assert streams_dir.is_dir(), f"Expected 'streams' directory at {streams_dir}"


# --- AC-005: JSON is valid (parseable) ---


class TestJsonValidity:
    """AC-005: JSON is valid (parseable by jq / json.loads)."""

    def test_json_is_parseable(self, stream_defs_text: str) -> None:
        try:
            data = json.loads(stream_defs_text)
        except json.JSONDecodeError as e:
            pytest.fail(f"stream-definitions.json is not valid JSON: {e}")
        assert isinstance(data, dict), "Top-level must be a JSON object"

    def test_has_streams_key(self, stream_defs: dict) -> None:
        assert "streams" in stream_defs, (
            "stream-definitions.json must have a top-level 'streams' key"
        )

    def test_streams_is_array(self, stream_defs: dict) -> None:
        assert isinstance(stream_defs["streams"], list), "'streams' must be an array"


# --- AC-004: All required fields present ---


class TestRequiredFields:
    """AC-004: All required fields present: name, subjects, retention, max_age, max_msgs, storage, replicas."""

    def test_all_streams_have_required_fields(self, streams_list: list[dict]) -> None:
        for stream in streams_list:
            stream_name = stream.get("name", "<unnamed>")
            missing = REQUIRED_FIELDS - set(stream.keys())
            assert not missing, (
                f"Stream '{stream_name}' is missing required fields: {missing}"
            )

    def test_subjects_is_list_of_strings(self, streams_list: list[dict]) -> None:
        for stream in streams_list:
            name = stream.get("name", "<unnamed>")
            subjects = stream.get("subjects", [])
            assert isinstance(subjects, list), (
                f"Stream '{name}': subjects must be an array"
            )
            for subj in subjects:
                assert isinstance(subj, str), (
                    f"Stream '{name}': each subject must be a string, got {type(subj)}"
                )

    def test_max_msgs_is_integer(self, streams_list: list[dict]) -> None:
        for stream in streams_list:
            name = stream.get("name", "<unnamed>")
            assert isinstance(stream.get("max_msgs"), int), (
                f"Stream '{name}': max_msgs must be an integer"
            )

    def test_replicas_is_integer(self, streams_list: list[dict]) -> None:
        for stream in streams_list:
            name = stream.get("name", "<unnamed>")
            assert isinstance(stream.get("replicas"), int), (
                f"Stream '{name}': replicas must be an integer"
            )

    def test_max_age_is_string(self, streams_list: list[dict]) -> None:
        for stream in streams_list:
            name = stream.get("name", "<unnamed>")
            assert isinstance(stream.get("max_age"), str), (
                f"Stream '{name}': max_age must be a string (NATS duration format)"
            )

    def test_storage_is_string(self, streams_list: list[dict]) -> None:
        for stream in streams_list:
            name = stream.get("name", "<unnamed>")
            assert isinstance(stream.get("storage"), str), (
                f"Stream '{name}': storage must be a string"
            )


# --- AC-006: Retention values use NATS CLI format ---


class TestRetentionValues:
    """AC-006: Retention values use NATS CLI format: work (WorkQueue) or limits (Limits)."""

    def test_all_retentions_are_valid(self, streams_list: list[dict]) -> None:
        for stream in streams_list:
            name = stream.get("name", "<unnamed>")
            retention = stream.get("retention")
            assert retention in VALID_RETENTION_VALUES, (
                f"Stream '{name}': retention must be one of {VALID_RETENTION_VALUES}, got '{retention}'"
            )


# --- AC-002: All 6 core streams defined with exact spec values ---


class TestCoreStreams:
    """AC-002: All 6 core streams defined with exact spec values."""

    def test_all_six_core_streams_present(
        self, streams_by_name: dict[str, dict]
    ) -> None:
        for stream_name in EXPECTED_CORE_STREAMS:
            assert stream_name in streams_by_name, (
                f"Core stream '{stream_name}' not found in definitions"
            )

    def test_core_streams_have_core_scope(
        self, streams_by_name: dict[str, dict]
    ) -> None:
        for stream_name in EXPECTED_CORE_STREAMS:
            stream = streams_by_name[stream_name]
            assert stream.get("scope") == "core", (
                f"Core stream '{stream_name}' must have scope='core', got '{stream.get('scope')}'"
            )

    @pytest.mark.parametrize("stream_name", list(EXPECTED_CORE_STREAMS.keys()))
    def test_core_stream_subjects(
        self, streams_by_name: dict[str, dict], stream_name: str
    ) -> None:
        expected = EXPECTED_CORE_STREAMS[stream_name]
        actual = streams_by_name[stream_name]
        assert actual["subjects"] == expected["subjects"], (
            f"Stream '{stream_name}': subjects mismatch — "
            f"expected {expected['subjects']}, got {actual['subjects']}"
        )

    @pytest.mark.parametrize("stream_name", list(EXPECTED_CORE_STREAMS.keys()))
    def test_core_stream_retention(
        self, streams_by_name: dict[str, dict], stream_name: str
    ) -> None:
        expected = EXPECTED_CORE_STREAMS[stream_name]
        actual = streams_by_name[stream_name]
        assert actual["retention"] == expected["retention"], (
            f"Stream '{stream_name}': retention mismatch — "
            f"expected '{expected['retention']}', got '{actual['retention']}'"
        )

    @pytest.mark.parametrize("stream_name", list(EXPECTED_CORE_STREAMS.keys()))
    def test_core_stream_max_age(
        self, streams_by_name: dict[str, dict], stream_name: str
    ) -> None:
        expected = EXPECTED_CORE_STREAMS[stream_name]
        actual = streams_by_name[stream_name]
        assert actual["max_age"] == expected["max_age"], (
            f"Stream '{stream_name}': max_age mismatch — "
            f"expected '{expected['max_age']}', got '{actual['max_age']}'"
        )

    @pytest.mark.parametrize("stream_name", list(EXPECTED_CORE_STREAMS.keys()))
    def test_core_stream_max_msgs(
        self, streams_by_name: dict[str, dict], stream_name: str
    ) -> None:
        expected = EXPECTED_CORE_STREAMS[stream_name]
        actual = streams_by_name[stream_name]
        assert actual["max_msgs"] == expected["max_msgs"], (
            f"Stream '{stream_name}': max_msgs mismatch — "
            f"expected {expected['max_msgs']}, got {actual['max_msgs']}"
        )

    @pytest.mark.parametrize("stream_name", list(EXPECTED_CORE_STREAMS.keys()))
    def test_core_stream_storage(
        self, streams_by_name: dict[str, dict], stream_name: str
    ) -> None:
        expected = EXPECTED_CORE_STREAMS[stream_name]
        actual = streams_by_name[stream_name]
        assert actual["storage"] == expected["storage"], (
            f"Stream '{stream_name}': storage mismatch — "
            f"expected '{expected['storage']}', got '{actual['storage']}'"
        )

    @pytest.mark.parametrize("stream_name", list(EXPECTED_CORE_STREAMS.keys()))
    def test_core_stream_replicas(
        self, streams_by_name: dict[str, dict], stream_name: str
    ) -> None:
        expected = EXPECTED_CORE_STREAMS[stream_name]
        actual = streams_by_name[stream_name]
        assert actual["replicas"] == expected["replicas"], (
            f"Stream '{stream_name}': replicas mismatch — "
            f"expected {expected['replicas']}, got {actual['replicas']}"
        )


# --- AC-003: FINPROXY project stream included ---


class TestFinproxyStream:
    """AC-003: FINPROXY project stream included with scope=project and reasonable defaults (24h, 5000)."""

    def test_finproxy_stream_exists(self, streams_by_name: dict[str, dict]) -> None:
        assert "FINPROXY" in streams_by_name, "FINPROXY stream not found in definitions"

    def test_finproxy_scope_is_project(self, streams_by_name: dict[str, dict]) -> None:
        finproxy = streams_by_name["FINPROXY"]
        assert finproxy.get("scope") == "project", (
            f"FINPROXY scope must be 'project', got '{finproxy.get('scope')}'"
        )

    def test_finproxy_subjects(self, streams_by_name: dict[str, dict]) -> None:
        finproxy = streams_by_name["FINPROXY"]
        assert finproxy["subjects"] == ["finproxy.>"], (
            f"FINPROXY subjects must be ['finproxy.>'], got {finproxy['subjects']}"
        )

    def test_finproxy_retention_is_work(self, streams_by_name: dict[str, dict]) -> None:
        finproxy = streams_by_name["FINPROXY"]
        assert finproxy["retention"] == "work", (
            f"FINPROXY retention must be 'work' (WorkQueue), got '{finproxy['retention']}'"
        )

    def test_finproxy_max_age_is_24h(self, streams_by_name: dict[str, dict]) -> None:
        finproxy = streams_by_name["FINPROXY"]
        assert finproxy["max_age"] == "24h", (
            f"FINPROXY max_age must be '24h', got '{finproxy['max_age']}'"
        )

    def test_finproxy_max_msgs_is_5000(self, streams_by_name: dict[str, dict]) -> None:
        finproxy = streams_by_name["FINPROXY"]
        assert finproxy["max_msgs"] == 5000, (
            f"FINPROXY max_msgs must be 5000, got {finproxy['max_msgs']}"
        )

    def test_finproxy_storage_is_file(self, streams_by_name: dict[str, dict]) -> None:
        finproxy = streams_by_name["FINPROXY"]
        assert finproxy["storage"] == "file", (
            f"FINPROXY storage must be 'file', got '{finproxy['storage']}'"
        )

    def test_finproxy_replicas_is_1(self, streams_by_name: dict[str, dict]) -> None:
        finproxy = streams_by_name["FINPROXY"]
        assert finproxy["replicas"] == 1, (
            f"FINPROXY replicas must be 1, got {finproxy['replicas']}"
        )


# --- MEMORY stream (FEAT-MEM-04 relay write path) ---


class TestMemoryStream:
    """MEMORY stream backs the fleet-memory relay (FEAT-MEM-04).

    Contract (docs/decisions/MEM-04-relay-jetstream-contract.md in fleet-memory):
    a single core stream over memory.> carries both the ingest subject
    (memory.episode) and the DLQ subject (memory.dlq); limits retention so acked
    episodes and parked poison age out rather than being deleted on ack.
    """

    def test_memory_stream_exists(self, streams_by_name: dict[str, dict]) -> None:
        assert "MEMORY" in streams_by_name, "MEMORY stream not found in definitions"

    def test_memory_subjects_are_partitioned_episode_and_dlq(
        self, streams_by_name: dict[str, dict]
    ) -> None:
        # Publisher (nats-core) sends memory.episode.{project_id}.{episode_type};
        # poison is parked per-project on memory.dlq.{project_id}. Both lowercase + .>.
        assert streams_by_name["MEMORY"]["subjects"] == ["memory.episode.>", "memory.dlq.>"], (
            "MEMORY subjects must be ['memory.episode.>', 'memory.dlq.>'], got "
            f"{streams_by_name['MEMORY']['subjects']}"
        )

    def test_memory_retention_is_limits(
        self, streams_by_name: dict[str, dict]
    ) -> None:
        # limits (not work): the relay consumer tracks position; poison on memory.dlq
        # must be retained for inspection, not deleted on ack.
        assert streams_by_name["MEMORY"]["retention"] == "limits", (
            f"MEMORY retention must be 'limits', got '{streams_by_name['MEMORY']['retention']}'"
        )

    def test_memory_scope_is_core(self, streams_by_name: dict[str, dict]) -> None:
        assert streams_by_name["MEMORY"].get("scope") == "core", (
            f"MEMORY scope must be 'core', got '{streams_by_name['MEMORY'].get('scope')}'"
        )


# --- NATS duration format validation ---


class TestNatsDurationFormat:
    """Max age values must use valid NATS duration format (e.g., 7d, 24h, 1h)."""

    NATS_DURATION_PATTERN = re.compile(r"^\d+[smhd]$")

    def test_max_age_uses_valid_nats_duration(self, streams_list: list[dict]) -> None:
        for stream in streams_list:
            name = stream.get("name", "<unnamed>")
            max_age = stream.get("max_age", "")
            assert self.NATS_DURATION_PATTERN.match(max_age), (
                f"Stream '{name}': max_age '{max_age}' does not match NATS duration format "
                f"(expected pattern like '7d', '24h', '1h')"
            )

    @pytest.mark.parametrize(
        "stream_name,expected_max_age",
        [
            ("PIPELINE", "7d"),
            ("AGENTS", "24h"),
            ("JARVIS", "1h"),
            ("NOTIFICATIONS", "24h"),
            ("SYSTEM", "1h"),
            ("FLEET", "1h"),
            ("FINPROXY", "24h"),
        ],
    )
    def test_specific_stream_max_age_format(
        self,
        streams_by_name: dict[str, dict],
        stream_name: str,
        expected_max_age: str,
    ) -> None:
        stream = streams_by_name[stream_name]
        assert stream["max_age"] == expected_max_age, (
            f"Stream '{stream_name}': max_age must be '{expected_max_age}', got '{stream['max_age']}'"
        )


# --- Subject naming validation ---


class TestSubjectNaming:
    """All core subjects must follow dot-separated hierarchical naming."""

    DOT_SEPARATED_PATTERN = re.compile(r"^[a-z][a-z0-9]*(\.[a-z][a-z0-9]*)*(\.\>)?$")

    def test_subjects_follow_dot_separated_hierarchical_naming(
        self, streams_list: list[dict]
    ) -> None:
        for stream in streams_list:
            name = stream.get("name", "<unnamed>")
            for subject in stream.get("subjects", []):
                assert self.DOT_SEPARATED_PATTERN.match(subject), (
                    f"Stream '{name}': subject '{subject}' does not follow "
                    f"dot-separated hierarchical naming (e.g., 'pipeline.>')"
                )

    def test_subjects_use_wildcard_suffix(self, streams_list: list[dict]) -> None:
        for stream in streams_list:
            name = stream.get("name", "<unnamed>")
            for subject in stream.get("subjects", []):
                assert subject.endswith(".>"), (
                    f"Stream '{name}': subject '{subject}' should use '.>' wildcard suffix"
                )


# --- Spec compliance: explicit checks per task scope ---


class TestSpecCompliance:
    """Explicit spec compliance checks from the system specification."""

    def test_pipeline_retention_is_work(self, streams_by_name: dict[str, dict]) -> None:
        assert streams_by_name["PIPELINE"]["retention"] == "work", (
            "PIPELINE retention must be 'work' (WorkQueue) per spec"
        )

    def test_agents_max_age_is_24h(self, streams_by_name: dict[str, dict]) -> None:
        assert streams_by_name["AGENTS"]["max_age"] == "24h", (
            "AGENTS max_age must be '24h' per spec"
        )

    def test_jarvis_max_msgs_is_1000(self, streams_by_name: dict[str, dict]) -> None:
        assert streams_by_name["JARVIS"]["max_msgs"] == 1000, (
            "JARVIS max_msgs must be 1000 per spec"
        )

    def test_all_streams_replicas_is_1(self, streams_list: list[dict]) -> None:
        for stream in streams_list:
            name = stream.get("name", "<unnamed>")
            assert stream["replicas"] == 1, (
                f"Stream '{name}': replicas must be 1 (single server), got {stream['replicas']}"
            )

    def test_all_streams_storage_is_file(self, streams_list: list[dict]) -> None:
        for stream in streams_list:
            name = stream.get("name", "<unnamed>")
            assert stream["storage"] == "file", (
                f"Stream '{name}': storage must be 'file', got '{stream['storage']}'"
            )


# --- Additional validation: total stream count ---


class TestStreamCount:
    """Verify total number of streams matches spec (6 core + 1 project)."""

    def test_total_stream_count(self, streams_list: list[dict]) -> None:
        assert len(streams_list) == 8, (
            f"Expected 8 streams (6 base core + MEMORY + 1 project), got {len(streams_list)}"
        )

    def test_no_duplicate_stream_names(self, streams_list: list[dict]) -> None:
        names = [s["name"] for s in streams_list]
        assert len(names) == len(set(names)), f"Duplicate stream names found: {names}"

    def test_no_duplicate_subjects(self, streams_list: list[dict]) -> None:
        all_subjects = []
        for s in streams_list:
            all_subjects.extend(s["subjects"])
        assert len(all_subjects) == len(set(all_subjects)), (
            f"Duplicate subjects found: {all_subjects}"
        )


# =============================================================================
# TASK-JSTR-003: KV Bucket Definitions
# =============================================================================


@pytest.fixture
def kv_buckets_list(stream_defs: dict) -> list[dict]:
    """Extract the kv_buckets array from the definitions."""
    assert "kv_buckets" in stream_defs, (
        "stream-definitions.json must have a 'kv_buckets' key"
    )
    kv_buckets = stream_defs["kv_buckets"]
    assert isinstance(kv_buckets, list), "'kv_buckets' must be a JSON array"
    return kv_buckets


@pytest.fixture
def kv_buckets_by_name(kv_buckets_list: list[dict]) -> dict[str, dict]:
    """Index KV buckets by name for easy lookup."""
    return {b["name"]: b for b in kv_buckets_list}


# --- TASK-JSTR-003 AC-001: All 4 KV buckets defined ---


class TestKvBucketsExist:
    """TASK-JSTR-003 AC-001: All 4 KV buckets defined in stream-definitions.json."""

    def test_kv_buckets_key_exists(self, stream_defs: dict) -> None:
        assert "kv_buckets" in stream_defs, (
            "stream-definitions.json must have a top-level 'kv_buckets' key"
        )

    def test_kv_buckets_is_array(self, stream_defs: dict) -> None:
        assert isinstance(stream_defs["kv_buckets"], list), (
            "'kv_buckets' must be an array"
        )

    def test_exactly_4_kv_buckets(self, kv_buckets_list: list[dict]) -> None:
        assert len(kv_buckets_list) == 4, (
            f"Expected 4 KV buckets, got {len(kv_buckets_list)}"
        )

    def test_all_expected_buckets_present(
        self, kv_buckets_by_name: dict[str, dict]
    ) -> None:
        for bucket_name in EXPECTED_KV_BUCKETS:
            assert bucket_name in kv_buckets_by_name, (
                f"KV bucket '{bucket_name}' not found in definitions"
            )

    def test_no_duplicate_bucket_names(self, kv_buckets_list: list[dict]) -> None:
        names = [b["name"] for b in kv_buckets_list]
        assert len(names) == len(set(names)), (
            f"Duplicate KV bucket names found: {names}"
        )


# --- KV bucket required fields ---


class TestKvBucketRequiredFields:
    """All KV buckets must have required fields: name, ttl, description."""

    def test_all_buckets_have_required_fields(
        self, kv_buckets_list: list[dict]
    ) -> None:
        for bucket in kv_buckets_list:
            bucket_name = bucket.get("name", "<unnamed>")
            missing = KV_REQUIRED_FIELDS - set(bucket.keys())
            assert not missing, (
                f"KV bucket '{bucket_name}' is missing required fields: {missing}"
            )

    def test_name_is_string(self, kv_buckets_list: list[dict]) -> None:
        for bucket in kv_buckets_list:
            assert isinstance(bucket["name"], str), (
                f"KV bucket name must be a string, got {type(bucket['name'])}"
            )

    def test_description_is_string(self, kv_buckets_list: list[dict]) -> None:
        for bucket in kv_buckets_list:
            name = bucket.get("name", "<unnamed>")
            assert isinstance(bucket["description"], str), (
                f"KV bucket '{name}': description must be a string"
            )

    def test_description_is_not_empty(self, kv_buckets_list: list[dict]) -> None:
        for bucket in kv_buckets_list:
            name = bucket.get("name", "<unnamed>")
            assert len(bucket["description"].strip()) > 0, (
                f"KV bucket '{name}': description must not be empty"
            )


# --- TASK-JSTR-003 AC-004: TTL values applied correctly ---


class TestKvBucketTtlValues:
    """TASK-JSTR-003 AC-004: TTL values applied correctly (null = no TTL, persistent)."""

    def test_ttl_is_null_or_valid_duration(self, kv_buckets_list: list[dict]) -> None:
        for bucket in kv_buckets_list:
            name = bucket.get("name", "<unnamed>")
            ttl = bucket.get("ttl")
            if ttl is not None:
                assert isinstance(ttl, str), (
                    f"KV bucket '{name}': ttl must be null or a string, got {type(ttl)}"
                )
                assert NATS_DURATION_PATTERN.match(ttl), (
                    f"KV bucket '{name}': ttl '{ttl}' does not match NATS duration format "
                    f"(expected pattern like '7d', '1h')"
                )

    @pytest.mark.parametrize("bucket_name", list(EXPECTED_KV_BUCKETS.keys()))
    def test_expected_ttl_values(
        self, kv_buckets_by_name: dict[str, dict], bucket_name: str
    ) -> None:
        expected = EXPECTED_KV_BUCKETS[bucket_name]
        actual = kv_buckets_by_name[bucket_name]
        assert actual["ttl"] == expected["ttl"], (
            f"KV bucket '{bucket_name}': ttl mismatch — "
            f"expected {expected['ttl']!r}, got {actual['ttl']!r}"
        )

    def test_agent_status_is_persistent(
        self, kv_buckets_by_name: dict[str, dict]
    ) -> None:
        assert kv_buckets_by_name["agent-status"]["ttl"] is None, (
            "agent-status must have null TTL (persistent)"
        )

    def test_agent_registry_is_persistent(
        self, kv_buckets_by_name: dict[str, dict]
    ) -> None:
        assert kv_buckets_by_name["agent-registry"]["ttl"] is None, (
            "agent-registry must have null TTL (persistent)"
        )

    def test_pipeline_state_ttl_is_7d(
        self, kv_buckets_by_name: dict[str, dict]
    ) -> None:
        assert kv_buckets_by_name["pipeline-state"]["ttl"] == "7d", (
            f"pipeline-state TTL must be '7d', got '{kv_buckets_by_name['pipeline-state']['ttl']}'"
        )

    def test_jarvis_session_ttl_is_1h(
        self, kv_buckets_by_name: dict[str, dict]
    ) -> None:
        assert kv_buckets_by_name["jarvis-session"]["ttl"] == "1h", (
            f"jarvis-session TTL must be '1h', got '{kv_buckets_by_name['jarvis-session']['ttl']}'"
        )


# --- KV bucket naming convention ---


class TestKvBucketNaming:
    """KV bucket names must follow kebab-case convention."""

    KEBAB_CASE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(-[a-z][a-z0-9]*)*$")

    def test_bucket_names_are_kebab_case(self, kv_buckets_list: list[dict]) -> None:
        for bucket in kv_buckets_list:
            name = bucket["name"]
            assert self.KEBAB_CASE_PATTERN.match(name), (
                f"KV bucket name '{name}' does not follow kebab-case convention"
            )


# --- Seam test: kv_buckets contract ---


@pytest.mark.seam
class TestKvBucketsContract:
    """Seam test: verify kv_buckets section in stream-definitions.json."""

    def test_top_level_kv_buckets_key_exists(self, stream_defs: dict) -> None:
        assert "kv_buckets" in stream_defs, "Top-level 'kv_buckets' key must exist"

    def test_at_least_4_kv_buckets(self, kv_buckets_list: list[dict]) -> None:
        assert len(kv_buckets_list) >= 4, (
            f"Expected at least 4 KV buckets, got {len(kv_buckets_list)}"
        )

    def test_all_buckets_have_required_fields(
        self, kv_buckets_list: list[dict]
    ) -> None:
        for bucket in kv_buckets_list:
            assert "name" in bucket, "KV bucket missing 'name' field"
            assert "ttl" in bucket, (
                f"KV bucket '{bucket.get('name', '?')}' missing 'ttl' field"
            )
            assert "description" in bucket, (
                f"KV bucket '{bucket.get('name', '?')}' missing 'description' field"
            )
