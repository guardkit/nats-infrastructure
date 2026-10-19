"""The dashboard's answer identity, proved on a real broker (19 October 2026).

Design: factory-dashboard docs/architecture/approvals-from-the-dashboard-2026-10-19.md,
"Tests" ("The bus permission") and "What changes where".

What this proves, with a REAL nats-server and the PRODUCTION render path:

1. The accounts file is rendered by ``scripts/docker-entrypoint.sh`` itself — the
   script that is built into the broker image — from the real
   ``config/accounts/accounts.conf.template``, with nine generated throwaway
   passwords. The only thing replaced is the final ``exec nats-server``: a shim
   earlier on PATH records that it was reached and exits, so the script runs
   every line it runs in production and stops where the server would start.
2. A real ``nats-server`` (the one on PATH, same 2.11 line as the image) is then
   started from that rendered file on a free loopback port, and:
     * ``dashboard_approve`` may publish on ``agents.approval.forge.merge-FEAT-X.response``,
       and a full-access subscriber really receives it;
     * it is refused on ``agents.approval.forge.merge-FEAT-X`` (no ``.response``),
       ``pipeline.build-queued.x`` and ``jarvis.x`` — refused by the server, and
       nothing reaches a subscriber;
     * it can subscribe to NOTHING: ``agents.>``, ``_INBOX.>``, ``_INBOX.x`` and ``>`` are
       all refused, and another client's reply on ``_INBOX.x`` never reaches it
       (``_INBOX.>`` would be every client's replies — the 19 October review);
     * a wrong password is refused, so the auth path really checks passwords.
3. The entrypoint refuses to start, and never reaches the server, when
   ``DASHBOARD_APPROVE_NATS_PASSWORD`` is missing.

The client side speaks the NATS text protocol over a plain socket (stdlib only),
so a refusal is the server's own ``-ERR 'Permissions Violation …'`` line, read
before the ``PONG`` that follows it — never inferred from a client library's
asynchronous error callback.

This is NOT an ``integration`` test in this repository's sense (those talk to the
live broker on 4222). It starts its own throwaway server on loopback, touches no
live service, and is skipped — saying why — where nats-server or envsubst is not
installed. No password is ever printed: assertion messages name users and
subjects only.
"""

from __future__ import annotations

import json
import os
import secrets
import shutil
import socket
import subprocess
import time
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENTRYPOINT = PROJECT_ROOT / "scripts" / "docker-entrypoint.sh"
TEMPLATE = PROJECT_ROOT / "config" / "accounts" / "accounts.conf.template"

#: Every password the template names. The entrypoint's own envsubst list must
#: carry each of them (checked statically below as well as by the render).
ACCOUNTS = (
    "ADMIN",
    "RICH",
    "JAMES",
    "MARK",
    "FORGE",
    "FLEET_MEMORY",
    "GUARDKIT",
    "JARVIS",
    "DASHBOARD_APPROVE",
)

ANSWER_SUBJECT = "agents.approval.forge.merge-FEAT-X.response"
REFUSED_PUBLISH_SUBJECTS = (
    "agents.approval.forge.merge-FEAT-X",
    "pipeline.build-queued.x",
    "jarvis.x",
)

NATS_SERVER = shutil.which("nats-server")
ENVSUBST = shutil.which("envsubst")

pytestmark = pytest.mark.skipif(
    NATS_SERVER is None or ENVSUBST is None,
    reason=(
        "SKIPPED: the dashboard_approve bus-permission proof needs a local "
        "nats-server and envsubst on PATH "
        f"(nats-server: {'found' if NATS_SERVER else 'missing'}, "
        f"envsubst: {'found' if ENVSUBST else 'missing'}). "
        "Nothing was proved about the broker's permissions on this machine."
    ),
)


# ---------------------------------------------------------------------------
# Rendering through the production entrypoint
# ---------------------------------------------------------------------------


def _sandbox(root: Path) -> dict[str, Path]:
    """The /etc/nats layout the entrypoint expects, under ``root``, with the
    REAL template, and a nats-server shim that only records it was reached."""
    config_dir = root / "nats"
    template_dir = config_dir / "config" / "accounts"
    template_dir.mkdir(parents=True)
    shutil.copyfile(TEMPLATE, template_dir / TEMPLATE.name)
    bin_dir = root / "bin"
    bin_dir.mkdir()
    marker = root / "server-was-reached"
    shim = bin_dir / "nats-server"
    shim.write_text(f'#!/bin/sh\n: > "{marker}"\nexit 0\n', encoding="utf-8")
    shim.chmod(0o755)
    return {
        "config_dir": config_dir,
        "bin_dir": bin_dir,
        "marker": marker,
        "log_dir": root / "log",
        "rendered": config_dir / "accounts" / "accounts.conf",
    }


def _run_entrypoint(box: dict[str, Path], passwords: dict[str, str]):
    env = {
        "PATH": f"{box['bin_dir']}:{os.environ.get('PATH', '/usr/bin:/bin')}",
        "NATS_CONFIG_DIR": str(box["config_dir"]),
        "NATS_LOG_DIR": str(box["log_dir"]),
    }
    env.update({f"{name}_NATS_PASSWORD": value for name, value in passwords.items()})
    return subprocess.run(
        ["/bin/sh", str(ENTRYPOINT), "-c", "/etc/nats/nats-server.conf"],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


def _generated_passwords() -> dict[str, str]:
    return {name: secrets.token_hex(16) for name in ACCOUNTS}


# ---------------------------------------------------------------------------
# A minimal NATS text-protocol client (stdlib only)
# ---------------------------------------------------------------------------


class Conn:
    """One NATS connection. ``roundtrip`` sends commands followed by PING and
    returns every server line up to the PONG, so a ``-ERR`` the server sends
    for those commands is always seen before this returns."""

    def __init__(self, port: int, user: str, password: str) -> None:
        self.sock = socket.create_connection(("127.0.0.1", port), timeout=5)
        self.buf = b""
        info = self._line()
        assert info.startswith("INFO "), "the broker did not greet with INFO"
        connect = {
            "verbose": False,
            "pedantic": False,
            "user": user,
            "pass": password,
            "name": f"permission-test-{user}",
            "lang": "python-socket",
            "version": "0",
            "protocol": 1,
            "echo": True,
        }
        self.sock.sendall(f"CONNECT {json.dumps(connect)}\r\n".encode())
        self.greeting = self.roundtrip("")

    def _line(self) -> str:
        while b"\r\n" not in self.buf:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("the broker closed the connection")
            self.buf += chunk
        line, self.buf = self.buf.split(b"\r\n", 1)
        return line.decode()

    def roundtrip(self, commands: str) -> list[str]:
        self.sock.sendall(f"{commands}PING\r\n".encode())
        lines: list[str] = []
        while True:
            try:
                line = self._line()
            except ConnectionError:
                lines.append("<closed>")
                return lines
            if line == "PONG":
                return lines
            if line == "PING":
                self.sock.sendall(b"PONG\r\n")
                continue
            if line.startswith("MSG "):
                size = int(line.split()[-1])
                while len(self.buf) < size + 2:
                    self.buf += self.sock.recv(65536)
                payload, self.buf = self.buf[:size], self.buf[size + 2 :]
                lines.append(f"{line} {payload.decode()}")
                continue
            lines.append(line)
            if line.startswith("-ERR") and "Authorization Violation" in line:
                return lines

    def publish(self, subject: str, payload: str = "probe") -> list[str]:
        return self.roundtrip(f"PUB {subject} {len(payload)}\r\n{payload}\r\n")

    def subscribe(self, subject: str, sid: int) -> list[str]:
        return self.roundtrip(f"SUB {subject} {sid}\r\n")

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass


def _errors(lines: list[str]) -> list[str]:
    return [line for line in lines if line.startswith("-ERR")]


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ---------------------------------------------------------------------------
# Fixtures: one render, one throwaway broker for the module
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def rendered(tmp_path_factory: pytest.TempPathFactory) -> dict:
    root = tmp_path_factory.mktemp("render")
    box = _sandbox(root)
    generated = _generated_passwords()
    result = _run_entrypoint(box, generated)
    assert result.returncode == 0, (
        "the production entrypoint refused to render with every password set: "
        + result.stderr[-2000:]
    )
    assert box["marker"].exists(), "the entrypoint never reached its exec of nats-server"
    return {"box": box, "passwords": generated, "root": root}


@pytest.fixture(scope="module")
def broker(rendered: dict):
    """A real nats-server from the RENDERED accounts file, on loopback only,
    with the same `include "accounts/accounts.conf"` the production config uses."""
    box, root = rendered["box"], rendered["root"]
    port = _free_port()
    store = root / "jetstream"
    conf = box["config_dir"] / "test-server.conf"
    conf.write_text(
        "\n".join(
            [
                'server_name: "dashboard-approve-permission-test"',
                'host: "127.0.0.1"',
                f"port: {port}",
                f'jetstream {{ store_dir: "{store}", max_mem: 16MB, max_file: 64MB }}',
                'include "accounts/accounts.conf"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    log = (root / "nats-server.log").open("w")
    proc = subprocess.Popen(
        [NATS_SERVER, "-c", str(conf)], stdout=log, stderr=subprocess.STDOUT
    )
    try:
        deadline = time.monotonic() + 15
        while True:
            if proc.poll() is not None:
                pytest.fail(
                    "nats-server exited at start from the rendered config; its log: "
                    + (root / "nats-server.log").read_text()[-2000:]
                )
            try:
                socket.create_connection(("127.0.0.1", port), timeout=1).close()
                break
            except OSError:
                if time.monotonic() > deadline:
                    pytest.fail("nats-server did not open its port within 15 s")
                time.sleep(0.2)
        yield {"port": port, "passwords": rendered["passwords"]}
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)
        log.close()


@pytest.fixture
def dashboard(broker: dict):
    conn = Conn(broker["port"], "dashboard_approve", broker["passwords"]["DASHBOARD_APPROVE"])
    yield conn
    conn.close()


@pytest.fixture
def watcher(broker: dict):
    """A full-access subscriber (rich), to see what really got through."""
    conn = Conn(broker["port"], "rich", broker["passwords"]["RICH"])
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# The render
# ---------------------------------------------------------------------------


def test_the_entrypoint_substitutes_the_new_password_by_name() -> None:
    text = ENTRYPOINT.read_text(encoding="utf-8")
    envsubst_line = next(
        line for line in text.splitlines() if line.strip().startswith("envsubst '")
    )
    for name in ACCOUNTS:
        assert f"${{{name}_NATS_PASSWORD}}" in envsubst_line, (
            f"{name}_NATS_PASSWORD is not in the entrypoint's fixed envsubst list"
        )


def test_the_rendered_file_carries_the_user_with_its_password(rendered: dict) -> None:
    text = rendered["box"]["rendered"].read_text(encoding="utf-8")
    assert "${" not in text, "an unresolved ${VAR} survived the render"
    assert 'user: "dashboard_approve"' in text
    assert f'password: "{rendered["passwords"]["DASHBOARD_APPROVE"]}"' in text, (
        "the dashboard_approve password was not substituted into the rendered file"
    )
    # The JetStream system subjects other users rely on must survive envsubst.
    assert '"$JS.>"' in text and '"$KV.>"' in text


# ---------------------------------------------------------------------------
# The broker
# ---------------------------------------------------------------------------


def test_it_connects(dashboard: Conn) -> None:
    assert _errors(dashboard.greeting) == [], "dashboard_approve could not connect"


def test_a_wrong_password_is_refused(broker: dict) -> None:
    conn = Conn(broker["port"], "dashboard_approve", "definitely-wrong-password-probe")
    try:
        assert any("Authorization Violation" in line for line in conn.greeting), (
            "a wrong dashboard_approve password was accepted"
        )
    finally:
        conn.close()


def test_it_may_publish_a_card_answer_and_it_arrives(dashboard: Conn, watcher: Conn) -> None:
    assert _errors(watcher.subscribe(ANSWER_SUBJECT, 1)) == []
    said = dashboard.publish(ANSWER_SUBJECT, "answer")
    assert _errors(said) == [], f"publishing on {ANSWER_SUBJECT} was refused"
    got = watcher.roundtrip("")
    deadline = time.monotonic() + 5
    while not any(line.startswith(f"MSG {ANSWER_SUBJECT} ") for line in got):
        assert time.monotonic() < deadline, f"nothing arrived on {ANSWER_SUBJECT}"
        time.sleep(0.1)
        got += watcher.roundtrip("")
    assert any(line.endswith(" answer") for line in got)


@pytest.mark.parametrize("subject", REFUSED_PUBLISH_SUBJECTS)
def test_it_is_refused_anywhere_else(dashboard: Conn, watcher: Conn, subject: str) -> None:
    assert _errors(watcher.subscribe(subject, 7)) == []
    said = dashboard.publish(subject, "should-not-arrive")
    refusals = [line for line in _errors(said) if "Permissions Violation for Publish" in line]
    assert refusals and subject in refusals[0], (
        f"dashboard_approve was not refused on {subject}"
    )
    time.sleep(0.3)
    got = watcher.roundtrip("")
    assert not any(line.startswith("MSG ") for line in got), (
        f"a refused publish on {subject} still reached a subscriber"
    )


@pytest.mark.parametrize("subject", ("agents.>", "_INBOX.>", "_INBOX.x", ">"))
def test_it_cannot_subscribe_to_anything(dashboard: Conn, subject: str) -> None:
    said = dashboard.subscribe(subject, 2)
    refusals = [line for line in _errors(said) if "Permissions Violation for Subscription" in line]
    assert refusals and subject in refusals[0], (
        f"dashboard_approve was allowed to subscribe to {subject}"
    )


def test_another_clients_reply_never_reaches_it(dashboard: Conn, watcher: Conn) -> None:
    """The over-grant the review found: with ``_INBOX.>`` this user read other
    clients' private replies. Now the subscription is refused and nothing arrives."""
    said = dashboard.subscribe("_INBOX.>", 4)
    assert any("Permissions Violation for Subscription" in line for line in _errors(said))
    assert _errors(watcher.publish("_INBOX.x", "someone-elses-reply")) == []
    time.sleep(0.3)
    got = dashboard.roundtrip("")
    assert not any(line.startswith("MSG ") for line in got), (
        "another client's reply reached dashboard_approve"
    )


# ---------------------------------------------------------------------------
# The refusal to start
# ---------------------------------------------------------------------------


def test_the_entrypoint_refuses_to_start_without_the_new_password(tmp_path: Path) -> None:
    box = _sandbox(tmp_path)
    generated = _generated_passwords()
    del generated["DASHBOARD_APPROVE"]
    result = _run_entrypoint(box, generated)
    assert result.returncode != 0, (
        "the entrypoint started with DASHBOARD_APPROVE_NATS_PASSWORD missing"
    )
    assert not box["marker"].exists(), "the entrypoint reached nats-server anyway"
    assert "Empty password value" in result.stderr, result.stderr[-1000:]
    assert (
        "DASHBOARD_APPROVE_NATS_PASSWORD is missing from the broker's environment"
        in result.stderr
    ), result.stderr[-1000:]
    named = [line for line in result.stderr.splitlines() if " is missing from the broker" in line]
    assert len(named) == 1, "the refusal named more than the one missing password"
