"""Tests for kv/kv-definitions.json — validates JetStream KV bucket definitions.

Verifies all acceptance criteria for TASK-KV-001:
- AC-001: kv/kv-definitions.json exists with valid JSON
- AC-002: All 4 buckets defined with name, ttl, storage, history, max_value_size, description
- AC-003: TTL values use nats CLI duration format (e.g. "7d", "1h", "" for none)
- AC-004: Storage types correctly assigned (file for persistent, memory for ephemeral)
- AC-005: History depth matches spec requirements
- AC-006: JSON schema is consistent with stream-definitions.json style
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

# Path to the KV definitions file relative to the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
KV_DEFS_FILE = PROJECT_ROOT / "kv" / "kv-definitions.json"
STREAM_DEFS_FILE = PROJECT_ROOT / "streams" / "stream-definitions.json"

# Required fields for each KV bucket definition
KV_REQUIRED_FIELDS = {"name", "ttl", "storage", "history", "max_value_size", "description"}

# Valid NATS duration pattern for TTL values (or empty string for no TTL)
NATS_DURATION_PATTERN = re.compile(r"^\d+[smhd]$")

# Valid storage types
VALID_STORAGE_TYPES = {"file", "memory"}

# Expected KV bucket specs from TASK-KV-001
EXPECTED_KV_BUCKETS = {
    "agent-status": {
        "ttl": "",
        "storage": "file",
        "history": 1,
        "max_value_size": "64KB",
        "description_contains": "status",
    },
    "agent-registry": {
        "ttl": "",
        "storage": "file",
        "history": 5,
        "max_value_size": "256KB",
        "description_contains": "routing",
    },
    "pipeline-state": {
        "ttl": "7d",
        "storage": "file",
        "history": 3,
        "max_value_size": "64KB",
        "description_contains": "pipeline",
    },
    "jarvis-session": {
        "ttl": "1h",
        "storage": "memory",
        "history": 1,
        "max_value_size": "128KB",
        "description_contains": "session",
    },
}

# Kebab-case bucket name pattern
KEBAB_CASE_PATTERN = re.compile(r"^[a-z][a-z0-9]*(-[a-z][a-z0-9]*)*$")


# --- Fixtures ---


@pytest.fixture
def kv_defs_text() -> str:
    """Read the kv-definitions.json file content."""
    assert KV_DEFS_FILE.exists(), f"kv-definitions.json not found at {KV_DEFS_FILE}"
    return KV_DEFS_FILE.read_text(encoding="utf-8")


@pytest.fixture
def kv_defs(kv_defs_text: str) -> dict:
    """Parse kv-definitions.json as JSON."""
    data = json.loads(kv_defs_text)
    assert isinstance(data, dict), "kv-definitions.json must be a valid JSON object"
    return data


@pytest.fixture
def kv_buckets_list(kv_defs: dict) -> list[dict]:
    """Extract the kv_buckets array from the definitions."""
    assert "kv_buckets" in kv_defs, "kv-definitions.json must have a 'kv_buckets' key"
    kv_buckets = kv_defs["kv_buckets"]
    assert isinstance(kv_buckets, list), "'kv_buckets' must be a JSON array"
    return kv_buckets


@pytest.fixture
def kv_buckets_by_name(kv_buckets_list: list[dict]) -> dict[str, dict]:
    """Index KV buckets by name for easy lookup."""
    return {b["name"]: b for b in kv_buckets_list}


# =============================================================================
# AC-001: kv/kv-definitions.json exists with valid JSON
# =============================================================================


class TestKvDefsFileExists:
    """AC-001: kv/kv-definitions.json exists with valid JSON."""

    def test_file_exists(self) -> None:
        assert KV_DEFS_FILE.exists(), (
            f"Expected kv-definitions.json at {KV_DEFS_FILE}"
        )

    def test_file_is_not_empty(self, kv_defs_text: str) -> None:
        assert len(kv_defs_text.strip()) > 0, (
            "kv-definitions.json must not be empty"
        )

    def test_file_in_kv_directory(self) -> None:
        kv_dir = PROJECT_ROOT / "kv"
        assert kv_dir.is_dir(), f"Expected 'kv' directory at {kv_dir}"

    def test_json_is_parseable(self, kv_defs_text: str) -> None:
        try:
            data = json.loads(kv_defs_text)
        except json.JSONDecodeError as e:
            pytest.fail(f"kv-definitions.json is not valid JSON: {e}")
        assert isinstance(data, dict), "Top-level must be a JSON object"

    def test_has_kv_buckets_key(self, kv_defs: dict) -> None:
        assert "kv_buckets" in kv_defs, (
            "kv-definitions.json must have a top-level 'kv_buckets' key"
        )

    def test_kv_buckets_is_array(self, kv_defs: dict) -> None:
        assert isinstance(kv_defs["kv_buckets"], list), "'kv_buckets' must be an array"


# =============================================================================
# AC-002: All 4 buckets defined with name, ttl, storage, history, max_value_size, description
# =============================================================================


class TestKvBucketDefinitions:
    """AC-002: All 4 buckets defined with required fields."""

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

    def test_history_is_integer(self, kv_buckets_list: list[dict]) -> None:
        for bucket in kv_buckets_list:
            name = bucket.get("name", "<unnamed>")
            assert isinstance(bucket["history"], int), (
                f"KV bucket '{name}': history must be an integer, got {type(bucket['history'])}"
            )

    def test_max_value_size_is_string(self, kv_buckets_list: list[dict]) -> None:
        for bucket in kv_buckets_list:
            name = bucket.get("name", "<unnamed>")
            assert isinstance(bucket["max_value_size"], str), (
                f"KV bucket '{name}': max_value_size must be a string, got {type(bucket['max_value_size'])}"
            )

    def test_storage_is_string(self, kv_buckets_list: list[dict]) -> None:
        for bucket in kv_buckets_list:
            name = bucket.get("name", "<unnamed>")
            assert isinstance(bucket["storage"], str), (
                f"KV bucket '{name}': storage must be a string, got {type(bucket['storage'])}"
            )

    @pytest.mark.parametrize("bucket_name", list(EXPECTED_KV_BUCKETS.keys()))
    def test_description_contains_expected_keyword(
        self, kv_buckets_by_name: dict[str, dict], bucket_name: str
    ) -> None:
        expected = EXPECTED_KV_BUCKETS[bucket_name]
        actual = kv_buckets_by_name[bucket_name]
        keyword = expected["description_contains"]
        assert keyword.lower() in actual["description"].lower(), (
            f"KV bucket '{bucket_name}': description should contain '{keyword}', "
            f"got '{actual['description']}'"
        )


# =============================================================================
# AC-003: TTL values use nats CLI duration format (e.g. "7d", "1h", "" for none)
# =============================================================================


class TestKvBucketTtlFormat:
    """AC-003: TTL values use nats CLI duration format."""

    def test_ttl_is_string(self, kv_buckets_list: list[dict]) -> None:
        for bucket in kv_buckets_list:
            name = bucket.get("name", "<unnamed>")
            assert isinstance(bucket["ttl"], str), (
                f"KV bucket '{name}': ttl must be a string (empty for no TTL), got {type(bucket['ttl'])}"
            )

    def test_ttl_is_empty_or_valid_duration(self, kv_buckets_list: list[dict]) -> None:
        for bucket in kv_buckets_list:
            name = bucket.get("name", "<unnamed>")
            ttl = bucket["ttl"]
            if ttl != "":
                assert NATS_DURATION_PATTERN.match(ttl), (
                    f"KV bucket '{name}': ttl '{ttl}' does not match NATS duration format "
                    f"(expected pattern like '7d', '1h', or '' for none)"
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

    def test_agent_status_no_ttl(self, kv_buckets_by_name: dict[str, dict]) -> None:
        assert kv_buckets_by_name["agent-status"]["ttl"] == "", (
            "agent-status must have empty TTL (no expiration)"
        )

    def test_agent_registry_no_ttl(self, kv_buckets_by_name: dict[str, dict]) -> None:
        assert kv_buckets_by_name["agent-registry"]["ttl"] == "", (
            "agent-registry must have empty TTL (no expiration)"
        )

    def test_pipeline_state_ttl_is_7d(self, kv_buckets_by_name: dict[str, dict]) -> None:
        assert kv_buckets_by_name["pipeline-state"]["ttl"] == "7d", (
            f"pipeline-state TTL must be '7d', got '{kv_buckets_by_name['pipeline-state']['ttl']}'"
        )

    def test_jarvis_session_ttl_is_1h(self, kv_buckets_by_name: dict[str, dict]) -> None:
        assert kv_buckets_by_name["jarvis-session"]["ttl"] == "1h", (
            f"jarvis-session TTL must be '1h', got '{kv_buckets_by_name['jarvis-session']['ttl']}'"
        )


# =============================================================================
# AC-004: Storage types correctly assigned (file for persistent, memory for ephemeral)
# =============================================================================


class TestKvBucketStorageTypes:
    """AC-004: Storage types correctly assigned."""

    def test_storage_is_valid_type(self, kv_buckets_list: list[dict]) -> None:
        for bucket in kv_buckets_list:
            name = bucket.get("name", "<unnamed>")
            assert bucket["storage"] in VALID_STORAGE_TYPES, (
                f"KV bucket '{name}': storage must be one of {VALID_STORAGE_TYPES}, "
                f"got '{bucket['storage']}'"
            )

    def test_agent_status_storage_is_file(self, kv_buckets_by_name: dict[str, dict]) -> None:
        assert kv_buckets_by_name["agent-status"]["storage"] == "file", (
            "agent-status must use 'file' storage (persistent)"
        )

    def test_agent_registry_storage_is_file(self, kv_buckets_by_name: dict[str, dict]) -> None:
        assert kv_buckets_by_name["agent-registry"]["storage"] == "file", (
            "agent-registry must use 'file' storage (persistent)"
        )

    def test_pipeline_state_storage_is_file(self, kv_buckets_by_name: dict[str, dict]) -> None:
        assert kv_buckets_by_name["pipeline-state"]["storage"] == "file", (
            "pipeline-state must use 'file' storage (persistent)"
        )

    def test_jarvis_session_storage_is_memory(self, kv_buckets_by_name: dict[str, dict]) -> None:
        assert kv_buckets_by_name["jarvis-session"]["storage"] == "memory", (
            "jarvis-session must use 'memory' storage (ephemeral)"
        )

    @pytest.mark.parametrize("bucket_name", list(EXPECTED_KV_BUCKETS.keys()))
    def test_expected_storage_values(
        self, kv_buckets_by_name: dict[str, dict], bucket_name: str
    ) -> None:
        expected = EXPECTED_KV_BUCKETS[bucket_name]
        actual = kv_buckets_by_name[bucket_name]
        assert actual["storage"] == expected["storage"], (
            f"KV bucket '{bucket_name}': storage mismatch — "
            f"expected '{expected['storage']}', got '{actual['storage']}'"
        )


# =============================================================================
# AC-005: History depth matches spec requirements
# =============================================================================


class TestKvBucketHistoryDepth:
    """AC-005: History depth matches spec requirements."""

    def test_history_is_positive_integer(self, kv_buckets_list: list[dict]) -> None:
        for bucket in kv_buckets_list:
            name = bucket.get("name", "<unnamed>")
            history = bucket["history"]
            assert isinstance(history, int) and history >= 1, (
                f"KV bucket '{name}': history must be a positive integer, got {history}"
            )

    def test_agent_status_history_is_1(self, kv_buckets_by_name: dict[str, dict]) -> None:
        assert kv_buckets_by_name["agent-status"]["history"] == 1, (
            f"agent-status history must be 1, got {kv_buckets_by_name['agent-status']['history']}"
        )

    def test_agent_registry_history_is_5(self, kv_buckets_by_name: dict[str, dict]) -> None:
        assert kv_buckets_by_name["agent-registry"]["history"] == 5, (
            f"agent-registry history must be 5, got {kv_buckets_by_name['agent-registry']['history']}"
        )

    def test_pipeline_state_history_is_3(self, kv_buckets_by_name: dict[str, dict]) -> None:
        assert kv_buckets_by_name["pipeline-state"]["history"] == 3, (
            f"pipeline-state history must be 3, got {kv_buckets_by_name['pipeline-state']['history']}"
        )

    def test_jarvis_session_history_is_1(self, kv_buckets_by_name: dict[str, dict]) -> None:
        assert kv_buckets_by_name["jarvis-session"]["history"] == 1, (
            f"jarvis-session history must be 1, got {kv_buckets_by_name['jarvis-session']['history']}"
        )

    @pytest.mark.parametrize("bucket_name", list(EXPECTED_KV_BUCKETS.keys()))
    def test_expected_history_values(
        self, kv_buckets_by_name: dict[str, dict], bucket_name: str
    ) -> None:
        expected = EXPECTED_KV_BUCKETS[bucket_name]
        actual = kv_buckets_by_name[bucket_name]
        assert actual["history"] == expected["history"], (
            f"KV bucket '{bucket_name}': history mismatch — "
            f"expected {expected['history']}, got {actual['history']}"
        )


# =============================================================================
# AC-006: JSON schema is consistent with stream-definitions.json style
# =============================================================================


class TestKvDefsStyleConsistency:
    """AC-006: JSON schema is consistent with stream-definitions.json style."""

    def test_top_level_is_object_with_array_value(self, kv_defs: dict) -> None:
        """Same pattern as stream-definitions.json: top-level object with array value."""
        assert isinstance(kv_defs, dict), "Top-level must be a JSON object"
        assert "kv_buckets" in kv_defs, "Must have 'kv_buckets' key"
        assert isinstance(kv_defs["kv_buckets"], list), "'kv_buckets' must be an array"

    def test_each_bucket_is_object(self, kv_buckets_list: list[dict]) -> None:
        for i, bucket in enumerate(kv_buckets_list):
            assert isinstance(bucket, dict), (
                f"KV bucket at index {i} must be a JSON object"
            )

    def test_bucket_names_are_kebab_case(self, kv_buckets_list: list[dict]) -> None:
        """Same naming convention as streams (lowercase with hyphens)."""
        for bucket in kv_buckets_list:
            name = bucket["name"]
            assert KEBAB_CASE_PATTERN.match(name), (
                f"KV bucket name '{name}' does not follow kebab-case convention"
            )

    def test_all_buckets_have_replicas_field(self, kv_buckets_list: list[dict]) -> None:
        """Consistent with stream-definitions.json including replicas."""
        for bucket in kv_buckets_list:
            name = bucket.get("name", "<unnamed>")
            assert "replicas" in bucket, (
                f"KV bucket '{name}' missing 'replicas' field "
                f"(consistent with stream-definitions.json style)"
            )

    def test_all_replicas_are_1(self, kv_buckets_list: list[dict]) -> None:
        """Single-node deployment: replicas must be 1."""
        for bucket in kv_buckets_list:
            name = bucket.get("name", "<unnamed>")
            assert bucket["replicas"] == 1, (
                f"KV bucket '{name}': replicas must be 1 (single server), got {bucket['replicas']}"
            )

    def test_all_buckets_have_description(self, kv_buckets_list: list[dict]) -> None:
        """Consistent with stream-definitions.json: every entry has description."""
        for bucket in kv_buckets_list:
            name = bucket.get("name", "<unnamed>")
            assert "description" in bucket, (
                f"KV bucket '{name}' missing 'description' field"
            )
            assert isinstance(bucket["description"], str), (
                f"KV bucket '{name}': description must be a string"
            )
            assert len(bucket["description"].strip()) > 0, (
                f"KV bucket '{name}': description must not be empty"
            )


# =============================================================================
# Max value size validation
# =============================================================================


class TestKvBucketMaxValueSize:
    """Max value size values use human-readable KB format."""

    MAX_VALUE_SIZE_PATTERN = re.compile(r"^\d+KB$")

    def test_max_value_size_format(self, kv_buckets_list: list[dict]) -> None:
        for bucket in kv_buckets_list:
            name = bucket.get("name", "<unnamed>")
            mvs = bucket["max_value_size"]
            assert self.MAX_VALUE_SIZE_PATTERN.match(mvs), (
                f"KV bucket '{name}': max_value_size '{mvs}' must match pattern like '64KB'"
            )

    @pytest.mark.parametrize("bucket_name", list(EXPECTED_KV_BUCKETS.keys()))
    def test_expected_max_value_size(
        self, kv_buckets_by_name: dict[str, dict], bucket_name: str
    ) -> None:
        expected = EXPECTED_KV_BUCKETS[bucket_name]
        actual = kv_buckets_by_name[bucket_name]
        assert actual["max_value_size"] == expected["max_value_size"], (
            f"KV bucket '{bucket_name}': max_value_size mismatch — "
            f"expected '{expected['max_value_size']}', got '{actual['max_value_size']}'"
        )


# =============================================================================
# Seam test: kv-definitions contract
# =============================================================================


@pytest.mark.seam
class TestKvDefinitionsContract:
    """Seam test: verify kv-definitions.json contract for downstream consumers."""

    def test_file_exists_at_expected_path(self) -> None:
        assert KV_DEFS_FILE.exists(), (
            f"kv-definitions.json must exist at {KV_DEFS_FILE}"
        )

    def test_top_level_kv_buckets_key_exists(self, kv_defs: dict) -> None:
        assert "kv_buckets" in kv_defs, "Top-level 'kv_buckets' key must exist"

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
            assert "storage" in bucket, (
                f"KV bucket '{bucket.get('name', '?')}' missing 'storage' field"
            )
            assert "history" in bucket, (
                f"KV bucket '{bucket.get('name', '?')}' missing 'history' field"
            )
            assert "max_value_size" in bucket, (
                f"KV bucket '{bucket.get('name', '?')}' missing 'max_value_size' field"
            )
            assert "description" in bucket, (
                f"KV bucket '{bucket.get('name', '?')}' missing 'description' field"
            )
