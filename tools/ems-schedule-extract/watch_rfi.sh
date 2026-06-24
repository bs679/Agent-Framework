#!/usr/bin/env bash
# watch_rfi.sh — poll a folder for new schedule PDFs and extract each to Excel.
# Cron / Task-Scheduler friendly (no inotify): processes any *.pdf whose .xlsx is
# missing or older than the PDF, then exits. A flock prevents overlapping runs.
#
# Usage:   watch_rfi.sh <watch_dir> <out_dir>
# Cron:    */15 * * * * /path/to/repo/tools/ems-schedule-extract/watch_rfi.sh \
#                       "/sync/Madison EMS/RFI Responses" "/sync/Madison EMS" >/dev/null 2>&1
set -euo pipefail

WATCH="${1:?usage: watch_rfi.sh <watch_dir> <out_dir>}"
OUT="${2:?usage: watch_rfi.sh <watch_dir> <out_dir>}"
# repo root = two levels up from this script (tools/ems-schedule-extract/ -> repo)
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
mkdir -p "$OUT"
LOG="$OUT/.extract.log"
LOCK="$OUT/.extract.lock"

exec 9>"$LOCK"
flock -n 9 || { echo "$(date '+%F %T') another run in progress; skipping" >>"$LOG"; exit 0; }

shopt -s nullglob nocaseglob
found=0
for pdf in "$WATCH"/*.pdf; do
  base="$(basename "$pdf")"
  out="$OUT/${base%.*}.xlsx"
  # skip if up-to-date output already exists
  if [ -f "$out" ] && [ "$out" -nt "$pdf" ]; then continue; fi
  found=1
  echo "$(date '+%F %T') processing: $base" >>"$LOG"
  if ( cd "$REPO" && claude -p "/extract-ems-schedule '$pdf' '$out'" \
         --allowedTools Bash Read Write Edit Agent Glob ) >>"$LOG" 2>&1; then
    echo "$(date '+%F %T') done: $base -> $out" >>"$LOG"
  else
    echo "$(date '+%F %T') FAILED: $base (see log above)" >>"$LOG"
  fi
done
[ "$found" -eq 0 ] && echo "$(date '+%F %T') nothing new" >>"$LOG"
exit 0
