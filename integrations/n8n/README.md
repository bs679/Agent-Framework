# n8n Workflow Integrations — AIOS/PULSE Phase 8

Workflow automation for the CHCA agent system. All 6 workflows run on a self-hosted n8n instance. All AI inference goes through **Ollama (localhost:11434)** — no sensitive data leaves the local network.

## Prerequisites

- n8n self-hosted instance (Docker or npm)
- Ollama running locally with `llama3.1:8b` model pulled
- Pulse API running and accessible
- MS Graph OAuth2 app registered in Azure AD (for calendar access)
- MS Teams incoming webhook configured (for urgent alerts)

## Quick Start

### 1. Pull the Ollama model

```bash
ollama pull llama3.1:8b
```

### 2. Configure n8n environment variables

Set these in your n8n instance (Settings → Environment Variables, or via `N8N_` env vars):

| Variable | Example Value | Description |
|----------|--------------|-------------|
| `PULSE_API_BASE_URL` | `http://localhost:8000` | Pulse app base URL |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API base URL |
| `MS_TEAMS_WEBHOOK_URL` | `https://outlook.office.com/webhook/...` | Teams incoming webhook |
| `N8N_WEBHOOK_SECRET` | `$(openssl rand -hex 32)` | Shared secret callers must send as `X-Webhook-Secret` header |

### 3. Set up credentials in n8n

Create the following credentials in the n8n UI (Settings → Credentials):

**MS Graph OAuth2** (`microsoftGraphOAuth2`)
- Name: `MS Graph OAuth2`
- Client ID: from your Azure AD app registration
- Client Secret: from your Azure AD app registration
- Tenant ID: your Azure AD tenant
- Scope: `Calendars.Read Mail.Read User.Read`

**Pulse API Token** (`httpHeaderAuth`)
- Name: `Pulse API Token`
- Header Name: `Authorization`
- Header Value: `Bearer <your-pulse-api-token>`

### 4. Import workflows

Import each JSON file from `workflows/` into n8n:

```
n8n UI → Workflows → Import from File
```

Or via CLI:

```bash
# If using n8n CLI
n8n import:workflow --input=workflows/01-daily-context-builder.json
n8n import:workflow --input=workflows/02-grievance-deadline-monitor.json
n8n import:workflow --input=workflows/03-legislative-calendar-tracker.json
n8n import:workflow --input=workflows/04-weekly-report-aggregator.json
n8n import:workflow --input=workflows/05-email-thread-intelligence.json
n8n import:workflow --input=workflows/06-new-member-orientation.json
```

### 5. Activate workflows

After import, each workflow is **inactive** by default. Review each one, verify credential bindings, then toggle active.

## Workflow Reference

### 01 — Daily Context Builder
- **Trigger:** Schedule — 6:45 AM daily
- **Purpose:** Builds morning context for agents 15 min before check-in
- **Flow:** Fetches calendar (MS Graph) + tasks + email summary from Pulse → posts unified context → pings each agent's /health endpoint
- **Credentials used:** MS Graph OAuth2, Pulse API Token

### 02 — Grievance Deadline Monitor
- **Trigger:** Schedule — 8:00 AM daily
- **Purpose:** Alerts on grievances due within 7 days; urgent Teams alerts for 48h deadlines
- **Flow:** Fetches open grievances → filters by due date → dedup (skip if already alerted today) → posts alert to agent check-in → urgent ones also go to MS Teams
- **Credentials used:** Pulse API Token, MS Teams Webhook URL
- **Static data:** Tracks which cases have been alerted today to avoid duplicates

### 03 — Legislative Calendar Tracker
- **Trigger:** Schedule — Monday 7:00 AM weekly
- **Purpose:** Scrapes CT General Assembly for hearings relevant to healthcare labor
- **Flow:** Fetches CGA page → filters by keywords (staffing ratios, collective bargaining, SEBAC, 1199, AFSCME, etc.) → sends to Ollama for relevance scoring → creates Pulse tasks assigned to Dave
- **Credentials used:** Pulse API Token, Ollama Base URL
- **AI:** Ollama `llama3.1:8b` — summarizes and rates hearing relevance

### 04 — Weekly Report Aggregator
- **Trigger:** Schedule — Friday 4:00 PM
- **Purpose:** Generates a weekly staff activity summary for Dave
- **Flow:** Fetches week's report data → sends to Ollama for summarization → posts as draft report → notifies Dave's agent
- **Credentials used:** Pulse API Token, Ollama Base URL
- **AI:** Ollama `llama3.1:8b` — summarizes weekly activity in <200 words

### 05 — Email Thread Intelligence
- **Trigger:** Webhook — called by Pulse when an email is flagged for processing
- **Webhook path:** `/webhook/email-thread-intelligence`
- **Payload:** `{email_id, subject, thread_length, sender, owner_agent}`
- **Purpose:** Summarizes email threads and suggests next actions
- **Flow:** Validates payload → fetches full thread from Pulse → sends to Ollama for summary → returns summary + suggested action to the owning agent
- **Credentials used:** Pulse API Token, Ollama Base URL
- **AI:** Ollama `llama3.1:8b` — summarizes thread in <150 words
- **SECURITY:** Email content is sent to Ollama (local) ONLY. Never to any external API.

### 06 — New Member Orientation Trigger
- **Trigger:** Webhook — called when a new member is added to Pulse
- **Webhook path:** `/webhook/new-member-orientation`
- **Payload:** `{member_name, facility, bargaining_unit, hire_date}`
- **Purpose:** Creates onboarding checklist tasks and schedules follow-up
- **Flow:** Validates payload → creates 8 orientation tasks assigned to ExecSec agent → schedules 30-day check-in task for Dave
- **Credentials used:** Pulse API Token
- **No AI used** — purely task creation

## Testing Each Workflow

### Schedule-triggered workflows (01, 02, 03, 04)

1. Import the workflow
2. Open it in the n8n editor
3. Click "Execute Workflow" to run manually
4. Check execution log for errors
5. Verify data appears in Pulse

### Webhook-triggered workflows (05, 06)

Test with curl:

```bash
# Workflow 05 — Email Thread Intelligence
curl -X POST http://localhost:5678/webhook/email-thread-intelligence \
  -H "Content-Type: application/json" \
  -d '{
    "email_id": "test-001",
    "subject": "Grievance Step 2 — Waterbury Hospital",
    "thread_length": 5,
    "sender": "hr@waterbury.org",
    "owner_agent": "dave"
  }'

# Workflow 06 — New Member Orientation
curl -X POST http://localhost:5678/webhook/new-member-orientation \
  -H "Content-Type: application/json" \
  -d '{
    "member_name": "Jane Smith",
    "facility": "Bradley Memorial Hospital",
    "bargaining_unit": "RN",
    "hire_date": "2026-03-01"
  }'
```

## Security Notes

- **All AI inference goes to Ollama (localhost:11434).** No workflow sends sensitive data to external APIs.
- Credential values are never stored in workflow JSON files — they use n8n credential references.
- The `credentials-template.json` file contains empty strings only — it documents the required credential structure.
- Grievance details, member info, email content, and financial data stay local.
- MS Teams alerts contain only plain-text deadline summaries — no case details beyond case ID and facility.

## Credential Reference Map

| Credential Name | n8n Type | Used By Workflows |
|----------------|----------|-------------------|
| MS Graph OAuth2 | `microsoftGraphOAuth2` | 01 |
| Pulse API Token | `httpHeaderAuth` | 01, 02, 03, 04, 05, 06 |
| Ollama Base URL | environment variable | 03, 04, 05 |
| MS Teams Webhook URL | environment variable | 02 |

## Error Handling & Retry Strategy

### Global Error Handler (workflow 00)

Import `00-error-handler.json` first, then go to **Settings → Workflows → Error Workflow** and select it.
All other workflows will route unhandled errors here. The handler creates a high-priority Pulse task
visible in the Dave agent sidebar — no sensitive execution data is included in the task.

### Retry configuration (schedule-triggered workflows)

In the n8n UI, for each schedule-triggered workflow (01–04):
1. Open the workflow → Settings (gear icon)
2. Set **Retry on Fail** → `3`
3. Set **Retry Wait Time** → `60` seconds

This gives failed API calls three chances before the error handler fires.

### Webhook authentication (workflows 05, 06)

Callers must include the header:
```
X-Webhook-Secret: <value of N8N_WEBHOOK_SECRET env var>
```
Requests without a valid secret return a thrown error and are not processed.
Generate the secret with: `openssl rand -hex 32`

### Dead-letter audit

Errors create Pulse tasks tagged `n8n-error`. Review these weekly and clear resolved ones.
The metadata field on each task contains: `workflow_name`, `execution_id`, `error_message`, `timestamp`.

## File Structure

```
integrations/n8n/
├── README.md                          ← This file
├── credentials-template.json          ← Credential structure (no values)
└── workflows/
    ├── 00-error-handler.json          ← Global dead-letter handler (import first)
    ├── 01-daily-context-builder.json
    ├── 02-grievance-deadline-monitor.json
    ├── 03-legislative-calendar-tracker.json
    ├── 04-weekly-report-aggregator.json
    ├── 05-email-thread-intelligence.json  ← Requires X-Webhook-Secret header
    └── 06-new-member-orientation.json     ← Requires X-Webhook-Secret header
```
