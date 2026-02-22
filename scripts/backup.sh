#!/usr/bin/env bash
# =============================================================================
# AIOS/Pulse — Daily Backup Script
#
# Creates a timestamped backup of:
#   - PostgreSQL database (pg_dump → gzip)
#   - Agent memory volumes (tar.gz per agent)
#
# Run via cron:
#   0 2 * * * /path/to/Agent-Framework/scripts/backup.sh >> /var/log/aios-backup.log 2>&1
#
# Backups are stored in ./backups/YYYY-MM-DD/ and rotated after 30 days.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# ---------------------------------------------------------------------------
# Configuration (override via environment)
# ---------------------------------------------------------------------------
BACKUP_BASE="${BACKUP_BASE:-$PROJECT_ROOT/backups}"
BACKUP_DATE="$(date +%Y-%m-%d)"
BACKUP_DIR="$BACKUP_BASE/$BACKUP_DATE"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-postgres}"
POSTGRES_USER="${POSTGRES_USER:-pulse}"
POSTGRES_DB="${POSTGRES_DB:-aios_pulse}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
log_error() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $*" >&2; }

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
if ! command -v docker &>/dev/null; then
    log_error "docker not found — aborting"
    exit 1
fi

if ! docker inspect "$POSTGRES_CONTAINER" &>/dev/null; then
    log_error "Postgres container '$POSTGRES_CONTAINER' not running — aborting"
    exit 1
fi

# ---------------------------------------------------------------------------
# Create backup directory
# ---------------------------------------------------------------------------
mkdir -p "$BACKUP_DIR"
log "Backup started: $BACKUP_DIR"

# ---------------------------------------------------------------------------
# 1. PostgreSQL dump
# ---------------------------------------------------------------------------
PG_DUMP_FILE="$BACKUP_DIR/postgres.sql.gz"
log "Dumping PostgreSQL database '$POSTGRES_DB'..."
if docker exec "$POSTGRES_CONTAINER" \
    pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip > "$PG_DUMP_FILE"; then
    SIZE="$(du -sh "$PG_DUMP_FILE" | cut -f1)"
    log "PostgreSQL dump complete: $PG_DUMP_FILE ($SIZE)"
else
    log_error "PostgreSQL dump failed"
    exit 1
fi

# ---------------------------------------------------------------------------
# 2. Agent memory volumes
# ---------------------------------------------------------------------------
AGENTS_DIR="$PROJECT_ROOT/agents"
if [ -d "$AGENTS_DIR" ]; then
    log "Backing up agent memory volumes..."
    for agent_dir in "$AGENTS_DIR"/*/; do
        [ -d "$agent_dir" ] || continue
        agent_id="$(basename "$agent_dir")"
        memory_dir="$agent_dir/memory"

        # Skip agents with no memory directory
        if [ ! -d "$memory_dir" ]; then
            log "  $agent_id: no memory directory, skipping"
            continue
        fi

        archive="$BACKUP_DIR/memory-${agent_id}.tar.gz"
        if tar -czf "$archive" -C "$AGENTS_DIR" "${agent_id}/memory/"; then
            SIZE="$(du -sh "$archive" | cut -f1)"
            log "  $agent_id memory: $archive ($SIZE)"
        else
            log_error "  Failed to archive memory for agent $agent_id"
        fi
    done
else
    log "No agents directory found at $AGENTS_DIR — skipping memory backup"
fi

# ---------------------------------------------------------------------------
# 3. Write manifest
# ---------------------------------------------------------------------------
MANIFEST="$BACKUP_DIR/MANIFEST.txt"
{
    echo "AIOS/Pulse Backup Manifest"
    echo "Date: $BACKUP_DATE"
    echo "Created: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    echo "PostgreSQL DB: $POSTGRES_DB"
    echo ""
    echo "Files:"
    ls -lh "$BACKUP_DIR/"
} > "$MANIFEST"

# ---------------------------------------------------------------------------
# 4. Rotate old backups (delete directories older than RETENTION_DAYS)
# ---------------------------------------------------------------------------
log "Rotating backups older than $RETENTION_DAYS days..."
find "$BACKUP_BASE" -maxdepth 1 -mindepth 1 -type d -mtime +"$RETENTION_DAYS" \
    -exec rm -rf {} + && log "Rotation complete"

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
log "Backup complete: $BACKUP_DIR"
