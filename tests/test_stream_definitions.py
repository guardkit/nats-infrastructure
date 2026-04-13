"""Tests for streams/stream-definitions.json — validates JetStream stream definitions.

Verifies all acceptance criteria for TASK-JSTR-001:
- AC-001: File created at streams/stream-definitions.json
- AC-002: All 6 core streams defined with exact spec values
- AC-003: FINPROXY project stream included with scope=project and reasonable defaults (24h, 5000)
- AC-004: All required fields present: name, subjects, retention, max_age, max_msgs, storage, replicas
- AC-005: JSON is valid (parseable)
- AC-006: Retention values use NATS CLI format: work (WorkQueue) or limits (Limits)
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

# Path to the stream definitions file relative to the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
STREAM_DEFS_FILE = PROJECT_ROOT / "streams" / "stream-definitions.json"

# Required fields for each stream definition
REQUIRED_FIELDS = {"name", "subjects", "retention", "max_age", "max_msgs", "storage", "replicas"}

# Valid retention values in NATS CLI format
VALID_RETENTION_VALUES = {"work", "limits"}

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
    assert STREAM_DEFS_FILE.exists(), f"stream-definitions.json not found at {STREAM_DEFS_FILE}"
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
        assert streams_dir.is_dir(), (
            f"Expected 'streams' directory at {streams_dir}"
        )


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
        assert isinstance(stream_defs["streams"], list), (
            "'streams' must be an array"
        )


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

    def test_all_six_core_streams_present(self, streams_by_name: dict[str, dict]) -> None:
        for stream_name in EXPECTED_CORE_STREAMS:
            assert stream_name in streams_by_name, (
                f"Core stream '{stream_name}' not found in definitions"
            )

    def test_core_streams_have_core_scope(self, streams_by_name: dict[str, dict]) -> None:
        for stream_name in EXPECTED_CORE_STREAMS:
            stream = streams_by_name[stream_name]
            assert stream.get("scope") == "core", (
                f"Core stream '{stream_name}' must have scope='core', got '{stream.get('scope')}'"
            )

    @pytest.mark.parametrize("stream_name", list(EXPECTED_CORE_STREAMS.keys()))
    def test_core_stream_subjects(self, streams_by_name: dict[str, dict], stream_name: str) -> None:
        expected = EXPECTED_CORE_STREAMS[stream_name]
        actual = streams_by_name[stream_name]
        assert actual["subjects"] == expected["subjects"], (
            f"Stream '{stream_name}': subjects mismatch — "
            f"expected {expected['subjects']}, got {actual['subjects']}"
        )

    @pytest.mark.parametrize("stream_name", list(EXPECTED_CORE_STREAMS.keys()))
    def test_core_stream_retention(self, streams_by_name: dict[str, dict], stream_name: str) -> None:
        expected = EXPECTED_CORE_STREAMS[stream_name]
        actual = streams_by_name[stream_name]
        assert actual["retention"] == expected["retention"], (
            f"Stream '{stream_name}': retention mismatch — "
            f"expected '{expected['retention']}', got '{actual['retention']}'"
        )

    @pytest.mark.parametrize("stream_name", list(EXPECTED_CORE_STREAMS.keys()))
    def test_core_stream_max_age(self, streams_by_name: dict[str, dict], stream_name: str) -> None:
        expected = EXPECTED_CORE_STREAMS[stream_name]
        actual = streams_by_name[stream_name]
        assert actual["max_age"] == expected["max_age"], (
            f"Stream '{stream_name}': max_age mismatch — "
            f"expected '{expected['max_age']}', got '{actual['max_age']}'"
        )

    @pytest.mark.parametrize("stream_name", list(EXPECTED_CORE_STREAMS.keys()))
    def test_core_stream_max_msgs(self, streams_by_name: dict[str, dict], stream_name: str) -> None:
        expected = EXPECTED_CORE_STREAMS[stream_name]
        actual = streams_by_name[stream_name]
        assert actual["max_msgs"] == expected["max_msgs"], (
            f"Stream '{stream_name}': max_msgs mismatch — "
            f"expected {expected['max_msgs']}, got {actual['max_msgs']}"
        )

    @pytest.mark.parametrize("stream_name", list(EXPECTED_CORE_STREAMS.keys()))
    def test_core_stream_storage(self, streams_by_name: dict[str, dict], stream_name: str) -> None:
        expected = EXPECTED_CORE_STREAMS[stream_name]
        actual = streams_by_name[stream_name]
        assert actual["storage"] == expected["storage"], (
            f"Stream '{stream_name}': storage mismatch — "
            f"expected '{expected['storage']}', got '{actual['storage']}'"
        )

    @pytest.mark.parametrize("stream_name", list(EXPECTED_CORE_STREAMS.keys()))
    def test_core_stream_replicas(self, streams_by_name: dict[str, dict], stream_name: str) -> None:
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
        assert "FINPROXY" in streams_by_name, (
            "FINPROXY stream not found in definitions"
        )

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


# --- Additional validation: total stream count ---


class TestStreamCount:
    """Verify total number of streams matches spec (6 core + 1 project)."""

    def test_total_stream_count(self, streams_list: list[dict]) -> None:
        assert len(streams_list) == 7, (
            f"Expected 7 streams (6 core + 1 project), got {len(streams_list)}"
        )

    def test_no_duplicate_stream_names(self, streams_list: list[dict]) -> None:
        names = [s["name"] for s in streams_list]
        assert len(names) == len(set(names)), (
            f"Duplicate stream names found: {names}"
        )

    def test_no_duplicate_subjects(self, streams_list: list[dict]) -> None:
        all_subjects = []
        for s in streams_list:
            all_subjects.extend(s["subjects"])
        assert len(all_subjects) == len(set(all_subjects)), (
            f"Duplicate subjects found: {all_subjects}"
        )
