# Pull Request Review (Open PRs #1–#10)

> **Review type:** Triage-level — sequencing, dependency risk, and merge strategy.
> The repository checkout in this environment does not include PR branches or diffs;
> code-level findings require a follow-up deep-review pass on each branch.

---

## Executive Recommendation

Merge in dependency order and block late-phase integrations until core runtime
boundaries are stable:

| Merge order | PR | Title |
|-------------|-----|-------|
| 1 | #1 | Add AIOS/PULSE phase prompt index and cross-cutting rules |
| 2 | #2 | Phase 1 scaffold and foundations |
| 3 | #3 | Phase 2 onboarding React webapp |
| 4 | #5 | Phase 3a config generators |
| 5 | #4 | Phase 4 AIOS CLI |
| 6 | #6 | Phase 5 Docker isolation |
| 7 | #8 | Phase 7 plane ↔ Pulse integration |
| 8 | #9 | Phase 7b model router |
| 9 | #7 | Phase 8 n8n workflows |
| 10 | #10 | Project review + prioritized roadmap |

---

## PR-by-PR Review Notes

### #1 — Add AIOS/PULSE phase prompt index and cross-cutting rules

- **Assessment:** Good as an early merge if it is documentation-only and non-breaking.
- **Risks:** If wording is prescriptive but not reflected in implementation, this can
  become stale quickly.
- **Review focus:** Ensure terminology, phase names, and ownership boundaries match
  what later PRs actually implement.
- **Recommendation:** **Approve with minor doc edits.**

---

### #2 — Phase 1: repo scaffold, JSON schema, Pydantic models, example agent, README, .gitignore

- **Assessment:** Foundational — likely a hard dependency for almost everything else.
- **Risks:** Schema churn causes cascading breakage in phases 2, 3a, and CLI/runtime code.
- **Review focus:**
  - Backward-compatible schema evolution strategy.
  - Validation strictness and defaults in Pydantic models.
  - Clear separation between example assets and production code.
- **Recommendation:** **Approve after strict API/schema review.**

---

### #3 — feat(phase-2): build staff onboarding React webapp

- **Assessment:** High product value; depends on phase 1 schema contracts.
- **Risks:** UI may overfit current schema and break when generators/CLI evolve.
- **Review focus:**
  - Form field parity with generator inputs.
  - Client/server validation consistency.
  - Save/load draft behavior and required-field handling.
- **Recommendation:** **Approve after schema contract tests are in place.**

---

### #4 — Phase 4: Build aios CLI for agent plane management

- **Assessment:** Critical operational surface.
- **Risks:** If merged before container/runtime assumptions are finalized, command
  interfaces may churn.
- **Review focus:**
  - Idempotent commands (`create`, `plan`, `apply`, `status`).
  - Safe failure semantics and clear exit codes.
  - Config path conventions aligned with phase 3a outputs.
- **Recommendation:** **Conditional approve** — prefer after #5 unless the interface
  is fully abstracted from runtime details.

---

### #5 — Phase 3a: Wire up SOUL, USER, IDENTITY config file generators

- **Assessment:** Core personalization pipeline; should land before broad CLI automation.
- **Risks:** Template drift across six config files as remaining generators are added.
- **Review focus:**
  - Deterministic output and reproducibility.
  - Clear template ownership/versioning.
  - Validation hooks before file write.
- **Recommendation:** **Approve with strong golden-file tests.**

---

### #6 — Phase 5: Docker isolation and per-agent container setup

- **Assessment:** Security and tenancy boundary milestone.
- **Risks:** Over-permissive mounts, shared secrets, or weak network isolation.
- **Review focus:**
  - Volume and secret scoping per agent.
  - Resource limits and health checks.
  - Restart/upgrade behavior and orphan cleanup.
- **Recommendation:** **Deep review required; high priority.** Do not skip.

---

### #7 — Phase 8: Add n8n workflow definitions for agent automation

- **Assessment:** Valuable automation layer but should not precede stable runtime
  contracts.
- **Risks:** Encodes assumptions about events and payloads before integrations settle.
- **Review focus:**
  - Trigger/event schema versioning.
  - Retry and dead-letter strategy.
  - Secret handling in workflow nodes.
- **Recommendation:** **Hold until #8/#9 interfaces stabilize.**

---

### #8 — Phase 7: Agent plane ↔ Pulse integration

- **Assessment:** Core integration milestone; likely prerequisite to robust automation.
- **Risks:** Tight coupling between Pulse-specific APIs and plane orchestration internals.
- **Review focus:**
  - Contract boundaries (DTOs/adapters).
  - Auth/authz and tenant scoping.
  - Latency/error budget behavior.
- **Recommendation:** **High-priority merge after runtime base (#6) is stable.**

---

### #9 — Add central AI router for model routing by task type (Phase 7b)

- **Assessment:** Important architecture component for quality/cost control.
- **Risks:** Hardcoded routing logic and unobservable fallback behavior.
- **Review focus:**
  - Policy-driven routing configuration.
  - Telemetry and per-route success metrics.
  - Safe default/fallback model behavior (Ollama primary → Claude API fallback).
- **Recommendation:** **Approve after #8 unless router is strictly internal and decoupled.**

---

### #10 — Add project review and prioritized improvement roadmap

- **Assessment:** Useful synthesis PR; should reflect post-merge reality.
- **Risks:** Becomes outdated if merged before the technical PR sequence settles.
- **Review focus:**
  - Evidence-based prioritization (incidents, test gaps, delivery risk).
  - Explicit near-term ownership and milestones.
- **Recommendation:** **Merge last** (or continuously update before final merge).

---

## Cross-PR Blocking Checklist

Before merging #6–#9, verify these across PR boundaries:

- [ ] Stable schema/version strategy from #2 feeding #3, #5, and #4.
- [ ] End-to-end provisioning path: onboarding input → generated files → CLI
      orchestration → container runtime.
- [ ] Tenant isolation guarantees in filesystem, secrets, network, and logs.
- [ ] Observability baseline: structured logs, health probes, and traceable
      correlation IDs.
- [ ] Failure recovery path for partial provisioning and upgrade rollback.

---

## Suggested Review Labels

| Label | PRs |
|-------|-----|
| `foundational` | #1, #2 |
| `product-ui` | #3 |
| `config-pipeline` | #5 |
| `platform-runtime` | #4, #6 |
| `integration` | #8, #9 |
| `automation` | #7 |
| `planning` | #10 |

---

## Immediate Actions

- Start deep technical review on **#2, #5, #6, #8** now.
- Request revision/hold on **#7** until integration contracts (#8/#9) are explicit.
- Merge **#10** only after major implementation PRs are updated and reconciled.
