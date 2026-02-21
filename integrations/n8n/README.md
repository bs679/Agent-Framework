# n8n Workflow Integrations — AIOS/Pulse Phase 8

Six n8n workflow definitions that automate recurring tasks for CHCA staff agents.

**Security rule:** All AI inference routes to Ollama (`localhost:11434`). No workflow
sends sensitive data (member info, grievance details, email content, financial data)
to any external API.

---

## Workflows

| # | File | Trigger | AI? | Description |
|---|------|---------|-----|-------------|
| 1 | `01-daily-context-builder.json` | Schedule 6:45 AM daily | No | Fetches calendar, tasks, email summary; builds daily context; pings agent health |
| 2 | `02-grievance-deadline-monitor.json` | Schedule 8:00 AM daily | No | Checks open grievances due within 7 days; dedup alerts; Teams webhook for <48h |
| 3 | `03-legislative-calendar-tracker.json` | Schedule Monday 7:00 AM | Ollama | Scrapes CT General Assembly hearings; filters by labor keywords; Ollama summary; creates Pulse tasks |
| 4 | `04-weekly-report-aggregator.json` | Schedule Friday 4:00 PM | Ollama | Aggregates weekly check-ins; Ollama summary; posts draft report for Dave's review |
| 5 | `05-email-thread-intelligence.json` | Webhook (from Pulse) | Ollama | Summarizes flagged email threads; returns summary + suggested action to agent |
| 6 | `06-new-member-orientation.json` | Webhook (from Pulse) | No | Creates orientation checklist tasks; assigns to ExecSec; schedules 30-day check-in for Dave |

---

## Prerequisites

- **n8n** running (self-hosted, Docker or npm)
- **Ollama** running on `localhost:11434` with `llama3.1:8b` model pulled
- **Pulse API** running and accessible
- **MS Graph** Azure AD app registration (for calendar access)
- **MS Teams** incoming webhook connector (for urgent grievance alerts)

---

## Import Instructions

### 1. Start n8n

```bash
# Docker
docker run -d --name n8n -p 5678:5678 \
  -v n8n_data:/home/node/.n8n \
  --add-host=host.docker.internal:host-gateway \
  n8nio/n8n

# Or npm
npx n8n start
```

### 2. Set Up Credentials

Before importing workflows, create the following credentials in n8n
(Settings > Credentials > Add Credential):

#### MS Graph OAuth2
- Type: **Microsoft OAuth2 API** (or Generic OAuth2)
- Name: **MS Graph OAuth2**
- Client ID: from Azure AD app registration
- Client Secret: from Azure AD app registration
- Tenant ID: your Azure AD tenant
- Scope: `Calendars.Read Mail.Read User.Read`

#### Pulse API Token
- Type: **Header Auth**
- Name: **Pulse API Token**
- Header Name: `Authorization`
- Header Value: `Bearer <your-pulse-api-token>`

#### n8n Environment Variables
Set these in n8n Settings > Variables (or via `N8N_` env vars):

| Variable | Value |
|----------|-------|
| `pulseApiBaseUrl` | `http://localhost:8000` (or your Pulse host) |
| `msTeamsWebhookUrl` | Your MS Teams incoming webhook URL |

### 3. Import Workflows

For each JSON file in `workflows/`:

1. Open n8n UI (default: `http://localhost:5678`)
2. Click **Workflows** > **Import from File**
3. Select the JSON file
4. Open the imported workflow
5. Verify credential references resolve (yellow warning icon = missing credential)
6. Toggle the workflow **Active**

Or use the n8n CLI:

```bash
for f in workflows/*.json; do
  n8n import:workflow --input="$f"
done
```

### 4. Verify Ollama

Workflows 3, 4, and 5 call Ollama. Verify it's running:

```bash
curl http://localhost:11434/api/generate \
  -d '{"model": "llama3.1:8b", "prompt": "Say hello", "stream": false}'
```

If Ollama runs inside Docker, ensure the n8n container can reach `localhost:11434`
(use `host.docker.internal:11434` if needed and update the HTTP Request URLs accordingly).

---

## Testing Each Workflow

### Workflow 1 — Daily Context Builder
1. Open the workflow in n8n
2. Click **Execute Workflow** (manual run)
3. Verify: Calendar fetch returns data (or auth error if no MS Graph creds yet)
4. Verify: Pulse task and email summary endpoints respond
5. Verify: Agent health pings execute (may 404 if no agents running — that's OK)

### Workflow 2 — Grievance Deadline Monitor
1. Ensure Pulse has at least one open grievance with a `due_date` within 7 days
2. Execute manually
3. Verify: Filter node produces items only for grievances due within 7 days
4. Verify: Dedup node skips on second execution (same day)
5. Verify: If `within_48h` is true, Teams webhook fires

### Workflow 3 — Legislative Calendar Tracker
1. Execute manually
2. Verify: CT General Assembly page fetches successfully
3. Verify: Keyword filter produces relevant hearings (or empty if none match)
4. Verify: Ollama call completes and returns a summary
5. Verify: Tasks created in Pulse with `tag=legislative`

### Workflow 4 — Weekly Report Aggregator
1. Ensure Pulse has check-in data for the current week
2. Execute manually
3. Verify: Ollama produces a <200 word summary
4. Verify: Draft report posted to Pulse
5. Verify: Dave's agent notified

### Workflow 5 — Email Thread Intelligence
1. Use n8n's webhook test URL or curl:
   ```bash
   curl -X POST http://localhost:5678/webhook-test/email-thread-intelligence \
     -H "Content-Type: application/json" \
     -d '{"email_id": "test-123", "subject": "Contract negotiation update", "thread_length": 5, "sender": "steward@facility.org", "owner_agent": "dave"}'
   ```
2. Verify: Thread fetched from Pulse (will 404 with fake ID — check flow logic)
3. Verify: Ollama call uses `localhost:11434` — no external API
4. Verify: Response includes `summary` and `suggested_action`

### Workflow 6 — New Member Orientation
1. Use n8n's webhook test URL or curl:
   ```bash
   curl -X POST http://localhost:5678/webhook-test/new-member-orientation \
     -H "Content-Type: application/json" \
     -d '{"member_name": "Jane Smith", "facility": "Bradley Memorial Hospital", "bargaining_unit": "1199NE", "hire_date": "2026-02-20"}'
   ```
2. Verify: 7 orientation tasks + 1 thirty-day check-in created in Pulse
3. Verify: Orientation tasks assigned to `execsec`
4. Verify: 30-day check-in assigned to `dave`

---

## Credential Reference Map

All workflows reference credentials by the names below. These must match exactly
in your n8n credential setup.

| Credential Name | Type | Used By Workflows |
|----------------|------|-------------------|
| MS Graph OAuth2 | Microsoft OAuth2 | 1 |
| Pulse API Token | Header Auth | 1, 2, 3, 4, 5, 6 |
| Ollama (localhost) | Direct HTTP | 3, 4, 5 |
| MS Teams Webhook | Direct HTTP (via env var) | 2 |

---

## Security Notes

- **Ollama only**: Workflows 3, 4, 5 send data to `http://localhost:11434/api/generate`.
  This is a local-only endpoint. No sensitive data leaves the network.
- **No hardcoded secrets**: All credentials use n8n credential references.
  The JSON files contain credential IDs and names, not values.
- **Webhook authentication**: Workflows 5 and 6 accept webhook POSTs.
  In production, configure n8n webhook authentication or place behind a reverse proxy.
- **MS Teams webhook**: The Teams URL is stored as an n8n environment variable,
  not hardcoded in any workflow JSON.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Workflow shows yellow credential warning | Create the credential with the exact name listed above |
| Ollama timeout | Increase timeout in HTTP Request node; ensure model is downloaded (`ollama pull llama3.1:8b`) |
| MS Graph 401 | Re-authorize OAuth2 credential; check token expiry |
| Pulse connection refused | Verify Pulse API is running on the configured `pulseApiBaseUrl` |
| Webhook not triggering | Ensure workflow is **Active** (toggled on); check n8n webhook URL |
| CT General Assembly page changed | Update HTML parsing in workflow 3's Code node |

---

## File Structure

```
integrations/n8n/
  README.md                  # This file
  credentials-template.json  # Credential structure (no secrets)
  workflows/
    01-daily-context-builder.json
    02-grievance-deadline-monitor.json
    03-legislative-calendar-tracker.json
    04-weekly-report-aggregator.json
    05-email-thread-intelligence.json
    06-new-member-orientation.json
```
