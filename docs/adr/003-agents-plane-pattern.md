# ADR 003: Agents Plane Pattern — One Isolated Agent per Staff Member, Not a Shared Agent

- **Status:** Accepted
- **Date:** 2026-07-06

## Context

We are deploying AI agents for the 8 staff members of CHCA (Connecticut
Health Care Associates, District 1199NE, AFSCME), a healthcare workers'
union, on top of OpenClaw. This repo is explicitly **not a fork of
OpenClaw** (`Claude.md`): OpenClaw is an infrastructure dependency, and we
build an orchestration and provisioning layer above it. Two architectural
questions had to be settled together:

1. **One shared agent or one agent per person?** A single shared agent
   would be simpler to run, but staff have conflicting confidentiality
   boundaries: the SecTreas handles dues, disbursements, and finance; the
   ExecSec drafts minutes; the President handles grievance intelligence
   and negotiation strategy. `Claude.md` Hard Rules encode separation-of-
   duties constraints (co-signatures on disbursements, SecTreas retaining
   minutes approval, executive-session material never recorded) that
   presume roles are distinct actors — a shared agent's memory would
   commingle exactly the data these rules keep apart. Privacy First
   requires that "no agent can read another's config or memory."
2. **Custom orchestration or ad-hoc per-agent setup?** Hand-configuring 8
   OpenClaw instances does not scale to the P0→P1→P2 rollout (Dave, then
   SecTreas + ExecSec, then 5 staff) and invites configuration drift.

Upstream OpenClaw issue #17299 proposes the "Agents Plane" pattern —
"OpenClaw for Teams" — an infrastructure layer provisioning isolated
agents (compute, identity, secrets, network, access, runtime) per team
member, with a `planes` CLI. As of Feb 2026 it has no assignees or linked
PRs; it is a design, not shipped code.

## Decision

Adopt the Agents Plane pattern: a plane of 8 isolated OpenClaw agents, one
per staff member, managed by our own orchestration layer rather than a
single shared agent or unmanaged per-person installs. Concretely (see the
architecture diagram in `Claude.md`):

- **Per-agent identity and personalization.** Each agent is generated from
  a 23-question onboarding form (`onboarding/`) into 6 config files —
  `SOUL.md`, `USER.md`, `IDENTITY.md`, `AGENTS.md`, `HEARTBEAT.md`,
  `MEMORY.md` — at `agents/{agent-id}/config/`, loaded by OpenClaw at
  container startup. `agent_id` is permanent (`{role-slug}-{name-slug}-
  {4char}`, `prompts/README.md` rule #7) and keys memory, volumes, logs.
- **Per-agent isolation.** Each agent runs in its own Docker container on
  its own `internal: true` network with its own `.env` secrets and memory
  volume at `agents/{agent-id}/memory/` (ADR 001; zero trust between
  agents per the upstream security model).
- **Shared orchestration layer.** The provisioning CLI
  (`provisioning/cli/planes.py`, `provisioning/cli/agents.py`) mirrors the
  upstream `openclaw planes create / add-agent / status / remove-agent /
  logs` surface. The admin dashboard (Phase 6), n8n hooks
  (`integrations/n8n/`), and Pulse bridge (`integrations/pulse/`) are
  plane-level shared services.
- **Role differentiation on a common base.** The three paid officers get
  role-specific capability modules (Phase 9: President grievance
  intelligence and legislative tracking; SecTreas finance and disbursement
  co-signature workflow; ExecSec minutes and scheduling); the other 5
  staff get the standard agent. The onboarding form and CLI handle all 8
  from day one (`prompts/README.md` rule #6). Inter-agent collaboration is
  explicit, defined per agent in `AGENTS.md`, not implicit shared state.

We implement the pattern ourselves rather than waiting on upstream: our
Docker-based plane is a complete working implementation of the #17299
concept ("running ahead of upstream, not behind it" per `Claude.md`); the
deployment substrate is decided separately in ADR 001.

## Consequences

### Positive

- Confidentiality boundaries between roles are structural: grievance
  detail, finance data, and minutes drafts live in different containers,
  networks, and memory volumes. A compromise or misbehavior of one agent
  is contained to one person's data.
- Separation-of-duties rules (co-signatures, minutes approval,
  executive-session handling) map onto distinct agent identities instead
  of being simulated inside one shared context.
- Deep personalization: SOUL/USER/HEARTBEAT files tune tone, overwhelm
  triggers, and check-in rhythm per person — impossible to reconcile in
  one shared agent serving 8 working styles.
- Uniform lifecycle operations: provisioning, status, logs, rolling
  upgrades (`aios agents upgrade`, P1 item #7 in `docs/PROJECT_REVIEW.md`),
  and daily memory backups apply plane-wide.
- Upstream alignment: if OpenClaw ships the Agents Plane, Thinking Clock
  (#17287, maps to `HEARTBEAT.md`), or LanceDB `agentId` memory scoping
  (#15325), we adopt them as backends without changing the pattern.

### Negative

- 8x the runtime footprint of a shared agent: 8 containers, config sets,
  and memory stores contend for one host (including Ollama capacity).
- Failures are per-agent and easy to miss without plane-level
  observability — the admin dashboard (Phase 6) is still unbuilt and is
  flagged in `docs/PROJECT_REVIEW.md` as a critical rollout dependency.
- Cross-agent workflows (e.g., ExecSec drafting minutes for SecTreas
  approval) require explicit integration through Pulse/n8n rather than
  free data sharing — deliberate friction, but friction.
- The orchestration layer (generators, CLI, dashboard, upgrade path) is
  code we own and maintain; #17299 is a design to track, not code to use.

## Alternatives Considered

1. **Single shared agent for all 8 staff.** Cheapest to run, but it
   commingles member data, finance, grievances, and negotiation strategy
   across role boundaries; it cannot enforce "no agent can read another's
   memory," represent separation of duties, or be tuned per person. Rejected.
2. **Fork OpenClaw and build multi-tenancy in.** Rejected in `Claude.md`:
   forking means carrying every upstream change; the orchestration-layer
   approach keeps OpenClaw a replaceable dependency and lets us adopt
   upstream multi-tenancy work (#17299, #15325, #10004) as it lands.
3. **Wait for the upstream Agents Plane implementation.** Rejected: #17299
   has no assignees or linked PRs, and CHCA's rollout cannot block on it.
   Building to the same CLI shape keeps later convergence cheap.
4. **Unmanaged per-person OpenClaw installs (no plane layer).** Rejected: 8
   hand-managed instances drift, with no uniform security posture, no
   plane-wide status/upgrade/backup story, and no admin audit surface.
