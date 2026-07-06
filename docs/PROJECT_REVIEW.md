# Project Review & Improvement Plan

_Updated July 2026 — reflects current implementation state across Phases 1–10._

---

## Current Implementation Status

Phases 1–5 and 7–10 are implemented. The following components exist and are functional:

| Phase | Component | Status | Key gaps |
|-------|-----------|--------|----------|
| 1 | Repo scaffold, JSON schema, Pydantic models | ✅ Done | — |
| 2 | Staff onboarding React webapp (23 questions) | ✅ Done | Missing section progress persistence |
| 3 | Config generators (6 files per agent) | ✅ Done | No golden-file snapshot tests yet |
| 4 | `aios` CLI (planes + agents) | ✅ Done | `status` shows registry only, not live Docker state |
| 5 | Docker isolation, per-agent containers | ✅ Done | Dockerfile now runs non-root; schema validation at startup added |
| 6 | Admin dashboard (React app in `admin/` + `/api/v1/admin/agents*` endpoints) | ✅ Done | Agent list w/ live Docker state, heartbeats, logs, restart (July 2026) |
| 7 | Pulse ↔ agent-plane integration | ✅ Done | JWT now has explicit dev-mode guard; production JWKS path implemented |
| 7b | Central AI router | ✅ Done | Model updated to claude-sonnet-4-6; timing telemetry added |
| 8 | n8n workflow automation | ✅ Done | Webhook auth added; global error handler workflow added |
| 9 | Officer-specific modules (President, SecTreas, ExecSec + compliance calendar) | ✅ Done | Merged via PRs #19–#24; post-merge integration fixes applied July 2026 |
| 10 | Production hardening (PostgreSQL, Redis, rate limiting, backups, SSL) | ✅ Done | Merged via PR #23; async pg store (`db/pg_models.py`) not yet wired to endpoints |

### Post-merge integration fixes (July 2026)

The PR #19–#24 merge series left several integration breaks that have now been fixed:

- Duplicate `BoardMeeting` ORM model (Phase 9a `board.py` vs 9b `minutes.py`) crashed every model import — consolidated in `db/models/board.py`.
- `db/models.py` (Phase 10 async pg models) was shadowed by the `db/models/` package — renamed to `db/pg_models.py`.
- Phase 9b Alembic migration used revision `001` parallel to 9a's `001_phase9a` and re-created `board_meetings` — rechained as `002_phase9b`.
- Phase 9b routers (finance, minutes, scheduling) were never mounted in `app.py` — all endpoints 404'd.
- Check-in cross-agent ownership guard (scheduler-service exception) lost in the Phase 10 merge — restored.
- Context-cache invalidation on check-in used a glob that never matched the stored key — fixed with exact-key delete.
- Officer-module tables were never created at startup (`init_db()` only covered the core stack) — `create_all_tables()` now runs in the app lifespan.
- `aios planes` command group was never registered in the CLI entry point; an orphaned parallel Typer CLI (`provisioning/cli/commands/`) was removed.
- Orphaned parallel onboarding UI (`configGenerators.js`, `SummaryScreen.jsx`, `sections/`, `components/`) removed — `App.jsx` + `generators/` is the live path.
- `EXEC_SESSION_FERNET_KEY` is now required outside dev mode (fail-fast instead of ephemeral per-worker keys).
- CI pipeline added (`.github/workflows/ci.yml`): ruff + pytest + vitest + build.

### Roadmap items completed (July 2026)

- **P0 #1 / P1 #5** — Golden-file snapshot tests for all 6 generators across all 3 role classes (President / SecTreas / standard staff): `onboarding/src/generators/__tests__/snapshots.test.js`.
- **P0 #2** — `aios planes status` now reports live Docker container state (running/stopped/missing/unavailable) via the shared `provisioning/cli/docker_status.py` helper.
- **P1 #6** — Phase 6 admin dashboard: `GET /api/v1/admin/agents` (registry + container state + morning/evening heartbeats), `GET .../logs`, `POST .../restart` (ADMIN-only, registered agents only), with the React frontend in `admin/`.
- **P1 #8** — CI pipeline (now also covers the admin app).
- **P2 #11** — ADRs written: `docs/adr/001-docker-over-gcp-vms.md`, `002-ollama-primary-claude-fallback.md`, `003-agents-plane-pattern.md`.

Still open: **P1 #7** (`aios agents upgrade` rolling upgrade — the command exists; health-verify step still TODO), **P2 #9** (memory backup cron — `scripts/backup.sh` exists, cron/`aios planes backup` wiring TODO), **P2 #10** (observability baseline), production JWT validation against the CHCA Azure AD tenant, and the n8n workflow endpoint mismatches (need confirmation whether workflows target this API or a separate Pulse core service).

---

## Remaining Gaps — Prioritized

### P0 — Must fix before first production agent (Dave)

**1. Add golden-file snapshot tests for all 6 generators**
For each of `generateSOUL`, `generateUSER`, `generateIDENTITY`, `generateAGENTS`,
`generateHEARTBEAT`, `generateMEMORY`: create a fixture representing Dave's
onboarding responses, run the generator, and snapshot the output.
- Prevents silent template regressions
- Evidence: unit tests exist but no snapshot fixtures yet

**2. Harden `aios planes status` to show live Docker state**
Currently shows registry metadata only. Add `docker inspect` calls to report
real container state (running/stopped/missing) alongside registry data.

**3. Validate production JWT auth end-to-end**
`PULSE_DEV_MODE=true` is now explicit and logged with a warning; production JWKS
path is implemented. Before going live: unset `PULSE_DEV_MODE` in production `.env`
and validate token verification against the CHCA Azure AD tenant.

**4. Configure n8n Error Workflow**
Import `integrations/n8n/workflows/00-error-handler.json` and set it as the
global Error Workflow in n8n Settings → Workflows → Error Workflow. Then set
retry counts (3 retries, 60 s wait) on all schedule-triggered workflows (01–04).

### P1 — Must fix before rolling out to SecTreas + ExecSec

**5. Add role-specific snapshot fixtures**
SecTreas and ExecSec responses exercise different generator code paths. Add
fixtures for each role class (President, SecTreas/ExecSec, standard staff).

**6. Build admin dashboard (Phase 6)**
Minimum viable: list agents with Docker status + last heartbeat time. Without
this, failures are invisible during multi-agent rollout.

**7. Implement `aios agents upgrade` command**
Rolling upgrade: pull latest image → stop container → start with new image →
verify health → proceed to next agent. Required before any image update.

**8. Add CI pipeline**
No CI workflow exists. Add `.github/workflows/ci.yml` running:
- `pytest` for Python provisioning code and Pydantic models
- `vitest` for the onboarding generators
- `ruff` for Python linting

### P2 — Before production hardening (Phase 10)

**9. Implement memory backup cron**
Daily backup of `agents/*/memory/` volumes to a local encrypted archive.
`aios planes backup` command + cron schedule.

**10. Add observability baseline**
- Agent provisioning success/failure rate (CLI exit codes logged to structured file)
- Config generation latency (instrument generators for regression detection)
- n8n workflow success rate (available via n8n API, surface in admin dashboard)

**11. Architecture Decision Records (ADRs)**
- `docs/adr/001-docker-over-gcp-vms.md` — local Docker vs GCP VM-per-agent
- `docs/adr/002-ollama-primary-claude-fallback.md` — AI routing rationale
- `docs/adr/003-agents-plane-pattern.md` — why Agents Plane vs shared agent

---

## Immediate Next Actions (this week)

- [ ] Add snapshot fixtures to `onboarding/src/generators/__tests__/` for all 3 role classes
- [ ] Configure n8n error handler workflow and retry settings
- [ ] Unset `PULSE_DEV_MODE` in production `.env` and test JWKS verification end-to-end
- [ ] Begin Phase 6 admin dashboard — critical dependency for multi-agent rollout
- [ ] Add `.github/workflows/ci.yml`

---

## Execution Sequence (next 4 weeks)

1. **Week 1:** Snapshot tests + CI + n8n error handler configured
2. **Week 2:** Admin dashboard Phase 6 MVP (agent list + Docker status + heartbeat)
3. **Week 3:** `aios agents upgrade` + memory backup + production JWT validated
4. **Week 4:** Phase 9 officer modules for SecTreas + ExecSec, then P1 rollout
