# ADR-001: Standalone Infrastructure Repo

**Date:** April 2026
**Status:** Accepted

## Context

NATS server configuration, Docker deployment, stream provisioning, and monitoring
could live in the jarvis repo, the guardkitfactory repo, or its own repo.

## Decision

Standalone `nats-infrastructure` repo. The NATS server is backbone middleware shared
by the entire fleet — coupling it to any single consumer creates a false dependency.

## Consequences

- Any agent repo can be built and tested independently (using local NATS or TestNatsBroker)
- Infrastructure changes (accounts, streams, monitoring) don't touch application code
- GB10 deployment is a single `docker compose up` from this repo
- Clear ownership: infrastructure config changes are reviewed separately from agent logic
