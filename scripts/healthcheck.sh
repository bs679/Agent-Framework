#!/usr/bin/env bash
# =============================================================================
# AIOS/Pulse — Health Check Script
#
# Runs every 5 minutes via cron. On failure, POSTs to the n8n webhook which
# sends an MS Teams alert to Dave. Never sends email — Teams only.
#
# Cron entry:
#   */5 * * * * /path/to/Agent-Framework/scripts/healthcheck.sh >> /var/log/aios-healthcheck.log 2>&1
#
# Checks:
#   1. All 8 agent containers are running
#   2. Pulse API responds to GET /api/v1/health
#   3. PostgreSQL responds to pg_isready
#   4. Redis responds to redis-cli ping
#   5. Ollama responds to GET localhost:11434/api/version
#   5b. AI router: GET /api/v1/ai/health — all configured models report status
#   6. Free disk space > 20%
# =============================================================================

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# ---------------------------------------------------------------------------
# Configuration (override via environment or .env)
# ---------------------------------------------------------------------------
ENV_FILE="$PROJECT_ROOT/.env"
if [ -f "$ENV_FILE" ]; then
    # shellcheck disable=SC1090
    set -a; source "$ENV_FILE"; set +a
fi

PULSE_API_URL="${PULSE_API_URL:-http://localhost:8000}"
OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-postgres}"
POSTGRES_USER="${POSTGRES_USER:-pulse}"
REDIS_CONTAINER="${REDIS_CONTAINER:-redis}"
N8N_HEALTH_WEBHOOK_URL="${N8N_HEALTH_WEBHOOK_URL:-}"
AGENT_COUNT="${AGENT_COUNT:-8}"
DISK_THRESHOLD="${DISK_THRESHOLD:-20}"  # Alert if free space < 20%

# Agent container names (update if names differ)
AGENT_CONTAINERS=(
    "openclaw-president-dave"
    "openclaw-secretary-treasurer"
    "openclaw-executive-secretary"
    "openclaw-staff-4"
    "openclaw-staff-5"
    "openclaw-staff-6"
    "openclaw-staff-7"
    "openclaw-staff-8"
)

# ---------------------------------------------------------------------------
# State tracking
# ---------------------------------------------------------------------------
FAILURES=()
TIMESTAMP="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
log() { echo "[$TIMESTAMP] $*"; }
fail() { FAILURES+=("$1"); log "FAIL: $1"; }
pass() { log "OK: $1"; }

# ---------------------------------------------------------------------------
# Check 1: Agent containers
# ---------------------------------------------------------------------------
log "--- Check 1: Agent containers ---"
running_count=0
for container in "${AGENT_CONTAINERS[@]}"; do
    status="$(docker inspect --format='{{.State.Status}}' "$container" 2>/dev/null || echo 'not_found')"
    if [ "$status" = "running" ]; then
        running_count=$((running_count + 1))
        pass "Container $container is running"
    else
        fail "Container $container status: $status"
    fi
done
log "Running containers: $running_count / ${#AGENT_CONTAINERS[@]}"

# ---------------------------------------------------------------------------
# Check 2: Pulse API health
# ---------------------------------------------------------------------------
log "--- Check 2: Pulse API ---"
http_code="$(curl -s -o /dev/null -w '%{http_code}' \
    --max-time 10 "$PULSE_API_URL/api/v1/health" 2>/dev/null || echo '000')"
if [ "$http_code" = "200" ]; then
    pass "Pulse API /api/v1/health returned 200"
else
    fail "Pulse API /api/v1/health returned HTTP $http_code"
fi

# ---------------------------------------------------------------------------
# Check 3: PostgreSQL
# ---------------------------------------------------------------------------
log "--- Check 3: PostgreSQL ---"
if docker exec "$POSTGRES_CONTAINER" pg_isready -U "$POSTGRES_USER" &>/dev/null; then
    pass "PostgreSQL pg_isready OK"
else
    fail "PostgreSQL pg_isready failed (container: $POSTGRES_CONTAINER)"
fi

# ---------------------------------------------------------------------------
# Check 4: Redis
# ---------------------------------------------------------------------------
log "--- Check 4: Redis ---"
redis_ping="$(docker exec "$REDIS_CONTAINER" redis-cli ping 2>/dev/null || echo 'ERROR')"
if [ "$redis_ping" = "PONG" ]; then
    pass "Redis ping OK"
else
    fail "Redis ping failed: $redis_ping"
fi

# ---------------------------------------------------------------------------
# Check 5: Ollama
# ---------------------------------------------------------------------------
log "--- Check 5: Ollama ---"
ollama_code="$(curl -s -o /dev/null -w '%{http_code}' \
    --max-time 5 "$OLLAMA_BASE_URL/api/version" 2>/dev/null || echo '000')"
if [ "$ollama_code" = "200" ]; then
    pass "Ollama /api/version returned 200"
else
    fail "Ollama not responding (HTTP $ollama_code) — check Ollama process on host"
fi

# ---------------------------------------------------------------------------
# Check 5b: AI Router
# ---------------------------------------------------------------------------
log "--- Check 5b: AI Router ---"
ai_health_code="$(curl -s -o /dev/null -w '%{http_code}' \
    --max-time 15 "$PULSE_API_URL/api/v1/ai/health" 2>/dev/null || echo '000')"
if [ "$ai_health_code" = "200" ]; then
    pass "AI router /api/v1/ai/health returned 200"
else
    fail "AI router health check failed (HTTP $ai_health_code)"
fi

# ---------------------------------------------------------------------------
# Check 6: Disk space
# ---------------------------------------------------------------------------
log "--- Check 6: Disk space ---"
# Check the filesystem hosting the project
disk_free_pct="$(df "$PROJECT_ROOT" | awk 'NR==2 {gsub(/%/,""); print 100 - $5}')"
if [ "${disk_free_pct:-0}" -gt "$DISK_THRESHOLD" ]; then
    pass "Disk space: ${disk_free_pct}% free (threshold: ${DISK_THRESHOLD}%)"
else
    fail "Low disk space: ${disk_free_pct}% free (threshold: ${DISK_THRESHOLD}%)"
fi

# ---------------------------------------------------------------------------
# Report results
# ---------------------------------------------------------------------------
if [ "${#FAILURES[@]}" -eq 0 ]; then
    log "All checks passed"
    exit 0
fi

log "=== FAILURES DETECTED (${#FAILURES[@]}) ==="
for f in "${FAILURES[@]}"; do
    log "  - $f"
done

# ---------------------------------------------------------------------------
# Alert via n8n → MS Teams (never email)
# ---------------------------------------------------------------------------
if [ -n "$N8N_HEALTH_WEBHOOK_URL" ]; then
    log "Sending alert to n8n webhook..."
    FAILURE_LIST="$(printf '%s\\n' "${FAILURES[@]}")"
    PAYLOAD="{
        \"status\": \"degraded\",
        \"timestamp\": \"$TIMESTAMP\",
        \"failures\": $(printf '%s\n' "${FAILURES[@]}" | python3 -c 'import json,sys; print(json.dumps([l.strip() for l in sys.stdin]))'),
        \"host\": \"$(hostname)\",
        \"project_root\": \"$PROJECT_ROOT\"
    }"
    curl -s -X POST "$N8N_HEALTH_WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -d "$PAYLOAD" \
        --max-time 10 && log "Alert sent" || log "WARNING: Alert delivery failed"
else
    log "N8N_HEALTH_WEBHOOK_URL not set — alert not sent"
fi

exit 1
