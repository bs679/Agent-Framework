# SSL/HTTPS Setup

Pulse runs on HTTP locally (port 8000) and is accessed by the Tauri desktop
app — no TLS required for that path.  If you need web access (browser, remote
staff, or external integrations), enable HTTPS via nginx.

---

## Path A — Let's Encrypt (real domain, internet-accessible)

Use this if you have a real domain pointing to the server and need remote access.

### Prerequisites

- A registered domain (e.g. `pulse.chca1199ne.org`)
- Ports 80 and 443 open in your firewall / router
- nginx installed: `sudo apt install nginx`
- certbot installed: `sudo apt install certbot python3-certbot-nginx`

### Steps

1. **Install nginx config**

   ```bash
   sudo cp nginx/sites-available/aios-pulse /etc/nginx/sites-available/aios-pulse
   sudo ln -s /etc/nginx/sites-available/aios-pulse /etc/nginx/sites-enabled/
   # Edit server_name to your real domain:
   sudo nano /etc/nginx/sites-available/aios-pulse
   sudo nginx -t && sudo systemctl reload nginx
   ```

2. **Obtain certificate**

   ```bash
   sudo certbot --nginx -d your-domain.example.com
   ```

   certbot will automatically update your nginx config to use the Let's Encrypt
   certificate and set up auto-renewal via a systemd timer.

3. **Edit nginx config** to switch to Path A (uncomment the Let's Encrypt lines,
   comment out Path B self-signed lines).

4. **Test renewal**

   ```bash
   sudo certbot renew --dry-run
   ```

5. **Verify**: visit `https://your-domain.example.com/api/v1/health` in a browser.

---

## Path B — Self-Signed Certificate (local LAN only)

Use this for office LAN access when you don't need a real domain. Browsers will
show a certificate warning that you'll need to accept once per device (or add to
trust store).

### Steps

1. **Generate the certificate** (requires sudo)

   ```bash
   ./scripts/generate-self-signed-cert.sh pulse.local
   ```

   This creates `/etc/nginx/ssl/pulse.local.crt` and `.key`.

2. **Install nginx config**

   ```bash
   sudo apt install nginx
   sudo cp nginx/sites-available/aios-pulse /etc/nginx/sites-available/aios-pulse
   sudo ln -s /etc/nginx/sites-available/aios-pulse /etc/nginx/sites-enabled/
   sudo nginx -t && sudo systemctl reload nginx
   ```

   The default config already uses Path B (self-signed).

3. **Add to /etc/hosts** on client machines (or configure DNS):

   ```
   192.168.1.x    pulse.local   # replace with server's LAN IP
   ```

4. **Import the certificate into your browser / OS trust store**

   | Platform | Command |
   |----------|---------|
   | macOS | `sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain /etc/nginx/ssl/pulse.local.crt` |
   | Ubuntu | `sudo cp /etc/nginx/ssl/pulse.local.crt /usr/local/share/ca-certificates/ && sudo update-ca-certificates` |
   | Windows | Open `certmgr.msc` → Trusted Root Certification Authorities → Import |
   | Firefox | Settings → Privacy → Certificates → View Certificates → Import |

5. **Verify**: visit `https://pulse.local/api/v1/health`

---

## Tauri Desktop App

The Tauri desktop app communicates with Pulse over HTTP on `localhost:8000`
directly — no nginx, no certificates needed. SSL is only required for browser
or remote access.

If the Tauri app is deployed to staff machines that access Pulse over the LAN:
update `PULSE_API_URL` in the `.env` to `https://pulse.local` and ensure the
self-signed cert is trusted on each staff machine.

---

## Nginx Config Location

```
nginx/
└── sites-available/
    └── aios-pulse    ← copy to /etc/nginx/sites-available/
```

---

## Port Reference

| Port | Service | Notes |
|------|---------|-------|
| 8000 | Pulse API (HTTP) | Direct access / Tauri |
| 80 | nginx HTTP | Redirects to 443 |
| 443 | nginx HTTPS | Reverse proxy to 8000 |
| 5432 | PostgreSQL | localhost only — not exposed |
| 6379 | Redis | localhost only — not exposed |
