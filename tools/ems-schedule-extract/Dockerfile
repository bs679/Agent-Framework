# EMS schedule extractor — self-contained image (Synology/NAS or any Docker host).
# Bundles poppler (pdftoppm), tesseract (OSD), the Python libs, and the Claude Code
# CLI. Mount your synced OneDrive folders and supply an API key at runtime.
#
#   docker build -t ems-extract -f tools/ems-schedule-extract/Dockerfile .
#   docker run -d --name ems-extract --restart unless-stopped \
#     -e ANTHROPIC_API_KEY=sk-ant-... \
#     -e INTERVAL=900 \
#     -v "/volume1/OneDrive/Madison EMS/RFI Responses:/data/in:ro" \
#     -v "/volume1/OneDrive/Madison EMS:/data/out" \
#     ems-extract
#
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        poppler-utils tesseract-ocr ca-certificates curl gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pillow numpy pandas openpyxl \
    && npm install -g @anthropic-ai/claude-code

WORKDIR /repo
COPY . /repo

# Override at runtime as needed.
ENV WATCH_DIR=/data/in \
    OUT_DIR=/data/out \
    INTERVAL=900

ENTRYPOINT ["bash", "tools/ems-schedule-extract/docker-entrypoint.sh"]
