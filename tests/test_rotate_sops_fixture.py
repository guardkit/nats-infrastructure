"""Runs scripts/test-rotate-sops-fixture.sh from the pytest suite.

The fixture derives the $KV.<bucket>.> probe-capture filters from the KV
definitions. When KV buckets moved out of streams/stream-definitions.json into
kv/kv-definitions.json, the fixture still parsed the old file, derived zero KV
filters and failed — and nothing in the pytest suite ran it. These tests close
that gap.

The fixture is offline by construction: a synthetic secrets root in a temp dir,
and docker/nats/systemctl/ssh shims that fail and are audited as never invoked.
It needs sops, age-keygen and openssl, so the run is skipped where they are
missing; the static check always runs.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURE = PROJECT_ROOT / "scripts" / "test-rotate-sops-fixture.sh"
KV_DEFS_FILE = PROJECT_ROOT / "kv" / "kv-definitions.json"


def test_fixture_derives_kv_filters_from_kv_definitions() -> None:
    text = FIXTURE.read_text(encoding="utf-8")
    assert 'KV_DEFS="${SCRIPT_DIR}/../kv/kv-definitions.json"' in text
    body = re.search(r"kv_filters\(\) \{(.*?)\n\}", text, re.S)
    assert body is not None
    assert "${KV_DEFS}" in body.group(1)
    assert "${STREAM_DEFS}" not in body.group(1)
    buckets = json.loads(KV_DEFS_FILE.read_text(encoding="utf-8"))["kv_buckets"]
    assert len(buckets) >= 4, "the fixture requires at least four $KV filters"


@pytest.mark.skipif(
    any(shutil.which(t) is None for t in ("sops", "age-keygen", "openssl")),
    reason="the rotation fixture needs sops, age-keygen and openssl",
)
def test_rotate_sops_fixture_passes() -> None:
    result = subprocess.run(
        ["bash", str(FIXTURE)],
        capture_output=True, text=True, timeout=300,
    )
    out = result.stdout + result.stderr
    assert result.returncode == 0, out[-4000:]
    assert re.search(r"\(15\) parsed 1[3-9] stream \+ KV subject filters", out), out[-4000:]
    assert re.search(r"\(15\) the implicit KV_<bucket> streams are in the filter set \([4-9] ", out)
    assert re.search(r"RESULTS: \d+ passed, 0 failed", out), out[-4000:]
