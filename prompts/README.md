# AIOS/PULSE — Phase Prompt Index
**How to use:** Read CLAUDE.md first, then paste the relevant phase prompt into Claude Code.

---

## Phase Map

| File | Phase | Description | Sessions | Depends On |
|------|-------|-------------|----------|------------|
| `phase-01-scaffold.md` | 1 | Repo structure, JSON schema, Pydantic models, example agent | 1 | Nothing |
| `phase-02-onboarding-form.md` | 2 | React onboarding webapp (23 questions → 6 config files) | 1-2 | Phase 1 |
| `phase-03a-generators-soul-user-identity.md` | 3a | SOUL, USER, IDENTITY generators | 1 | Phases 1+2 |
| `phase-03b-generators-agents-heartbeat-memory.md` | 3b | AGENTS, HEARTBEAT, MEMORY generators + ZIP finalization | 1 | Phase 3a |
| `phase-04-provisioning-cli.md` | 4 | `aios` CLI — planes, agents, config commands | 1-2 | Phases 1+3 |
| `phase-05-docker-isolation.md` | 5 | Dockerfile, docker-compose generator, .env generator, isolation checks | 1 | Phase 4 |
| `phase-06-admin-dashboard.md` | 6 | Admin plane dashboard — health, logs, restart | 1 | Phases 4+5 |
| `phase-07-pulse-integration.md` | 7 | Pulse context API, check-in endpoints, sidebar, alerts | 1-2 | Phases 4-6 |
| `phase-08-n8n-hooks.md` | 8 | 6 n8n workflows — context builder, grievance monitor, etc. | 1-2 | Phase 7 |
| `phase-09a-officer-president.md` | 9a | President: grievance intel, research, legislative, board | 2 | Phases 7+8 |
| `phase-09b-officer-sectreasurer-execsec.md` | 9b | SecTreas: finance/disbursements. ExecSec: minutes/scheduling | 1-2 | Phase 9a |
| `phase-09c-standard-staff-compliance-calendar.md` | 9c | Standard staff profile, shared compliance calendar, smoke test | 1 | Phases 9a+9b |
| `phase-10-prod-hardening.md` | 10 | PostgreSQL, Redis, backups, monitoring, SSL, security, runbook | 2-3 | All phases |

**Total estimated sessions: 16-22**

---

## Key Cross-Cutting Rules (repeat these in every session if needed)

1. **No red colors.** Status indicators: green ✓ / yellow ~ / orange ! / dim white ○
2. **No sensitive data to external APIs.** All AI inference uses Ollama (localhost:11434) only
3. **Co-signatures are non-negotiable.** Two different officers required for every disbursement — enforce at API level, not just UI
4. **Executive session = no recording.** Events with exec session keywords get title/body/attendees sanitized before reaching any agent
5. **Admin sees metrics, never secrets.** Config show and admin dashboard must never expose pronouns, overwhelm_triggers, never_do instructions, .env values, or memory contents
6. **8 agents, not 3.** Don't hardcode for 3. The system must handle all 8 from day one
7. **agent_id is permanent.** Format: {role-slug}-{name-slug}-{4char}. Never change it after creation — it's the key for memory, volumes, and logs

---

## Hard Constraints from CLAUDE.md (quick reference)

- Executive Board meetings: no recording, pre-meeting prep only
- Dave chairs meetings (EVP bylaw amendment in progress — agent reflects actual practice)
- SecTreas retains minutes approval despite ExecSec drafting
- Disbursements always require co-signatures — no single-officer approval
- Member data, grievance details, negotiation strategy → Ollama only, never external APIs
- Volunteer officers (EVP, VP) do not get agents
