# ADR 001: Local Docker Containers per Agent, Not GCP VM-per-Agent

- **Status:** Accepted
- **Date:** 2026-07-06

## Context

The upstream OpenClaw Agents Plane proposal (issue #17299) recommends
VM-per-agent on GCP as its primary deployment model: each agent gets a VM
with OpenClaw pre-installed, a dedicated GCP service account, Secret Manager
secrets with IAM bindings, VPC/firewall network isolation, and IAP-tunneled
access scoped to the owner.

Our deployment context differs from the upstream assumptions in three ways:

1. **Data sensitivity is the dominant constraint.** CHCA (Connecticut Health
   Care Associates, District 1199NE, AFSCME) is a healthcare workers' union.
   Agents handle member lists, grievance details, disciplinary cases, dues
   accounts, and contract negotiation strategy. `Claude.md` (Privacy First,
   Hard Rules) makes local deployment a hard requirement: sensitive union
   data cannot go to GCP or any cloud. AI inference runs on Ollama on the
   local host specifically so this data never leaves the network.
2. **Scale is fixed and small.** There are exactly 8 staff agents
   (`Claude.md`, Staff Agent Roster). The upstream cost/complexity analysis
   puts VM-per-agent at ~$15–30/month per agent and positions it for
   "< 20 agents, high security"; at 8 agents that is ~$120–240/month of
   recurring cloud spend for isolation properties we can reproduce locally.
3. **Budget matters.** The union operates on a tight budget. Local Docker
   costs ~$0/month in infrastructure; the full GCP deployment is estimated
   at ~$90–110/month (`docs/gcp-migration-path.md`, Cost Estimates).

## Decision

Provision each of the 8 agents as an isolated Docker container on a local
host, implemented in Phase 5 (`prompts/phase-05-docker-isolation.md`) and
driven by the `aios` CLI (`provisioning/cli/planes.py`,
`provisioning/cli/agents.py`), which mirrors the upstream
`openclaw planes` command surface while substituting Docker for GCP VMs.

All five upstream security properties are implemented with Docker
equivalents (documented in `Claude.md`, Upstream Security Model):

| Upstream (GCP) | Our implementation (Docker) |
|----------------|------------------------------|
| Zero trust between agents | Separate Docker network per agent, `internal: true` blocks cross-agent traffic |
| SSH via IAP only | `docker exec` via CLI only; no shell exposed by default |
| Per-agent service accounts / Secret Manager | Per-agent `.env` files (dev); GCP Secret Manager with `chca-agents/{agent_id}/` prefixes in prod |
| Admin audit without secret access | Admin dashboard shows health/activity/config summaries; `.env` and memory contents never exposed via API |
| Network isolation | Bridge networks with `internal: true`; agents reach only Ollama and Pulse on the host |

Per-agent memory isolation uses separate filesystem paths
(`agents/{agent-id}/memory/`) mounted as isolated Docker volumes until
upstream LanceDB `agentId` scoping (issue #15325) ships.

GCP is retained as a documented **future migration path**, not a rejected
option: `docs/gcp-migration-path.md` specifies the triggers (remote access
needs, > 20 agents, availability or off-site DR requirements), an 8-step
migration procedure, and Terraform modules planned under
`provisioning/terraform/`. The `aios` CLI is deliberately backend-agnostic —
same commands, different backend — to keep that migration cheap. Even in
the GCP scenario, the recommendation is to keep Ollama on-premises reached
via VPN/IAP tunnel, preserving the privacy model.

## Consequences

### Positive

- Sensitive union data (member data, grievances, negotiation strategy)
  never leaves the local network; the privacy model is enforced by
  physical locality, not just policy.
- ~$0/month infrastructure cost versus ~$90–110/month on GCP.
- Containers on the host reach Ollama cleanly via `host.docker.internal`
  — no VPN or tunnel needed for local AI inference.
- Low operational complexity: no cloud IAM, billing, or VPC management
  for a 3-person officer rollout followed by 5 standard staff.
- We run ahead of upstream: issue #17299 has no assignees or linked PRs,
  and our Docker plane is a complete working implementation of the same
  concept rather than a dependency on it.

### Negative

- Isolation is "good" rather than "strongest" — container isolation is
  weaker than hardware VM isolation (upstream deployment-model table;
  see also OpenClaw issue #7575 on Sysbox for hardening options).
- Single physical host: no managed uptime, and maintenance windows take
  all 8 agents down. Backups are local-disk unless we adopt the partial
  Cloud Storage offsite path from `docs/gcp-migration-path.md`.
- No built-in remote access; staff working from home would need an IAP
  tunnel to the local server or a fuller migration.
- We own patching, monitoring, and backup of the host (addressed by
  Phase 10 hardening and P2 item #9, memory backup cron, in
  `docs/PROJECT_REVIEW.md`).

## Alternatives Considered

1. **GCP VM-per-agent (upstream recommendation).** Strongest isolation,
   ~$15–30/month per agent. Rejected: cloud residency of sensitive union
   data is unacceptable regardless of cost, and the cost is unjustified at
   8 agents. Kept as the documented migration path if remote access or
   scale demands it.
2. **Processes on a shared VM/host.** ~$2–5/month per agent, weak
   isolation. Rejected: upstream classifies it as dev/testing only, and it
   cannot satisfy the zero-trust-between-agents property (no agent may
   read another's config or memory).
3. **Kubernetes (GKE or local).** Rejected per Claude.md (Upstream Open
   Questions #3): with 8 agents, K8s adds complexity without benefit.
   Revisit only if the plane exceeds ~20 agents (e.g., other locals adopt
   the system).
4. **Cloud Run per agent.** Simpler than GKE and used in the migration
   doc, but shares the data-residency objection and cannot host Ollama
   (no GPU), which would force a tunnel back on-premises anyway.
