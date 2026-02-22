#!/usr/bin/env bash
# =============================================================================
# AIOS/Pulse — Generate Self-Signed TLS Certificate (local LAN use)
#
# Creates a self-signed certificate for pulse.local (or a custom hostname).
# The certificate is valid for 10 years and trusted by the local machine.
#
# Usage:
#   ./scripts/generate-self-signed-cert.sh [hostname]
#
#   Default hostname: pulse.local
#
# Output:
#   /etc/nginx/ssl/pulse.local.crt   (or <hostname>.crt)
#   /etc/nginx/ssl/pulse.local.key   (or <hostname>.key)
#
# After running this script:
#   1. Reload nginx: sudo nginx -t && sudo systemctl reload nginx
#   2. Import pulse.local.crt into your browser / OS trust store
#      (see docs/ssl-setup.md for platform-specific instructions)
# =============================================================================

set -euo pipefail

HOSTNAME="${1:-pulse.local}"
CERT_DIR="/etc/nginx/ssl"
DAYS=3650  # 10 years

echo "Generating self-signed certificate for: $HOSTNAME"
echo "Output directory: $CERT_DIR"

# Create output directory
sudo mkdir -p "$CERT_DIR"

# Generate private key + self-signed certificate
sudo openssl req -x509 -nodes \
    -days "$DAYS" \
    -newkey rsa:4096 \
    -keyout "$CERT_DIR/${HOSTNAME}.key" \
    -out "$CERT_DIR/${HOSTNAME}.crt" \
    -subj "/C=US/ST=Connecticut/L=Hartford/O=CHCA/OU=AIOS/CN=${HOSTNAME}" \
    -addext "subjectAltName=DNS:${HOSTNAME},DNS:localhost,IP:127.0.0.1"

sudo chmod 600 "$CERT_DIR/${HOSTNAME}.key"
sudo chmod 644 "$CERT_DIR/${HOSTNAME}.crt"

echo ""
echo "Certificate generated:"
echo "  Certificate: $CERT_DIR/${HOSTNAME}.crt"
echo "  Private key: $CERT_DIR/${HOSTNAME}.key"
echo ""
echo "Certificate details:"
openssl x509 -in "$CERT_DIR/${HOSTNAME}.crt" -noout -subject -issuer -dates
echo ""
echo "Next steps:"
echo "  1. Update /etc/nginx/sites-available/aios-pulse to use Path B (self-signed)"
echo "     ssl_certificate     $CERT_DIR/${HOSTNAME}.crt;"
echo "     ssl_certificate_key $CERT_DIR/${HOSTNAME}.key;"
echo "  2. Test nginx config: sudo nginx -t"
echo "  3. Reload nginx:      sudo systemctl reload nginx"
echo "  4. Import the certificate into your OS/browser trust store:"
echo "     macOS:   sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain $CERT_DIR/${HOSTNAME}.crt"
echo "     Linux:   sudo cp $CERT_DIR/${HOSTNAME}.crt /usr/local/share/ca-certificates/ && sudo update-ca-certificates"
echo "     Windows: Import via certmgr.msc → Trusted Root Certification Authorities"
echo ""
echo "See docs/ssl-setup.md for full instructions."
