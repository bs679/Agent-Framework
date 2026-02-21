FROM openclaw/openclaw:latest

RUN pip install requests python-docx msal python-dateutil

COPY docker/entrypoint.sh /entrypoint.sh
COPY docker/load_config.py /app/load_config.py
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
