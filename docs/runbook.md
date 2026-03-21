# AIOS/Pulse — Operational Runbook

Reference document for daily operations, weekly maintenance, incident
response, and adding new staff agents.

---

## Quick Reference

| What | Where |
|------|-------|
| Health dashboard | `GET /api/v1/health/full` |
| Monitoring alerts | MS Teams (never email) |
| Backup log | `/var/log/aios-backup.log` |
| Healthcheck log | `/var/log/aios-healthcheck.log` |
| Agent logs | `aios agents logs --agent {id}` |
| Agent status | `aios agents status --agent {id}` |

---

## Daily Checklist

### Morning (on startup or first thing)

1. **Check system health**

   ```bash
   curl http://localhost:8000/api/v1/health/full | python3 -m json.tool
   ```

   Expected response:
   ```json
   {
     "status": "healthy",
     "database": "ok",
     "redis": "ok",
     "ai_router": {"ollama": "ok", "kimi_k2": "disabled", "claude": "disabled"},
     "agents": {"running": 8, "total": 8, "degraded": []}
   }
   ```

   Any `"degraded"` or `"error"` values → see Incident Response below.

2. **Review backup log**

   ```bash
   tail -20 /var/log/aios-backup.log
   ```

   Look for `Backup complete:` at the end. If not present, check disk space and
   PostgreSQL container status.

3. **Check MS Teams for monitoring alerts**

   The healthcheck cron runs every 5 minutes and posts to Teams on failure.
   If there are unread alerts, address them before starting other work.

---

## Weekly Checklist

### Every Monday morning

1. **Review n8n workflow execution history**

   Open n8n at `http://localhost:5678` → Executions → filter for "Failed".
   Common failures: MS Graph token expiry, Ollama timeout on large prompts.

2. **Check disk space**

   ```bash
   df -h /
   df -h /home/user/Agent-Framework/backups
   ```

   Alert threshold: < 20% free. If low:
   - Check backup directory for old archives: `ls -lh backups/`
   - Manual rotation: `find backups/ -type d -mtime +30 -exec rm -rf {} +`

3. **Verify all 8 agents passed morning check-in**

   ```bash
   curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/v1/agents/checkin/status
   ```

   Or check the Pulse sidebar — all 8 agents should show a morning check-in.

4. **Test backup restore (monthly, first Monday)**

   ```bash
   # Restore to a test database to verify backup integrity
   ./scripts/restore.sh $(date +%Y-%m-%d) --db-only
   # Connect and spot-check data:
   docker exec postgres psql -U pulse aios_pulse -c "SELECT count(*) FROM check_ins;"
   ```

---

## Incident Response

### Agent container not starting

```bash
# 1. Check container logs first
aios agents logs --agent {id}

# 2. Check container status
aios agents status --agent {id}

# 3. If exited/stopped, try restart
docker start openclaw-{id}

# 4. If restart fails, check for config issues
docker run --rm \
  -v $(pwd)/agents/{id}/config:/app/config:ro \
  openclaw/openclaw:latest \
  openclaw validate-config

# 5. Last resort: full recreate
docker rm openclaw-{id}
docker-compose up -d openclaw-{id}  # if defined in compose
# or
aios agents upgrade --plane chca-agents --agent {id}
```

### Database connection error

```bash
# 1. Check postgres container
docker ps | grep postgres
docker logs postgres --tail 30

# 2. Test connectivity
docker exec postgres pg_isready -U pulse

# 3. If down, restart
docker-compose up -d postgres

# 4. Wait for health check, then restart Pulse
sleep 15
docker-compose restart pulse

# 5. Verify
curl http://localhost:8000/api/v1/health/full
```

### Ollama not responding

```bash
# 1. Check Ollama process on host (runs directly, not in Docker)
ps aux | grep ollama

# 2. Test endpoint
curl localhost:11434/api/version

# 3. If not running, restart Ollama
ollama serve &

# 4. Verify models are loaded
ollama list

# 5. If model missing, re-pull
ollama pull llama3.1:8b
```

### Kimi K2 calls failing

```bash
# 1. Check NVIDIA_API_KEY is set
grep NVIDIA_API_KEY .env

# 2. Verify KIMI_ENABLED=true
grep KIMI_ENABLED .env

# 3. Run AI router health check
aios ai health

# 4. Test with a non-sensitive prompt
aios ai test --task report_drafting --prompt "Summarise in one sentence: the meeting went well."

# 5. If API key is expired, get a new one from build.nvidia.com
#    Update .env, then restart Pulse:
docker-compose restart pulse
```

### Wrong model routing (sensitive data going to external API)

```bash
# 1. Inspect the routing table
aios ai test-routing

# 2. Verify config/ai-routing.yaml has correct sensitive: true flags
#    All grievance, member, negotiation tasks must be sensitive: true

# 3. Test routing for a specific task
aios ai test-routing | grep grievance

# 4. If routing table is wrong, edit config/ai-routing.yaml and restart Pulse
docker-compose restart pulse
```

### Backup failure

```bash
# 1. Check backup log
tail -50 /var/log/aios-backup.log

# 2. Verify disk space
df -h .

# 3. Check postgres container is running
docker inspect postgres --format='{{.State.Status}}'

# 4. Run backup manually to see error output
./scripts/backup.sh

# 5. Verify backup created
ls -lh backups/$(date +%Y-%m-%d)/
```

### Redis connection error

```bash
# 1. Check container
docker ps | grep redis
docker exec redis redis-cli ping

# 2. Restart if needed
docker-compose restart redis

# Note: Redis is optional — if it's down, API endpoints serve from source
# without caching. System remains functional; only performance is affected.
```

### Health monitoring alerts not reaching MS Teams

```bash
# 1. Verify N8N_HEALTH_WEBHOOK_URL is set
grep N8N_HEALTH_WEBHOOK_URL .env

# 2. Test webhook manually
curl -X POST "$N8N_HEALTH_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{"status":"test","timestamp":"now","failures":["manual test"]}'

# 3. Check n8n is running
curl http://localhost:5678/healthz

# 4. Review n8n workflow for the Teams webhook connector
```

---

## Adding a New Staff Agent (9th Person)

When a 9th staff member is onboarded:

1. **Have them complete the onboarding form**

   Open `http://localhost:5173` (or wherever the onboarding form is hosted).
   They complete the 23-question form and download the ZIP file.

2. **Extract the ZIP from their browser**

   The ZIP contains 6 config files:
   - `SOUL.md`, `USER.md`, `IDENTITY.md`, `AGENTS.md`, `HEARTBEAT.md`, `MEMORY.md`

3. **Copy 6 files to the agent config directory**

   ```bash
   # Replace {id} with the agent ID from IDENTITY.md
   mkdir -p agents/{id}/config/
   cp ~/Downloads/agent-config-{id}/*.md agents/{id}/config/
   ```

4. **Add to the plane and provision the container**

   ```bash
   aios agents add \
     --config agents/{id}/config/ \
     --plane chca-agents
   ```

   This creates `agents/{id}/.env` with a unique `MEMORY_ENCRYPTION_KEY`
   (never overwrites an existing key).

5. **Start the container**

   ```bash
   docker-compose up -d openclaw-{id}
   # or if not in compose:
   docker run -d \
     --name openclaw-{id} \
     --network chca-agents-net \
     -v $(pwd)/agents/{id}/config:/app/config:ro \
     -v $(pwd)/agents/{id}/memory:/app/memory:rw \
     --env-file agents/{id}/.env \
     --restart unless-stopped \
     openclaw/openclaw:latest
   ```

6. **Verify**

   ```bash
   aios agents status --agent {id}
   ```

   Expected: `status: running`, health check passing within 40s.

7. **Update `EXPECTED_AGENT_COUNT` in `.env`**

   ```bash
   # Change from 8 to 9
   sed -i 's/EXPECTED_AGENT_COUNT=8/EXPECTED_AGENT_COUNT=9/' .env
   ```

   This ensures the health endpoint and healthcheck script reflect the new total.

8. **Update `AGENT_CONTAINERS` in `scripts/healthcheck.sh`**

   Add `openclaw-{id}` to the `AGENT_CONTAINERS` array.

9. **Update `/api/v1/health/full` endpoint**

   Add the new container name to `_AGENT_CONTAINERS` in
   `integrations/pulse/api/v1/health.py` and restart Pulse.

---

## Container Management Reference

```bash
# Start all services
docker-compose up -d

# Stop all services (agents keep running — only infra stops)
docker-compose down

# View all containers
docker ps

# Agent-specific
aios agents list --plane chca-agents
aios agents status --agent president-dave
aios agents logs --agent president-dave
aios agents logs --agent president-dave --follow
aios agents restart --agent president-dave

# Rolling upgrade (updates all agents to latest OpenClaw image)
aios agents upgrade --plane chca-agents

# Backup & restore
./scripts/backup.sh
./scripts/restore.sh 2026-02-22
./scripts/restore.sh 2026-02-22 --agent president-dave --memory-only
./scripts/restore.sh 2026-02-22 --db-only
```

---

## Security Reminders

- Sensitive union data (grievances, member info, negotiation strategy) is
  always routed to Ollama (local). Never sent to Claude or Kimi K2.
- The AI router sanitizer is a last-resort safety net — verify `sensitive: true`
  flags are correct in `config/ai-routing.yaml`.
- `.env` files are gitignored. Never commit them.
- Admin sees agent health and logs but never `.env` contents or memory.
- Disbursements always require co-signatures — no agent may bypass this.
- Executive Session meetings: agent receives pre-meeting prep only. No recording.

---

*See also:*
- `docs/gcp-migration-path.md` — how to migrate to GCP if needed
- `docs/ssl-setup.md` — enabling HTTPS
- `Claude.md` — full project context and hard rules
