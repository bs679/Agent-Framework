#!/usr/bin/env bash
# Container entrypoint: poll the mounted watch dir on an interval and extract
# any new PDFs. Long-running; restart-friendly.
set -euo pipefail

: "${ANTHROPIC_API_KEY:?set ANTHROPIC_API_KEY for the transcription stage}"
: "${WATCH_DIR:?set WATCH_DIR}"
: "${OUT_DIR:?set OUT_DIR}"
INTERVAL="${INTERVAL:-900}"

echo "EMS extractor: watching '$WATCH_DIR' -> '$OUT_DIR' every ${INTERVAL}s"
while true; do
  bash tools/ems-schedule-extract/watch_rfi.sh "$WATCH_DIR" "$OUT_DIR" || \
    echo "$(date '+%F %T') watch run errored (continuing)"
  sleep "$INTERVAL"
done
