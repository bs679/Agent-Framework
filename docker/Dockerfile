FROM openclaw/openclaw:latest

RUN pip install requests python-docx msal python-dateutil pyyaml

COPY docker/entrypoint.sh /entrypoint.sh
COPY docker/load_config.py /app/load_config.py
RUN chmod +x /entrypoint.sh

# Run as non-root for container security.
# The base image must expose a writable /app/memory mount as this user.
RUN groupadd -r openclaw && useradd -r -g openclaw -d /app -s /sbin/nologin openclaw \
    && chown -R openclaw:openclaw /app

USER openclaw

# Health probe: OpenClaw exposes /health on port 3000 after startup.
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:3000/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]
