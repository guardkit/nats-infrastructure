#!/usr/bin/env python3
"""Offline stand-in for the nats CLI, used by the provisioning script tests.

Implements only the subset the provisioning scripts call — server check,
kv ls/add/edit/del, stream info/add/update — against a JSON state file, and
logs every invocation so tests can assert exactly which commands ran.
Anything else (e.g. `nats kv update <bucket> --history 5`, `nats kv info
--json`) fails the way the real CLI does.

Environment:
  FAKE_NATS_STATE   JSON state file: {"buckets": {...}, "streams": {...}}
  FAKE_NATS_LOG     file that receives one JSON argv list per invocation
  FAKE_NATS_FAIL    comma-separated verbs that fail, e.g. "kv edit,stream info"
  FAKE_NATS_EDIT_NOOP  if set, `kv edit` exits 0 without changing anything
"""

from __future__ import annotations

import json
import os
import re
import sys

BOOL_FLAGS = {"--json", "-j", "--names", "-n", "--force", "-f", "--defaults"}
ADD_FLAGS = {"--storage", "--history", "--max-value-size", "--ttl", "--replicas"}
EDIT_FLAGS = ADD_FLAGS - {"--storage"}


def fail(msg: str) -> None:
    print(f"nats: error: {msg}", file=sys.stderr)
    sys.exit(1)


def parse(argv: list[str]) -> tuple[list[str], dict[str, str]]:
    positional: list[str] = []
    flags: dict[str, str] = {}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg.startswith("-"):
            if "=" in arg:
                name, value = arg.split("=", 1)
                flags[name] = value
            elif arg in BOOL_FLAGS:
                flags[arg] = "true"
            else:
                if i + 1 >= len(argv):
                    fail(f"expected argument for flag '{arg}'")
                flags[arg] = argv[i + 1]
                i += 1
        else:
            positional.append(arg)
        i += 1
    return positional, flags


def to_bytes(value: str) -> int:
    m = re.fullmatch(r"(-?\d+)\s*([A-Za-z]*)", value)
    if not m:
        fail(f"invalid size {value!r}")
    mult = {"": 1, "B": 1, "KB": 1024, "K": 1024, "MB": 1024**2, "M": 1024**2}
    return int(m.group(1)) * mult[m.group(2).upper()]


def to_seconds(value: str) -> int:
    m = re.fullmatch(r"(\d+)([smhd])", value)
    if not m:
        fail(f"invalid duration {value!r}")
    return int(m.group(1)) * {"s": 1, "m": 60, "h": 3600, "d": 86400}[m.group(2)]


def apply_flags(bucket: dict, flags: dict[str, str], allowed: set[str]) -> None:
    for flag in flags:
        if flag.startswith("--") and flag not in allowed | {"--server", "--creds", "--timeout"}:
            fail(f"unknown long flag '{flag}'")
    if "--storage" in flags:
        bucket["storage"] = flags["--storage"]
    if "--history" in flags:
        bucket["history"] = int(flags["--history"])
    if "--max-value-size" in flags:
        bucket["max_value_size"] = to_bytes(flags["--max-value-size"])
    if "--ttl" in flags:
        bucket["ttl_s"] = to_seconds(flags["--ttl"])
    if "--replicas" in flags:
        bucket["replicas"] = int(flags["--replicas"])


def stream_json(name: str, b: dict) -> str:
    return json.dumps(
        {
            "config": {
                "name": name,
                "storage": b["storage"],
                "max_msgs_per_subject": b["history"],
                "max_msg_size": b["max_value_size"],
                "max_age": b["ttl_s"] * 1_000_000_000,
                "num_replicas": b["replicas"],
            },
            "state": {"messages": b.get("messages", 0)},
        }
    )


def main() -> None:
    argv = sys.argv[1:]
    with open(os.environ["FAKE_NATS_LOG"], "a", encoding="utf-8") as log:
        log.write(json.dumps(argv) + "\n")

    state_path = os.environ["FAKE_NATS_STATE"]
    with open(state_path, encoding="utf-8") as fh:
        state = json.load(fh)
    buckets = state.setdefault("buckets", {})
    streams = state.setdefault("streams", {})

    pos, flags = parse(argv)
    verb = " ".join(pos[:2])
    failing = {v.strip() for v in os.environ.get("FAKE_NATS_FAIL", "").split(",") if v.strip()}
    if verb in failing:
        fail(f"simulated failure of '{verb}'")

    if pos[:3] == ["server", "check", "connection"]:
        sys.exit(0)

    if verb == "kv ls" and len(pos) == 2:
        for name in sorted(buckets):
            print(name)
    elif verb == "kv add" and len(pos) == 3:
        if pos[2] in buckets:
            fail("bucket already exists")
        b = {"storage": "file", "history": 1, "max_value_size": -1,
             "ttl_s": 0, "replicas": 1, "messages": 0}
        apply_flags(b, flags, ADD_FLAGS)
        buckets[pos[2]] = b
    elif verb == "kv edit" and len(pos) == 3:
        if pos[2] not in buckets:
            fail("bucket not found")
        if not os.environ.get("FAKE_NATS_EDIT_NOOP"):
            apply_flags(buckets[pos[2]], flags, EDIT_FLAGS)
        else:
            apply_flags(dict(buckets[pos[2]]), flags, EDIT_FLAGS)
    elif verb == "kv del" and len(pos) == 3:
        if "--force" not in flags and "-f" not in flags:
            fail("would prompt for confirmation")
        if pos[2] not in buckets:
            fail("bucket not found")
        del buckets[pos[2]]
    elif verb == "stream info" and len(pos) == 3 and "--json" in flags:
        name = pos[2]
        if name.startswith("KV_") and name[3:] in buckets:
            print(stream_json(name, buckets[name[3:]]))
        elif name in streams:
            print(json.dumps({"config": {"name": name, **streams[name]}}))
        else:
            fail("stream not found")
    elif verb in ("stream add", "stream update") and len(pos) == 3:
        streams[pos[2]] = {"max_msgs": int(flags.get("--max-msgs", "-1")),
                           "num_replicas": int(flags.get("--replicas", "1"))}
    else:
        fail(f"unsupported command {argv!r}")

    with open(state_path, "w", encoding="utf-8") as fh:
        json.dump(state, fh)


if __name__ == "__main__":
    main()
