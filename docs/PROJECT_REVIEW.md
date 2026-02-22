# Project Review & Improvement Plan

## Quick Assessment

The repository currently contains a detailed product/architecture memory document (`Claude.md`) but no implementation scaffold yet.

This is a strong starting point for vision alignment, but there are immediate gaps that will block execution if not addressed:

1. No runnable code skeleton for backend, frontend, provisioning, or integrations.
2. No defined schema for the onboarding output that produces the 6 configuration files.
3. No acceptance criteria per phase (so "done" is ambiguous).
4. No security baseline artifacts (threat model, secrets policy, tenancy test plan).
5. No CI workflow to enforce quality gates as development starts.

## Recommended Improvements (Prioritized)

## P0 — Start Building Infrastructure for Delivery

### 1) Add a minimal monorepo scaffold now
Create the documented top-level folders and placeholder modules so work can proceed in parallel:
- `onboarding/` (React)
- `provisioning/cli/` (Python)
- `admin/` (dashboard)
- `integrations/` (n8n, pulse, msgraph)
- `agents/` (generated agent output)

**Why:** Enables immediate task decomposition and reduces setup friction.

### 2) Define a canonical onboarding schema (`v1`)
Create a single source of truth for onboarding input and generated artifacts.
- Suggested file: `schemas/onboarding.v1.json`
- Include validation constraints and required/optional fields.
- Add a version field so future migrations are explicit.

**Why:** Prevents drift between UI form, generators, and provisioning CLI.

### 3) Write deterministic generators with snapshot tests
For each generated file (`SOUL`, `USER`, `IDENTITY`, `AGENTS`, `HEARTBEAT`, `MEMORY`):
- Build pure generation functions.
- Add snapshot fixtures using representative staff profiles.
- Enforce idempotent output.

**Why:** Configuration generation is core product logic and should be test-first.

### 4) Establish CI before feature work expands
At minimum:
- Lint + typecheck + unit tests.
- Conventional PR checks.
- Markdown linting for config templates.

**Why:** Quality gates are cheapest to introduce early.

## P1 — Reduce Risk in Multi-Tenant + Security Model

### 5) Add a concrete tenant isolation test matrix
Document and automate checks for:
- Cross-agent file access denial.
- Secrets boundary validation.
- Resource quota isolation.
- Log redaction behavior.

**Why:** Multi-tenant isolation is the system's highest-stakes technical promise.

### 6) Produce a threat model and control map
Create `docs/security/threat-model.md` with:
- Assets, trust boundaries, attack vectors.
- STRIDE-style threat table.
- Controls and validation approach.

**Why:** Security requirements in `Claude.md` are strong but currently non-operational.

### 7) Define memory lifecycle policy and retention controls
Document:
- What is retained, encrypted, summarized, or purged.
- Per-role retention exceptions.
- Human override and audit path.

**Why:** The "forget safely" principle needs enforceable lifecycle rules.

## P2 — Improve Product Operability

### 8) Add phase-level Definition of Done (DoD)
For each phase in `Claude.md`, include:
- Deliverables.
- Tests required.
- Demo scenario.
- Exit criteria.

**Why:** Turns roadmap from intent into executable milestones.

### 9) Add observability baseline from day one
Define minimal telemetry:
- Agent provisioning success rate.
- Config generation latency/error rate.
- Runtime health and heartbeat compliance.

**Why:** Operational visibility should not be postponed to production hardening.

### 10) Add architecture decision records (ADRs)
Start with:
- Why OpenClaw + orchestration layer approach.
- Why Ollama primary / Claude fallback.
- Why per-agent Docker isolation.

**Why:** Preserves rationale and reduces future design churn.

## Suggested 2-Week Execution Sequence

1. **Days 1-2:** Scaffold repo + CI + coding standards.
2. **Days 3-4:** Finalize onboarding schema `v1` + validation.
3. **Days 5-7:** Implement 6 config generators + snapshot tests.
4. **Days 8-9:** Build provisioning CLI skeleton (`aios agents create/list/validate`).
5. **Days 10-11:** Add isolation test matrix + local compose proof.
6. **Days 12-14:** Admin read-only status panel for provisioning + agent health.

## Immediate Next Actions

- [ ] Create `README.md` with setup and first-run instructions.
- [ ] Add `schemas/onboarding.v1.json` with 23-question mapping.
- [ ] Create `provisioning/cli/agents.py` with `validate-onboarding` command.
- [ ] Add `tests/generators/` with fixtures for all three role classes (President, SecTreas, ExecSec + standard staff).
- [ ] Add `.github/workflows/ci.yml` for lint/test checks.

---

If implemented in this order, the project can move from planning to a verifiable Phase 1-4 prototype quickly while preserving the privacy-first and multi-tenant guarantees.
