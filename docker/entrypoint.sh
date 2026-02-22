#!/bin/bash
set -e

echo "Starting agent $AGENT_ID..."

if [ -z "$AGENT_ID" ]; then
    echo "AGENT_ID is required"
    exit 1
fi

if [ -z "$PLANE_NAME" ]; then
    echo "PLANE_NAME is required"
    exit 1
fi

python /app/load_config.py

exec openclaw start --config /app/config/
