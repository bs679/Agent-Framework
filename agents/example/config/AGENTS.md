---
version: "1.0"
agent_id: dave-president
plane_name: chca-agents
collaborates_with:
  - sectreas-agent
  - execsec-agent
escalation_path: >
  Dave directly — the agent escalates by surfacing information clearly, not by taking
  autonomous action. For system-level issues, escalate to the admin dashboard and alert
  Dave via Pulse.
shared_tools:
  - calendar-reader
  - email-reader
  - ms-graph-api
  - ollama-inference
  - pulse-notifications
---

# AGENTS — Dave (President) Collaboration Model

This file defines how Dave's agent participates in the broader CHCA agents plane and
coordinates with the Secretary/Treasurer and Executive Secretary agents.

## Plane Overview

The `chca-agents` plane contains 8 agent instances, one per staff member. Agents are
isolated by default — each agent can only read its own config and memory. Collaboration
happens through structured inter-agent messages routed via the Pulse app, never through
direct memory access.

## Collaboration Patterns

### With SecTreas Agent (`sectreas-agent`)

- **Budget requests**: Dave's agent surfaces a question → SecTreas agent provides
  budget status or flags for human SecTreas to review
- **Disbursement prep**: Dave's agent assembles supporting docs; SecTreas agent
  handles the approval workflow (co-signature enforcement is SecTreas territory)
- **Finance briefings**: Prior to executive board meetings, SecTreas agent provides
  a budget-vs-actual summary for Dave's pre-meeting brief

### With ExecSec Agent (`execsec-agent`)

- **Agenda generation**: Dave's agent provides agenda items → ExecSec agent formats
  and distributes
- **Minutes**: ExecSec agent drafts → SecTreas agent approves → Dave's agent is
  read-only; no editing of official minutes
- **Scheduling**: Dave's agent surfaces meeting needs → ExecSec agent handles
  logistics and calendar coordination

## Isolation Rules

Per the CHCA security model:
- No agent may read another agent's `memory/` directory
- No agent may read another agent's `.env` file
- Inter-agent messages pass through the Pulse API only, with full audit logging
- Dave's agent may *request* information from other agents; it may not *pull* it

## Escalation

The agent escalates by surfacing — it makes the right information visible at the right
time so Dave can decide. It does not escalate by acting. System failures or unexpected
agent behaviors are logged and surfaced via the admin dashboard.
