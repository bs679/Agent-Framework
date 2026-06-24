#!/usr/bin/env bash
# setup.sh — install dependencies for the EMS schedule extractor.
# Safe to re-run. Installs poppler-utils + tesseract (system) and the Python libs.
set -euo pipefail

need(){ command -v "$1" >/dev/null 2>&1; }
SUDO=""; if [ "$(id -u)" -ne 0 ] && need sudo; then SUDO="sudo"; fi

echo "== installing system packages (poppler-utils, tesseract) =="
if   need apt-get; then $SUDO apt-get update -y && $SUDO apt-get install -y poppler-utils tesseract-ocr
elif need dnf;     then $SUDO dnf install -y poppler-utils tesseract
elif need yum;     then $SUDO yum install -y poppler-utils tesseract
elif need apk;     then $SUDO apk add --no-cache poppler-utils tesseract-ocr
elif need brew;    then brew install poppler tesseract
elif need opkg;    then $SUDO opkg update && $SUDO opkg install poppler-utils tesseract   # Synology/Entware
else echo "!! No known package manager. Install 'poppler-utils' + 'tesseract' manually, or run via Docker."; fi

echo "== installing Python libraries =="
python3 -m pip install --user --upgrade pillow numpy pandas openpyxl

echo "== verifying =="
ok=1
for c in pdftoppm tesseract python3; do
  if need "$c"; then echo "  ok: $c"; else echo "  MISSING: $c"; ok=0; fi
done
if need claude; then echo "  ok: claude CLI"
else echo "  MISSING: claude CLI — install Claude Code: https://docs.claude.com/en/docs/claude-code"; ok=0; fi
python3 - <<'PY'
import importlib.util as u
miss=[m for m in ("PIL","numpy","pandas","openpyxl") if not u.find_spec(m)]
print("  python deps OK" if not miss else "  MISSING python: "+", ".join(miss))
PY
[ "$ok" -eq 1 ] && echo "Setup complete." || { echo "Setup finished with missing pieces (see above)."; exit 1; }
