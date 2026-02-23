#!/usr/bin/env bash
# =============================================================================
# AIOS/Pulse — Disaster Recovery Restore Script
#
# Restores PostgreSQL database and agent memory volumes from a backup created
# by scripts/backup.sh.
#
# Usage:
#   ./scripts/restore.sh YYYY-MM-DD [--agent <agent-id>] [--db-only] [--memory-only]
#
# Examples:
#   # Full restore from 2026-02-22
#   ./scripts/restore.sh 2026-02-22
#
#   # Restore only the database
#   ./scripts/restore.sh 2026-02-22 --db-only
#
#   # Restore only one agent's memory
#   ./scripts/restore.sh 2026-02-22 --agent president-dave --memory-only
#
# WARNING: This script overwrites existing data.  Stop the Pulse container
#          before running a full restore to avoid write conflicts.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BACKUP_BASE="${BACKUP_BASE:-$PROJECT_ROOT/backups}"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-postgres}"
POSTGRES_USER="${POSTGRES_USER:-pulse}"
POSTGRES_DB="${POSTGRES_DB:-aios_pulse}"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
log_error() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $*" >&2; }
die() { log_error "$*"; exit 1; }

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
BACKUP_DATE=""
TARGET_AGENT=""
DB_ONLY=false
MEMORY_ONLY=false

usage() {
    echo "Usage: $0 YYYY-MM-DD [--agent <id>] [--db-only] [--memory-only]"
    exit 1
}

if [ $# -eq 0 ]; then usage; fi
BACKUP_DATE="$1"; shift

while [ $# -gt 0 ]; do
    case "$1" in
        --agent)    TARGET_AGENT="$2"; shift 2 ;;
        --db-only)  DB_ONLY=true; shift ;;
        --memory-only) MEMORY_ONLY=true; shift ;;
        *) die "Unknown argument: $1" ;;
    esac
done

# Validate date format
if ! echo "$BACKUP_DATE" | grep -qE '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'; then
    die "Invalid date format. Use YYYY-MM-DD."
fi

BACKUP_DIR="$BACKUP_BASE/$BACKUP_DATE"
if [ ! -d "$BACKUP_DIR" ]; then
    die "Backup directory not found: $BACKUP_DIR"
fi

log "=== AIOS/Pulse Restore: $BACKUP_DATE ==="
log "Source: $BACKUP_DIR"

# ---------------------------------------------------------------------------
# Confirmation prompt (unless CI=true)
# ---------------------------------------------------------------------------
if [ "${CI:-false}" != "true" ]; then
    echo ""
    echo "WARNING: This will overwrite existing data."
    read -r -p "Type 'yes' to continue: " CONFIRM
    if [ "$CONFIRM" != "yes" ]; then
        echo "Aborted."
        exit 0
    fi
fi

# ---------------------------------------------------------------------------
# 1. Restore PostgreSQL
# ---------------------------------------------------------------------------
if [ "$MEMORY_ONLY" = false ]; then
    PG_DUMP_FILE="$BACKUP_DIR/postgres.sql.gz"
    if [ ! -f "$PG_DUMP_FILE" ]; then
        die "PostgreSQL dump not found: $PG_DUMP_FILE"
    fi

    log "Restoring PostgreSQL database '$POSTGRES_DB'..."

    # Drop existing connections, recreate DB, restore
    docker exec "$POSTGRES_CONTAINER" \
        psql -U "$POSTGRES_USER" -c \
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$POSTGRES_DB' AND pid <> pg_backend_pid();" \
        postgres || true

    docker exec "$POSTGRES_CONTAINER" \
        psql -U "$POSTGRES_USER" -c "DROP DATABASE IF EXISTS $POSTGRES_DB;" postgres

    docker exec "$POSTGRES_CONTAINER" \
        psql -U "$POSTGRES_USER" -c "CREATE DATABASE $POSTGRES_DB;" postgres

    zcat "$PG_DUMP_FILE" | docker exec -i "$POSTGRES_CONTAINER" \
        psql -U "$POSTGRES_USER" "$POSTGRES_DB"

    log "PostgreSQL restore complete"
fi

# ---------------------------------------------------------------------------
# 2. Restore agent memory volumes
# ---------------------------------------------------------------------------
if [ "$DB_ONLY" = false ]; then
    AGENTS_DIR="$PROJECT_ROOT/agents"

    if [ -n "$TARGET_AGENT" ]; then
        # Restore a single agent
        archive="$BACKUP_DIR/memory-${TARGET_AGENT}.tar.gz"
        if [ ! -f "$archive" ]; then
            die "Memory archive not found: $archive"
        fi
        log "Restoring memory for agent '$TARGET_AGENT'..."
        rm -rf "$AGENTS_DIR/$TARGET_AGENT/memory"
        tar -xzf "$archive" -C "$AGENTS_DIR"
        log "  Memory restored: $AGENTS_DIR/$TARGET_AGENT/memory/"
    else
        # Restore all agents found in the backup
        log "Restoring all agent memory volumes..."
        for archive in "$BACKUP_DIR"/memory-*.tar.gz; do
            [ -f "$archive" ] || continue
            filename="$(basename "$archive")"
            agent_id="${filename#memory-}"
            agent_id="${agent_id%.tar.gz}"
            log "  Restoring agent '$agent_id'..."
            rm -rf "$AGENTS_DIR/$agent_id/memory"
            tar -xzf "$archive" -C "$AGENTS_DIR"
            log "    Restored: $AGENTS_DIR/$agent_id/memory/"
        done
    fi
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
log "=== Restore complete ==="
log "Next steps:"
log "  1. Run Alembic migrations if DB schema has changed: alembic upgrade head"
log "  2. Restart Pulse: docker-compose up -d pulse"
log "  3. Verify: curl http://localhost:8000/api/v1/health"
