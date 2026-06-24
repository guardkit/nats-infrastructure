# forge → dedicated NATS user (2026-06-24)

## What changed & why

Previously the forge service (the `forge-prod` container running `forge serve`) connected to NATS
as **`rich`** — a human principal — via inline creds baked into an ad-hoc `docker run`
(`FORGE_NATS_URL=nats://rich:…@localhost:4222`). The forge **CLI** had no creds at all and fell
back to NoOp (lifecycle events weren't published from CLI runs).

forge now has its **own identity**: a dedicated **`forge`** user in the **APPMILLA** account, so its
credential can be rotated/revoked/audited independently of the humans, and the inline-creds-in-a-
`docker run` smell is gone.

## Broker side (this repo)

- `config/accounts/accounts.conf.template` — added a `forge` user to APPMILLA. **Now subject-scoped**
  (2026-06-24, least privilege): `pipeline.> runbook.> agents.> fleet.> $JS.> $KV.> _INBOX.>` for
  both publish and subscribe. Verified enforced (forge publishes `runbook.>` but is denied
  `notifications.>`). _Originally landed as full `>` because the entrypoint's blanket `envsubst`
  clobbered `$JS`/`$KV`; that is now fixed (below), so the scoped form works._
- `scripts/docker-entrypoint.sh` — **restricted `envsubst` to the five `*_PASSWORD` vars**
  (`envsubst '${RICH_NATS_PASSWORD} … ${FORGE_NATS_PASSWORD}' < … > …`) so `$JS`/`$KV` system
  subjects survive substitution. Requires an image rebuild (`docker compose build`). Note: the
  post-substitution safeguard greps **braced** `${VAR}`, so unbraced `$JS`/`$KV` pass; but a literal
  `${VAR}` in a template *comment* will now survive and trip it — keep template comments free of
  `${UPPERCASE}` tokens (the header comment was reworded for this).
- `.env` (gitignored) — added `FORGE_NATS_PASSWORD`.
- Apply: `docker compose up -d --force-recreate` (re-renders accounts; brief reconnect blip — all
  clients auto-reconnect; `rich`/`james`/`mark` unaffected). Validate first by rendering the
  template with `envsubst` and `nats-server -t -c <rendered>`.

## forge side

- **`~/.config/forge/nats.env`** (chmod 600, outside git/mounts) — single source of truth:
  `FORGE_NATS_URL=nats://forge:<pw>@127.0.0.1:4222`. **Inline-URL form** because the running
  `forge:latest` image predates TASK-FMDR-008 and only parses inline-URL creds (not
  `FORGE_NATS_USER`/`PASSWORD`).
- **`~/forge-prod/docker-compose.yml`** — the old ad-hoc `docker run` reconstructed as compose,
  reading the creds via `env_file`. Recreate: `docker compose -f ~/forge-prod/docker-compose.yml up -d`.
- **CLI** — `~/.bashrc` sources `nats.env` so `forge runbook run`/`forge queue` authenticate too.

## Verified

`curl -s 'http://127.0.0.1:8222/connz?auth=1'` shows `forge-prod` connected as **`forge`** (2 conns);
a CLI `forge runbook run` published all six runbook lifecycle events **in order** to the live broker.

## Rollback

Broker: `git checkout config/accounts/accounts.conf.template`, restore `.env`, `docker compose up -d
--force-recreate`. forge-prod: the prior container can be re-created from the original inline-`rich`
`docker run` (full runtime captured during migration).

## Follow-ups

1. ✅ **Rebuilt `forge:latest` from `main` (≥ 008)** (2026-06-24) — prod image is current; its CLI
   has 008. **But** `FORGE_NATS_USER/PASSWORD` support is only in `forge/cli/runbook.py`; the
   **`forge serve` daemon path doesn't read it**, so `nats.env` stays inline-URL. → see 1a.
2. ✅ **Restricted the entrypoint `envsubst`** to the `*_PASSWORD` vars and **subject-scoped the
   `forge` user** (2026-06-24, verified enforced).
3. **1a (NEW): teach `forge serve` to honour `FORGE_NATS_USER/PASSWORD`** (mirror the CLI's
   `_resolve_nats_auth` in the serve NATS connect path), then drop inline-URL from `nats.env`. Forge
   code change + image rebuild.
4. **Rotate the NATS passwords** (rich/james/mark/admin were exposed in a session transcript). `rich`
   is used by **`nats-core`** (4 conns) — coordinate that update or it will break.
