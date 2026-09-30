"""Behavioural tests for kv/provision-kv.sh reconciliation, run offline.

The scripts run for real against tests/fake_nats.py (a stand-in `nats` on
PATH that keeps bucket state in a JSON file and logs every call). Covers:
- drift detection against kv/kv-definitions.json
- correction in place with `nats kv edit` (never `nats kv update`)
- refusal of a storage-type change unless --recreate names the bucket
- delete+recreate with --recreate
- --dry-run changes nothing
- non-zero exit on any failure
- TTL compared in exact nanoseconds (sub-second drift is not rounded away)
- malformed/partial stream info is refused before anything is changed
- streams/provision-streams.sh no longer touches KV buckets
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
KV_SCRIPT = PROJECT_ROOT / "kv" / "provision-kv.sh"
STREAMS_SCRIPT = PROJECT_ROOT / "streams" / "provision-streams.sh"
FAKE_NATS = Path(__file__).resolve().parent / "fake_nats.py"

pytestmark = pytest.mark.skipif(
    shutil.which("jq") is None, reason="provisioning scripts require jq"
)

# What the definitions want, in the fake's units
WANT = {
    "agent-status": {"storage": "file", "history": 1, "max_value_size": 65536, "ttl_s": 0, "replicas": 1},
    "agent-registry": {"storage": "file", "history": 5, "max_value_size": 262144, "ttl_s": 0, "replicas": 1},
    "pipeline-state": {"storage": "file", "history": 3, "max_value_size": 65536, "ttl_s": 604800, "replicas": 1},
    "jarvis-session": {"storage": "memory", "history": 1, "max_value_size": 131072, "ttl_s": 3600, "replicas": 1},
}

WRITE_VERBS = {("kv", "add"), ("kv", "edit"), ("kv", "del"), ("kv", "update")}


def _bare(**overrides) -> dict:
    """A bucket as a bare `nats kv add <name> [--ttl]` leaves it."""
    bucket = {"storage": "file", "history": 1, "max_value_size": -1, "ttl_s": 0, "replicas": 1, "messages": 0}
    bucket.update(overrides)
    return bucket


def _live_drifted() -> dict:
    """The live buckets as found on 30 September (created by provision-streams.sh)."""
    return {
        "agent-status": _bare(messages=4),
        "agent-registry": _bare(messages=6),
        "pipeline-state": _bare(ttl_s=604800, messages=3),
        "jarvis-session": _bare(ttl_s=3600, messages=2),
    }


class FakeNats:
    """Drives a script with the fake nats CLI first on PATH."""

    def __init__(self, tmp_path: Path) -> None:
        self.bin_dir = tmp_path / "bin"
        self.bin_dir.mkdir()
        shim = self.bin_dir / "nats"
        shim.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{FAKE_NATS}" "$@"\n')
        shim.chmod(0o755)
        self.state_file = tmp_path / "state.json"
        self.log_file = tmp_path / "calls.log"
        self.log_file.write_text("")
        self.seed({})

    def seed(self, buckets: dict) -> None:
        self.state_file.write_text(json.dumps({"buckets": buckets, "streams": {}}))

    def state(self) -> dict:
        return json.loads(self.state_file.read_text())

    def buckets(self) -> dict:
        return self.state()["buckets"]

    def calls(self) -> list[list[str]]:
        return [json.loads(line) for line in self.log_file.read_text().splitlines()]

    def verbs(self) -> list[tuple[str, ...]]:
        return [tuple(a for a in c if not a.startswith("-"))[:2] for c in self.calls()]

    def writes(self) -> list[list[str]]:
        return [c for c, v in zip(self.calls(), self.verbs()) if v in WRITE_VERBS]

    def run(self, script: Path, *args: str, **env: str) -> subprocess.CompletedProcess:
        full_env = {
            k: v for k, v in os.environ.items()
            if not k.startswith(("NATS_", "FAKE_NATS_"))
        }
        full_env.update(
            PATH=f"{self.bin_dir}{os.pathsep}{os.environ.get('PATH', '')}",
            NATS_URL="nats://fake-host:4222",
            FAKE_NATS_STATE=str(self.state_file),
            FAKE_NATS_LOG=str(self.log_file),
        )
        full_env.update(env)
        return subprocess.run(
            ["bash", str(script), *args],
            capture_output=True, text=True, env=full_env, timeout=60,
        )


@pytest.fixture
def fake(tmp_path: Path) -> FakeNats:
    return FakeNats(tmp_path)


def _settings(bucket: dict) -> dict:
    return {k: bucket[k] for k in ("storage", "history", "max_value_size", "ttl_s", "replicas")}


# =============================================================================
# Drift detection
# =============================================================================


class TestDriftDetection:
    def test_dry_run_reports_each_drifted_setting(self, fake: FakeNats) -> None:
        fake.seed(_live_drifted())
        result = fake.run(KV_SCRIPT, "--dry-run")
        out = result.stdout
        assert "Would update KV agent-status: max_value_size -1 -> 65536" in out
        assert "Would update KV agent-registry: history 1 -> 5, max_value_size -1 -> 262144" in out
        assert "Would update KV pipeline-state: history 1 -> 3, max_value_size -1 -> 65536" in out
        assert "Would update KV jarvis-session: max_value_size -1 -> 131072" in out
        assert "[REFUSED] KV jarvis-session — storage is file, definition wants memory." in result.stderr

    def test_matching_ttl_and_replicas_are_not_reported(self, fake: FakeNats) -> None:
        fake.seed(_live_drifted())
        out = fake.run(KV_SCRIPT, "--dry-run").stdout
        summaries = [line for line in out.splitlines() if "Would update KV" in line]
        assert len(summaries) == 4
        for line in summaries:
            assert "ttl " not in line
            assert "replicas " not in line

    def test_ttl_drift_is_reported(self, fake: FakeNats) -> None:
        buckets = {n: dict(w, messages=0) for n, w in WANT.items()}
        buckets["pipeline-state"]["ttl_s"] = 86400
        fake.seed(buckets)
        result = fake.run(KV_SCRIPT, "--dry-run")
        assert "Would update KV pipeline-state: ttl 86400s -> 604800s" in result.stdout
        assert result.returncode == 0

    def test_matching_buckets_are_ok(self, fake: FakeNats) -> None:
        fake.seed({n: dict(w, messages=0) for n, w in WANT.items()})
        result = fake.run(KV_SCRIPT)
        assert result.returncode == 0, result.stderr
        for name in WANT:
            assert f"[OK] KV {name}" in result.stdout
        assert fake.writes() == []
        assert "0 created, 0 updated, 0 recreated, 4 already current, 0 errors" in result.stdout


# =============================================================================
# Correction in place with nats kv edit
# =============================================================================


class TestEditCommands:
    def test_edits_use_kv_edit_with_every_managed_setting(self, fake: FakeNats) -> None:
        fake.seed(_live_drifted())
        fake.run(KV_SCRIPT, "--recreate", "jarvis-session")
        edits = {c[2]: c for c in fake.writes() if c[:2] == ["kv", "edit"]}
        assert set(edits) == {"agent-status", "agent-registry", "pipeline-state"}
        reg = edits["agent-registry"]
        for flag, value in (("--history", "5"), ("--max-value-size", "262144"), ("--replicas", "1")):
            assert reg[reg.index(flag) + 1] == value
        assert "--storage" not in reg
        assert "--ttl" not in reg
        pipe = edits["pipeline-state"]
        assert pipe[pipe.index("--ttl") + 1] == "604800s"

    def test_never_calls_kv_update(self, fake: FakeNats) -> None:
        fake.seed(_live_drifted())
        fake.run(KV_SCRIPT, "--recreate", "jarvis-session")
        assert ("kv", "update") not in fake.verbs()

    def test_edits_are_confirmed_by_rereading(self, fake: FakeNats) -> None:
        fake.seed(_live_drifted())
        fake.run(KV_SCRIPT, "--recreate", "jarvis-session")
        infos = [c for c in fake.calls() if c[:2] == ["stream", "info"] and c[2] == "KV_agent-status"]
        assert len(infos) == 2, "read once to compare, once to confirm"

    def test_connection_options_are_passed_to_every_call(self, fake: FakeNats) -> None:
        fake.seed(_live_drifted())
        fake.run(KV_SCRIPT, "--dry-run", NATS_CREDS="/path/to/test.creds")
        for call in fake.calls():
            assert call[call.index("--server") + 1] == "nats://fake-host:4222"
            assert call[call.index("--creds") + 1] == "/path/to/test.creds"


# =============================================================================
# Storage change: refused without --recreate, done with it
# =============================================================================


class TestStorageChange:
    def test_refused_without_flag(self, fake: FakeNats) -> None:
        fake.seed(_live_drifted())
        result = fake.run(KV_SCRIPT)
        assert result.returncode == 1
        assert "Re-run with --recreate jarvis-session" in result.stderr
        assert ("kv", "del") not in fake.verbs()
        session = fake.buckets()["jarvis-session"]
        assert session["storage"] == "file"
        assert session["messages"] == 2, "values must not be lost"

    def test_refusal_still_corrects_editable_settings(self, fake: FakeNats) -> None:
        fake.seed(_live_drifted())
        fake.run(KV_SCRIPT)
        buckets = fake.buckets()
        assert buckets["jarvis-session"]["max_value_size"] == 131072
        for name in ("agent-status", "agent-registry", "pipeline-state"):
            assert _settings(buckets[name]) == WANT[name]

    def test_recreate_with_flag(self, fake: FakeNats) -> None:
        fake.seed(_live_drifted())
        result = fake.run(KV_SCRIPT, "--recreate", "jarvis-session")
        assert result.returncode == 0, result.stdout + result.stderr
        assert "[RECREATE] KV jarvis-session — storage file -> memory" in result.stdout
        assert "2 stored value(s) lost" in result.stdout
        dels = [c for c in fake.writes() if c[:2] == ["kv", "del"]]
        assert [c[2] for c in dels] == ["jarvis-session"]
        assert "--force" in dels[0]
        assert {n: _settings(b) for n, b in fake.buckets().items()} == WANT

    def test_recreate_equals_form(self, fake: FakeNats) -> None:
        fake.seed(_live_drifted())
        result = fake.run(KV_SCRIPT, "--recreate=jarvis-session")
        assert result.returncode == 0
        assert fake.buckets()["jarvis-session"]["storage"] == "memory"

    def test_recreate_does_not_touch_bucket_whose_storage_matches(self, fake: FakeNats) -> None:
        fake.seed(_live_drifted())
        fake.run(KV_SCRIPT, "--recreate", "agent-status", "--recreate", "jarvis-session")
        dels = [c[2] for c in fake.writes() if c[:2] == ["kv", "del"]]
        assert dels == ["jarvis-session"]
        assert fake.buckets()["agent-status"]["messages"] == 4

    def test_recreate_unknown_bucket_is_rejected(self, fake: FakeNats) -> None:
        fake.seed(_live_drifted())
        result = fake.run(KV_SCRIPT, "--recreate", "jarvis-sesion")
        assert result.returncode == 2
        assert "no such bucket" in result.stderr
        assert fake.calls() == []

    def test_second_run_is_a_no_op(self, fake: FakeNats) -> None:
        fake.seed(_live_drifted())
        fake.run(KV_SCRIPT, "--recreate", "jarvis-session")
        fake.log_file.write_text("")
        result = fake.run(KV_SCRIPT, "--recreate", "jarvis-session")
        assert result.returncode == 0
        assert fake.writes() == []
        assert "4 already current" in result.stdout


# =============================================================================
# --dry-run changes nothing
# =============================================================================


class TestDryRun:
    def test_dry_run_changes_nothing(self, fake: FakeNats) -> None:
        fake.seed(_live_drifted())
        before = fake.state()
        fake.run(KV_SCRIPT, "--dry-run", "--recreate", "jarvis-session")
        assert fake.state() == before
        assert fake.writes() == []

    def test_dry_run_with_recreate_prints_plan_and_passes(self, fake: FakeNats) -> None:
        fake.seed(_live_drifted())
        result = fake.run(KV_SCRIPT, "--dry-run", "--recreate", "jarvis-session")
        assert result.returncode == 0, result.stderr
        out = result.stdout
        assert "Would RECREATE KV jarvis-session: storage file -> memory" in out
        assert "nats kv del jarvis-session --force" in out
        assert "nats kv add jarvis-session --storage memory --history 1 --replicas 1 --max-value-size 131072 --ttl 3600s" in out
        assert "nats kv edit agent-registry --history 5 --replicas 1 --max-value-size 262144" in out
        assert "KV Buckets (planned): 0 created, 3 updated, 1 recreated" in out

    def test_dry_run_exit_predicts_refusal(self, fake: FakeNats) -> None:
        fake.seed(_live_drifted())
        assert fake.run(KV_SCRIPT, "--dry-run").returncode == 1

    def test_dry_run_on_empty_server_plans_creates(self, fake: FakeNats) -> None:
        result = fake.run(KV_SCRIPT, "--dry-run")
        assert result.returncode == 0
        assert result.stdout.count("[DRY-RUN] Would create KV") == 4
        assert fake.buckets() == {}


# =============================================================================
# Creating missing buckets
# =============================================================================


class TestCreate:
    def test_creates_missing_buckets_with_definition_settings(self, fake: FakeNats) -> None:
        result = fake.run(KV_SCRIPT)
        assert result.returncode == 0, result.stderr
        assert {n: _settings(b) for n, b in fake.buckets().items()} == WANT
        for name in WANT:
            assert f"[CREATE] KV {name}" in result.stdout

    def test_creates_only_the_missing_bucket(self, fake: FakeNats) -> None:
        buckets = {n: dict(w, messages=1) for n, w in WANT.items() if n != "pipeline-state"}
        fake.seed(buckets)
        fake.run(KV_SCRIPT)
        adds = [c[2] for c in fake.writes() if c[:2] == ["kv", "add"]]
        assert adds == ["pipeline-state"]


# =============================================================================
# Non-zero exit on failure
# =============================================================================


class TestFailureExitCodes:
    def test_failed_edit_exits_nonzero(self, fake: FakeNats) -> None:
        fake.seed(_live_drifted())
        result = fake.run(KV_SCRIPT, "--recreate", "jarvis-session", FAKE_NATS_FAIL="kv edit")
        assert result.returncode == 1
        assert "[ERROR] KV agent-registry — failed to update bucket" in result.stderr
        assert "simulated failure" in result.stderr

    def test_edit_that_does_not_take_effect_exits_nonzero(self, fake: FakeNats) -> None:
        fake.seed(_live_drifted())
        result = fake.run(KV_SCRIPT, "--recreate", "jarvis-session", FAKE_NATS_EDIT_NOOP="1")
        assert result.returncode == 1
        assert "still differs after the change" in result.stderr

    def test_failed_create_exits_nonzero(self, fake: FakeNats) -> None:
        result = fake.run(KV_SCRIPT, FAKE_NATS_FAIL="kv add")
        assert result.returncode == 1
        assert "[ERROR] KV agent-status — failed to create bucket" in result.stderr

    def test_failed_delete_during_recreate_exits_nonzero(self, fake: FakeNats) -> None:
        fake.seed(_live_drifted())
        result = fake.run(KV_SCRIPT, "--recreate", "jarvis-session", FAKE_NATS_FAIL="kv del")
        assert result.returncode == 1
        assert ("kv", "add") not in fake.verbs()

    def test_unreadable_bucket_exits_nonzero(self, fake: FakeNats) -> None:
        fake.seed(_live_drifted())
        result = fake.run(KV_SCRIPT, "--dry-run", FAKE_NATS_FAIL="stream info")
        assert result.returncode == 1
        assert "could not read bucket settings" in result.stderr

    def test_bucket_listing_failure_is_fatal(self, fake: FakeNats) -> None:
        result = fake.run(KV_SCRIPT, FAKE_NATS_FAIL="kv ls")
        assert result.returncode == 1
        assert "[FATAL] Could not list KV buckets" in result.stderr
        assert fake.writes() == []

    def test_unknown_argument_exits_2(self, fake: FakeNats) -> None:
        result = fake.run(KV_SCRIPT, "--dryrun")
        assert result.returncode == 2
        assert fake.calls() == []

    def test_credentials_in_url_are_not_printed(self, fake: FakeNats) -> None:
        fake.seed(_live_drifted())
        result = fake.run(
            KV_SCRIPT, "--dry-run",
            NATS_URL="nats://someone:not-a-real-secret@fake-host:4222",
            FAKE_NATS_FAIL="stream info",
        )
        assert "not-a-real-secret" not in result.stdout + result.stderr
        assert "nats://***@fake-host:4222" in result.stdout


# =============================================================================
# TTL is compared in exact nanoseconds, never rounded to whole seconds
# =============================================================================


def _matching(**per_bucket: dict) -> dict:
    """Every bucket as defined, with per-bucket overrides."""
    buckets = {n: dict(w, messages=1) for n, w in WANT.items()}
    for name, overrides in per_bucket.items():
        buckets[name].update(overrides)
    return buckets


class TestTtlPrecision:
    def test_sub_second_ttl_on_persistent_bucket_is_drift(self, fake: FakeNats) -> None:
        # 500ms: floor() to whole seconds used to make this look like "no TTL"
        fake.seed(_matching(**{"agent-status": {"max_age_ns": 500_000_000}}))
        result = fake.run(KV_SCRIPT, "--dry-run")
        assert "Would update KV agent-status: ttl 0.5s -> 0s" in result.stdout
        assert "[OK] KV agent-status" not in result.stdout
        assert "nats kv edit agent-status --history 1 --replicas 1 --max-value-size 65536 --ttl 0s" in result.stdout

    def test_sub_second_ttl_is_removed_and_confirmed(self, fake: FakeNats) -> None:
        fake.seed(_matching(**{"agent-status": {"max_age_ns": 500_000_000}}))
        result = fake.run(KV_SCRIPT)
        assert result.returncode == 0, result.stderr
        assert "[UPDATE] KV agent-status: ttl 0.5s -> 0s" in result.stdout
        edits = [c for c in fake.writes() if c[:2] == ["kv", "edit"]]
        assert [c[2] for c in edits] == ["agent-status"]
        assert edits[0][edits[0].index("--ttl") + 1] == "0s"
        status = fake.buckets()["agent-status"]
        assert "max_age_ns" not in status and status["ttl_s"] == 0

    def test_fractional_second_drift_on_ttl_bucket_is_reported(self, fake: FakeNats) -> None:
        fake.seed(_matching(**{"jarvis-session": {"max_age_ns": 3_600_500_000_000}}))
        result = fake.run(KV_SCRIPT, "--dry-run")
        assert "Would update KV jarvis-session: ttl 3600.5s -> 3600s" in result.stdout
        assert "[OK] KV jarvis-session" not in result.stdout

    def test_nanosecond_drift_is_reported(self, fake: FakeNats) -> None:
        fake.seed(_matching(**{"pipeline-state": {"max_age_ns": 604_800_000_000_001}}))
        out = fake.run(KV_SCRIPT, "--dry-run").stdout
        assert "Would update KV pipeline-state: ttl 604800.000000001s -> 604800s" in out

    def test_confirm_detects_sub_second_residue(self, fake: FakeNats) -> None:
        # An edit that leaves 500ms behind must not be confirmed as done
        fake.seed(_matching(**{"agent-status": {"max_age_ns": 500_000_000}}))
        result = fake.run(KV_SCRIPT, FAKE_NATS_EDIT_NOOP="1")
        assert result.returncode == 1
        assert "[ERROR] KV agent-status — still differs after the change" in result.stderr

    def test_exact_ttls_are_current(self, fake: FakeNats) -> None:
        fake.seed(_matching())
        result = fake.run(KV_SCRIPT)
        assert result.returncode == 0, result.stderr
        assert "4 already current" in result.stdout


# =============================================================================
# Malformed or partial stream info is refused — never read as a difference
# =============================================================================


def _session_info(**config_overrides) -> dict:
    """A complete stream info response for a file-backed jarvis-session."""
    info = {
        "config": {
            "name": "KV_jarvis-session",
            "storage": "file",
            "max_msgs_per_subject": 1,
            "max_msg_size": 131072,
            "max_age": 3_600_000_000_000,
            "num_replicas": 1,
        },
        "state": {"messages": 2},
    }
    for key, value in config_overrides.items():
        if value is _DROP:
            del info["config"][key]
        else:
            info["config"][key] = value
    return info


_DROP = object()

MALFORMED_INFO = {
    "storage-missing": _session_info(storage=_DROP),
    "storage-null": _session_info(storage=None),
    "storage-unknown": _session_info(storage="disk"),
    "history-missing": _session_info(max_msgs_per_subject=_DROP),
    "history-string": _session_info(max_msgs_per_subject="1"),
    "ttl-missing": _session_info(max_age=_DROP),
    "ttl-fractional": _session_info(max_age=1.5),
    "replicas-missing": _session_info(num_replicas=_DROP),
    "max-value-size-invalid": _session_info(max_msg_size="128KB"),
    "wrong-stream": _session_info(name="KV_agent-status"),
    "state-missing": {"config": _session_info()["config"]},
    "config-missing": {"state": {"messages": 2}},
    "empty-object": {},
    "json-null": "null",
    "not-json": "nats: this is not json",
}


class TestMalformedStreamInfo:
    @pytest.fixture(params=sorted(MALFORMED_INFO), ids=sorted(MALFORMED_INFO))
    def malformed(self, request, fake: FakeNats) -> str:
        # Every other bucket matches, so ANY write at all is a failure
        fake.seed(_matching(**{"jarvis-session": {
            "storage": "file", "messages": 2, "stream_info": MALFORMED_INFO[request.param],
        }}))
        return request.param

    def test_refused_with_recreate_and_no_writes(self, fake: FakeNats, malformed: str) -> None:
        before = fake.state()
        result = fake.run(KV_SCRIPT, "--recreate", "jarvis-session")
        assert result.returncode == 1, result.stdout
        assert "[ERROR] KV jarvis-session — nats stream info KV_jarvis-session --json " \
               "returned missing or invalid settings" in result.stderr
        assert fake.writes() == []
        assert fake.state() == before
        assert "[RECREATE]" not in result.stdout

    def test_dry_run_plans_no_recreate(self, fake: FakeNats, malformed: str) -> None:
        result = fake.run(KV_SCRIPT, "--dry-run", "--recreate", "jarvis-session")
        assert result.returncode == 1
        assert "Would RECREATE" not in result.stdout
        assert "Would update KV jarvis-session" not in result.stdout
        assert "returned missing or invalid settings" in result.stderr

    def test_reason_is_reported(self, fake: FakeNats) -> None:
        fake.seed(_matching(**{"jarvis-session": {"stream_info": MALFORMED_INFO["storage-missing"]}}))
        result = fake.run(KV_SCRIPT, "--recreate", "jarvis-session")
        assert 'config.storage is null, expected "file" or "memory"' in result.stderr

    def test_complete_info_still_recreates(self, fake: FakeNats) -> None:
        # The same response with every field present is a real storage mismatch
        fake.seed(_matching(**{"jarvis-session": {
            "storage": "file", "messages": 2, "stream_info": _session_info(),
        }}))
        result = fake.run(KV_SCRIPT, "--recreate", "jarvis-session")
        assert result.returncode == 0, result.stderr
        assert "[RECREATE] KV jarvis-session — storage file -> memory" in result.stdout
        assert _settings(fake.buckets()["jarvis-session"]) == WANT["jarvis-session"]

    def test_absent_max_msg_size_means_unlimited(self, fake: FakeNats) -> None:
        # The CLI omits max_msg_size when 0, which the server treats as unlimited
        fake.seed(_matching(**{"jarvis-session": {"stream_info": _session_info(
            storage="memory", max_msg_size=_DROP)}}))
        result = fake.run(KV_SCRIPT, "--dry-run")
        assert result.returncode == 0, result.stderr
        assert "Would update KV jarvis-session: max_value_size -1 -> 131072" in result.stdout

    def test_invalid_info_on_confirm_is_an_error(self, fake: FakeNats) -> None:
        # The edit is made, but its re-read is partial: not confirmed as done
        fake.seed(_matching(**{"agent-status": {
            "max_value_size": -1,
            "stream_info_after_edit": {"config": {"name": "KV_agent-status"}},
        }}))
        result = fake.run(KV_SCRIPT)
        assert result.returncode == 1
        assert "[ERROR] KV agent-status — could not re-read valid bucket settings" in result.stderr
        assert "[UPDATE] KV agent-status" not in result.stdout


# =============================================================================
# provision-streams.sh no longer touches KV
# =============================================================================


class TestStreamsScriptLeavesKvAlone:
    def test_provision_streams_makes_no_kv_calls(self, fake: FakeNats) -> None:
        result = fake.run(STREAMS_SCRIPT)
        assert result.returncode == 0, result.stderr
        assert all(c[0] != "kv" for c in fake.calls()), fake.calls()
        assert fake.buckets() == {}
        assert "PIPELINE" in fake.state()["streams"]

    def test_provision_streams_leaves_existing_buckets_untouched(self, fake: FakeNats) -> None:
        fake.seed(_live_drifted())
        before = fake.buckets()
        fake.run(STREAMS_SCRIPT)
        assert fake.buckets() == before
        assert not any(c[2].startswith("KV_") for c in fake.calls() if len(c) > 2)

    def test_provision_streams_has_no_kv_code(self) -> None:
        text = STREAMS_SCRIPT.read_text(encoding="utf-8")
        assert "nats kv" not in text
        assert "kv_buckets" not in text
