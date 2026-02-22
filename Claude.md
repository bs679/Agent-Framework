# AIOS/PULSE — OpenClaw Multi-Tenant Agent System
## Claude Code Project Memory

> Read this file at the start of every session. It is the single source of truth for this project.

---

## What This Project Is

This repo builds a **multi-tenant AI agent deployment system** on top of OpenClaw, purpose-built for CHCA (Connecticut Health Care Associates), District 1199NE, AFSCME — a labor union representing healthcare workers at Bradley Memorial Hospital, Norwalk Hospital, Waterbury Hospital, and school districts in Regions 12, 13, and 17.

The system provisions isolated OpenClaw agents for each staff member. Each agent is personalized via an onboarding form and generates six configuration files that define its behavior, memory, and identity. Agents integrate with the Pulse app (the main organizational interface) and the broader AIOS personal operating system.

**This is NOT a fork of OpenClaw.** We are building an orchestration and provisioning layer *on top of* OpenClaw, treating it as an infrastructure dependency. We follow the Agents Plane design pattern proposed in OpenClaw issue #17299.

---

## Staff Agent Roster (8 total)

All 8 staff members get agents. The three paid officers get role-specific capability modules (Phase 9). The remaining 5 staff get the standard agent with the full onboarding form but without officer-specific tooling.

| Person | Role | Agent Type | Priority |
|--------|------|-----------|----------|
| Dave (you) | President | Officer — full capability modules | P0 |
| Secretary/Treasurer | Finance, dues, disbursements | Officer — finance modules | P1 |
| Executive Secretary | Minutes, scheduling, correspondence | Officer — admin modules | P1 |
| Staff member 4 | TBD | Standard | P2 |
| Staff member 5 | TBD | Standard | P2 |
| Staff member 6 | TBD | Standard | P2 |
| Staff member 7 | TBD | Standard | P2 |
| Staff member 8 | TBD | Standard | P2 |

Volunteer officers (EVP, VP) do NOT get agents — they have day jobs and are not staff.

**Rollout order:** Dave first (P0), then SecTreas + ExecSec (P1), then remaining 5 staff once the system is proven stable (P2). The onboarding form and provisioning CLI must handle all 8 from day one — don't hardcode for 3.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                         AGENTS PLANE (8 agents)                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │  Dave    │  │ SecTreas │  │ ExecSec  │  │ Staff 4  │  · · ·  │
│  │ (Officer)│  │ (Officer)│  │ (Officer)│  │(Standard)│         │
│  │          │  │          │  │          │  │          │         │
│  │ SOUL.md  │  │ SOUL.md  │  │ SOUL.md  │  │ SOUL.md  │         │
│  │ USER.md  │  │ USER.md  │  │ USER.md  │  │ USER.md  │         │
│  │IDENTITY  │  │IDENTITY  │  │IDENTITY  │  │IDENTITY  │         │
│  │AGENTS.md │  │AGENTS.md │  │AGENTS.md │  │AGENTS.md │         │
│  │HEARTBEAT │  │HEARTBEAT │  │HEARTBEAT │  │HEARTBEAT │         │
│  │MEMORY.md │  │MEMORY.md │  │MEMORY.md │  │MEMORY.md │         │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘         │
│                                                                   │
│   Shared: Provisioning CLI, Admin Dashboard, n8n hooks            │
└──────────────────────────────────────────────────────────────────┘
           │                    │
           ▼                    ▼
    ┌────────────┐      ┌────────────────┐
    │  OpenClaw  │      │   Pulse App    │
    │  Runtime   │      │  (FastAPI +    │
    │  (Docker   │      │   React/Tauri) │
    │  per agent)│      └────────────────┘
    └────────────┘               │
           │                     ▼
           └────────────▶ ┌────────────────┐
                          │  MS Graph API  │
                          │  Ollama (local)│
                          │  n8n workflows │
                          └────────────────┘
```

---

## Agent Configuration Files (6 per agent)

Each agent is configured by 6 markdown files generated from the onboarding form:

| File | Purpose |
|------|---------|
| `SOUL.md` | Core personality, values, communication style |
| `USER.md` | The human this agent serves — preferences, context, working style |
| `IDENTITY.md` | Agent's name, avatar persona, role definition |
| `AGENTS.md` | How this agent collaborates with other agents in the plane |
| `HEARTBEAT.md` | Proactive check-in schedule, reflection triggers, energy patterns |
| `MEMORY.md` | Long-term memory schema, what to remember, what to forget |

These files live at `agents/{agent-id}/config/` and are loaded by OpenClaw at container startup.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent Runtime | OpenClaw (open source, self-hosted) |
| Provisioning | Python CLI + Docker Compose (local), Terraform/GCP (prod) |
| Isolation | Docker containers per agent |
| Secrets | Per-agent `.env` files (dev), GCP Secret Manager (prod) |
| Backend | FastAPI (Pulse app — already ~85% complete) |
| Frontend | React 19 + Vite + TailwindCSS 4 + Tauri 2 |
| Database | SQLite (dev) → PostgreSQL + pgvector (prod) |
| AI | Ollama (local, primary) + Claude API (fallback) |
| Automation | n8n (workflow orchestration) |
| Auth | Azure AD + JWT |

---

## Design Principles

### Terminal Calm
All interfaces follow the Terminal Calm philosophy:
- Dark backgrounds, no decorative elements
- Gentle, non-judgmental language
- Traffic light status: green/yellow/orange (NEVER red)
- Progressive disclosure — show info only when relevant
- ADHD-friendly: reduce cognitive load, surface what matters when it matters

### Privacy First
- Ollama runs locally — sensitive union data never leaves the network
- Per-agent isolation — no agent can read another's config or memory
- Admin sees metrics/logs, never secret values or memory contents
- All agent memory encrypted at rest

### Forget Safely
> "The goal isn't to remember everything. It's to forget safely — knowing the system will surface what matters, when it matters."

---

## Repository Structure

```
openclaw-aios/
├── CLAUDE.md                        # ← You are here. Read first.
├── README.md
├── prompts/                         # Claude Code phase prompts
│   ├── phase-01-scaffold.md
│   ├── phase-02-onboarding-form.md
│   ├── phase-03-config-generators.md
│   ├── phase-04-provisioning-cli.md
│   ├── phase-05-docker-isolation.md
│   ├── phase-06-admin-dashboard.md
│   ├── phase-07-pulse-integration.md
│   ├── phase-08-n8n-hooks.md
│   ├── phase-09-officer-modules.md
│   └── phase-10-prod-hardening.md
├── agents/                          # Per-agent config + memory
│   └── {agent-id}/
│       ├── config/
│       │   ├── SOUL.md
│       │   ├── USER.md
│       │   ├── IDENTITY.md
│       │   ├── AGENTS.md
│       │   ├── HEARTBEAT.md
│       │   └── MEMORY.md
│       └── memory/                  # Runtime memory store
├── provisioning/                    # CLI tooling
│   ├── cli/
│   │   ├── planes.py                # `aios planes` commands
│   │   └── agents.py                # `aios agents` commands
│   └── terraform/                   # GCP infrastructure (Phase 10)
├── onboarding/                      # Staff onboarding webapp
│   ├── src/
│   │   ├── components/
│   │   ├── generators/              # Config file generators
│   │   └── App.jsx
│   └── public/
├── admin/                           # Admin dashboard
│   └── src/
├── integrations/
│   ├── n8n/                         # Workflow definitions
│   ├── pulse/                       # Pulse app bridge
│   └── msgraph/                     # MS Graph helpers
└── docs/
    ├── agents-plane-design.md
    ├── security-model.md
    └── officer-modules.md
```

---

## Phase Status (update this as you go)

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Repo scaffold + base config schema | 🔲 Not started |
| 2 | Staff onboarding form (React webapp) | ✅ Complete |
| 3 | Config file generators (6 files per agent) | 🔲 Not started |
| 4 | Provisioning CLI (`aios planes` commands) | 🔲 Not started |
| 5 | Docker isolation + per-agent containers | ✅ Complete |
| 6 | Admin dashboard | 🔲 Not started |
| 7 | Pulse app integration | 🔲 Not started |
| 8 | n8n workflow hooks | 🔲 Not started |
| 9 | Officer-specific modules | 🔲 Not started |
| 10 | Production hardening (GCP, certs, monitoring) | 🔲 Not started |

---

## The Onboarding Form (23 questions, 7 sections)

The onboarding form is a React webapp that generates all 6 config files. Sections:

1. **About You** — name, role, pronouns
2. **Your Work Style** — energy patterns, focus preferences, overwhelm triggers
3. **Communication** — tone, format, delivery preferences
4. **Your Agent** — name (optional — agent self-selects if blank), personality
5. **Meetings** — prep timing, note capture style
6. **Information** — how to deliver bad news, preferred formats
7. **Context** — current time sinks (seeds initial agent memory)

Key design note: agent naming is optional. If staff skip it, the agent picks its own name during first boot. This aligns with OpenClaw's self-directed agent philosophy.

---

## Officer Module Capabilities

### Dave (President)
- Research: wage studies, private equity analysis, FOIA requests
- Legislative tracking: bills, hearings, advocacy calendar
- Grievance intelligence: multi-site tracking, deadlines, outcome patterns
- Contract negotiation: proposal drafting, wage costing, comparables research
- Executive board: agenda generation, compliance calendar, bylaw tracking
- Meeting intelligence: pre-meeting briefings from calendar + email context

### Secretary/Treasurer
- Finance dashboard: dues revenue, budget vs actual, vendor tracking
- Disbursement workflow: co-signature enforcement (never bypass)
- Audit trail: all financial actions logged with timestamps
- Dues delinquency alerts: proactive surfacing, not reactive searching

### Executive Secretary
- Minutes workflow: template generation → draft → SecTreas approval
- Scheduling: meeting coordination, room/calendar management
- Correspondence: letter drafting, member communications
- Document management: filing, version control, retrieval

### Hard Rules (non-negotiable)
- Executive Board meetings are in **executive session** — no recording. Pre-meeting prep only.
- Dave **chairs meetings** (EVP bylaw assignment is being amended — agent reflects actual practice)
- SecTreas **retains minutes approval** despite delegating drafting to ExecSec
- Disbursements **always require co-signatures** — no agent may bypass this workflow
- Sensitive data (member lists, grievance details, negotiation strategy) stays on **Ollama only**, never sent to external APIs

---

## Agents Plane Architecture (from OpenClaw issue #17299)

This section documents the upstream Agents Plane proposal in full and records our deliberate design decisions relative to it. Claude Code must understand both what the proposal says AND how we've adapted it for CHCA's local deployment context.

### What the Agents Plane Proposes

The Agents Plane (issue #17299, opened Feb 15 2026, not yet implemented upstream) is an infrastructure layer for deploying isolated OpenClaw agents for team members. Each agent gets its own compute, identity, secrets, network isolation, and access controls. The proposal describes it as "OpenClaw for Teams."

**What gets provisioned per agent (upstream vision):**

| Resource | Details |
|----------|---------|
| Compute | VM (or container) with OpenClaw pre-installed |
| Identity | Dedicated GCP service account with minimal permissions |
| Secrets | Secret Manager prefixed secrets + IAM bindings |
| Network | VPC subnet or firewall rules for network isolation |
| Access | IAP tunnel scoped to the owner only (OS Login) |
| Channels | WhatsApp/Telegram/Signal connection (agent-specific) |
| Runtime | Thinking Clock + heartbeat pre-configured |

**Upstream CLI pattern (what we're modeling our CLI after):**
```bash
openclaw planes create --name "acme-agents" --project gcp-project-id --region us-east4
openclaw planes add-agent --plane acme-agents --name alice --owner alice@acme.com --vm-type e2-small
openclaw planes status
openclaw planes remove-agent --plane acme-agents --name alice
openclaw planes logs --plane acme-agents --name bob
```

Our `aios` CLI mirrors this pattern exactly, substituting Docker for GCP VMs.

### Upstream Security Model (we implement all of this)

The issue specifies five security properties. We implement all five — adapted for local Docker rather than GCP:

| Security Property | Upstream (GCP) | Our Implementation (Docker) |
|-------------------|---------------|----------------------------|
| Zero trust between agents | No agent can access another's VM, secrets, or network | Separate Docker networks per agent; `internal: true` prevents cross-agent traffic |
| SSH via IAP only | No SSH keys on disk, all access audited | `docker exec` access only via CLI; no shell exposed by default |
| Per-agent service accounts | Each SA can ONLY access its own Secret Manager secrets | Per-agent `.env` files; prod uses GCP Secret Manager with `chca-agents/{agent_id}/` prefix scoping |
| Admin audit without secret access | Separation of duties: admin sees metrics/logs, not secret values | Admin dashboard shows health/activity/config summaries; `.env` contents never exposed via API |
| Network isolation | Agents cannot reach each other's ports; egress controlled per policy | Docker bridge network with `internal: true`; agents reach only Ollama and Pulse on host |

### Deployment Model Decision

The upstream proposal compares three models. We chose deliberately:

| Model | Isolation | Cost/agent | Ops Complexity | Best For |
|-------|-----------|-----------|----------------|---------|
| VM-per-agent | Strongest | ~$15-30/mo | Low | < 20 agents, high security |
| **Container on Docker** ← us | Good | ~$0 (local) | Low | Self-hosted, privacy-first |
| Process on shared VM | Weak | ~$2-5/mo | Low | Dev/testing only |

**Why we chose Docker containers (not upstream's recommended VM-per-agent):**
- We have 8 agents, not 20+ — VM-per-agent overhead isn't justified at this scale
- Sensitive union data cannot go to GCP or any cloud — local deployment is a hard requirement, not a cost decision
- Ollama runs on the host machine — Docker containers with `host.docker.internal` access is the cleanest pattern
- Zero ongoing cloud cost matters for a union operating on a tight budget

**Future path:** If CHCA ever needs to deploy agents remotely (e.g., SecTreas working from home needs full agent access), the migration path is GCP VM-per-agent following the upstream Phase 1 spec. The `aios` CLI is designed to make this migration straightforward — same commands, different backend.

### The Thinking Clock (upstream issue #17287)

The upstream proposal references the "Agent Thinking Clock" — a periodic reflection cycle where each agent independently processes its recent activity, surfaces patterns, and prepares context. This is the upstream equivalent of our HEARTBEAT.md config.

**How this maps to our implementation:**
- `HEARTBEAT.md` defines when the agent checks in and what triggers proactive outreach
- The morning/evening check-in rhythm IS the Thinking Clock for our use case
- When OpenClaw implements the Thinking Clock natively (#17287), our HEARTBEAT.md should wire into it rather than running a separate scheduler

**Watch this issue:** When #17287 ships, Phase 8 (n8n workflows) may be partially replaceable by native OpenClaw Thinking Clock functionality for the daily context building workflows.

### Per-Agent Memory Isolation (upstream issue #15325)

The upstream memory isolation PR adds `agentId` scoping to LanceDB (OpenClaw's memory backend). Until this ships, our implementation uses separate filesystem paths per agent (`agents/{id}/memory/`) mounted as isolated Docker volumes. When #15325 merges:
- Migration path: export each agent's memory volume, import into LanceDB with correct `agentId` scope
- The MEMORY.md config schema should remain compatible — it describes policy, not storage implementation

### Upstream Open Questions — Our Answers

The issue lists 7 open questions. Here are our decisions so Claude Code doesn't invent its own answers:

1. **IaC tooling — Terraform or gcloud CLI?**
   Our answer: Terraform in Phase 10, pure Python/Docker SDK for Phases 1-9. We want portability if we ever move to AWS (AFSCME has relationships with multiple cloud providers).

2. **Multi-cloud — how tightly couple to GCP?**
   Our answer: Abstract the secrets backend behind a `SecretsProvider` interface. Dev uses `.env` files; prod uses GCP Secret Manager. AWS Secrets Manager support should be addable without changing agent code.

3. **K8s vs VMs — GKE from day one?**
   Our answer: No K8s. We have 8 agents. If we ever exceed 20 agents (possible if other locals adopt this system), revisit. Keep it simple for now.

4. **Billing/cost tracking — GCP labels or built-in tracker?**
   Our answer: Not relevant for local Docker deployment. If we migrate to GCP, use GCP labels per agent with `plane=chca-agents` and `agent_id={id}`.

5. **Channel provisioning — how to automate WhatsApp/Telegram per agent?**
   Our answer: Not in scope. Agents communicate through Pulse (web/desktop app) and MS Teams/email. No WhatsApp/Telegram.

6. **Agent updates — rolling upgrades?**
   Our answer: `aios agents upgrade --plane chca-agents` should pull latest OpenClaw image, stop each container, start with new image, verify health before moving to next. Implement in Phase 10.

7. **State & backup — snapshots, memory export/import?**
   Our answer: Daily backup of `agents/*/memory/` volumes via cron script (Phase 10). Memory export/import for migration is a Phase 10 stretch goal.

### Upstream Phase Relationship

The Agents Plane feature has its own 4-phase upstream roadmap. Our project phases map to it like this:

| Upstream Phase | Upstream Scope | Our Equivalent |
|---------------|---------------|----------------|
| Phase 1 | `planes create` + `add-agent` with VM-per-agent on GCP | Our Phases 1, 4, 5 (Docker instead of GCP VMs) |
| Phase 2 | Admin dashboard, cost tracking, agent health monitoring | Our Phase 6 |
| Phase 3 | K8s backend, multi-cloud support | Not in scope |
| Phase 4 | Self-service portal for team members, channel auto-provisioning | Our Phase 2 (onboarding form) |

**Important:** The upstream Agents Plane has no assignees and no linked PRs as of Feb 21, 2026 — it has not started implementation. Our Docker-based approach is a complete, working implementation of the same concept rather than a dependency on upstream work. We are running ahead of upstream, not behind it.

If upstream ships Phase 1 before we reach production, evaluate whether to migrate to their GCP provisioning or keep our local Docker approach. The local approach wins unless there's a specific need for remote access or scale.

---

## External References

- OpenClaw repo: https://github.com/openclaw/openclaw
- Agents Plane proposal: https://github.com/openclaw/openclaw/issues/17299
- GCP Secret Manager integration: https://github.com/openclaw/openclaw/pull/16663
- Per-agent memory isolation (LanceDB agentId scoping): https://github.com/openclaw/openclaw/issues/15325
- Sysbox Docker isolation: https://github.com/openclaw/openclaw/issues/7575
- Agent Thinking Clock: https://github.com/openclaw/openclaw/issues/17287
- Multi-agent per-org isolation prerequisites: https://github.com/openclaw/openclaw/issues/10004
- Pulse app spec: see project file `Current_state_of_Pulse_app_development_`

---

## Session Startup Checklist

1. Read this file (CLAUDE.md) fully
2. Check Phase Status table — identify current phase
3. Read the corresponding phase prompt from `prompts/`
4. Do not modify CLAUDE.md unless explicitly instructed
5. Ask Dave which phase to work on if it's unclear

---

*Last updated: February 2026*
