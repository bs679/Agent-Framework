# AIOS/PULSE — OpenClaw Multi-Tenant Agent System

This repo builds a multi-tenant AI agent deployment system on top of OpenClaw, purpose-built for CHCA (Connecticut Health Care Associates), District 1199NE, AFSCME — a labor union representing healthcare workers at Bradley Memorial Hospital, Norwalk Hospital, Waterbury Hospital, and school districts in Regions 12, 13, and 17. The system provisions isolated OpenClaw agents for each staff member, personalized via an onboarding form, generating six configuration files that define each agent's behavior, memory, and identity. This is an orchestration and provisioning layer built *on top of* OpenClaw — not a fork — following the [Agents Plane design pattern](https://github.com/openclaw/openclaw/issues/17299).

---

## Prerequisites

- Python 3.11+
- Docker (for per-agent container isolation)
- Node 18+
- [OpenClaw](https://github.com/openclaw/openclaw) (self-hosted)
- [Ollama](https://ollama.ai) (local inference — keeps sensitive union data off the cloud)

---

## Quick Start

```bash
git clone <this-repo> && cd Agent-Framework
pip install -r provisioning/requirements.txt
python -c "from provisioning.cli.types import AgentConfig; print('OK')"
```

---

## Phase Prompts

Work through these in order. Each prompt is a self-contained Claude Code session.

| Phase | File | Description |
|-------|------|-------------|
| 1 | [phase-01-scaffold.md](prompts/phase-01-scaffold.md) | Repo scaffold + base config schema |
| 2 | [phase-02-onboarding-form.md](prompts/phase-02-onboarding-form.md) | Staff onboarding form (React webapp) |
| 3 | [phase-03-config-generators.md](prompts/phase-03-config-generators.md) | Config file generators (6 files per agent) |
| 4 | [phase-04-provisioning-cli.md](prompts/phase-04-provisioning-cli.md) | Provisioning CLI (`aios planes` commands) |
| 5 | [phase-05-docker-isolation.md](prompts/phase-05-docker-isolation.md) | Docker isolation + per-agent containers |
| 6 | [phase-06-admin-dashboard.md](prompts/phase-06-admin-dashboard.md) | Admin dashboard |
| 7 | [phase-07-pulse-integration.md](prompts/phase-07-pulse-integration.md) | Pulse app integration |
| 8 | [phase-08-n8n-hooks.md](prompts/phase-08-n8n-hooks.md) | n8n workflow hooks |
| 9 | [phase-09-officer-modules.md](prompts/phase-09-officer-modules.md) | Officer-specific capability modules |
| 10 | [phase-10-prod-hardening.md](prompts/phase-10-prod-hardening.md) | Production hardening (GCP, certs, monitoring) |

---

## Reference

- Upstream Agents Plane proposal: https://github.com/openclaw/openclaw/issues/17299
- Full project context: [Claude.md](Claude.md)
