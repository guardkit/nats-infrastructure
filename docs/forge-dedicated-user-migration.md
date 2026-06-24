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

- `config/accounts/accounts.conf.template` — added a `forge` user to APPMILLA with full `>` pub/sub
  (same scope as `rich`/`james`; the **account** is the privilege boundary). Subject-level scoping
  (`pipeline.>`/`runbook.>`/`agents.>`/`fleet.>` + `$JS.API.>`/`$KV.>`) was attempted but **the
  entrypoint's blanket `envsubst` clobbers `$JS`/`$KV`** (treats them as shell vars → empty →
  `nats-server` rejects `".API.>"`). Proper scoping needs `envsubst` restricted to the `*_PASSWORD`
  vars (e.g. `envsubst '${RICH_NATS_PASSWORD} … ${FORGE_NATS_PASSWORD}'`) **and an image rebuild** —
  left as a future hardening.
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

1. **Rebuild `forge:latest` from `main` (≥ TASK-FMDR-008)** so the prod image gains env-var auth
   (`FORGE_NATS_USER/PASSWORD`), inline-cred log redaction, and the no-reconnect-spin fix. Then move
   `nats.env` to the `FORGE_NATS_USER` + `FORGE_NATS_PASSWORD` form.
2. **Rotate the NATS passwords** (rich/james/mark/admin were exposed in a session transcript). `rich`
   is used by **`nats-core`** (4 conns) — coordinate that update or it will break.
3. **Restrict the entrypoint `envsubst`** to the `*_PASSWORD` vars → enables subject-scoped users.
