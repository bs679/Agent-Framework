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

# load_config.py writes the system prompt to this file; export it so
# the exec'd openclaw process inherits the variable.
export OPENCLAW_SYSTEM_PROMPT
OPENCLAW_SYSTEM_PROMPT="$(cat /app/system_prompt.txt)"

exec openclaw start --config /app/config/
