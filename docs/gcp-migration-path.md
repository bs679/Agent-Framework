# GCP Migration Path

This document covers the steps to migrate AIOS/Pulse from local Docker to
Google Cloud Platform if remote access or scale becomes necessary.

---

## When to Consider Migrating

The local Docker deployment is the right choice for CHCA's current situation.
Consider migrating to GCP only if:

| Trigger | Threshold | Notes |
|---------|-----------|-------|
| Remote access needed | Any staff member needs agent access outside the office | IAP tunnels solve this without a full migration |
| Agent count grows | > 20 agents | Unlikely, but document the threshold |
| Availability requirements | Unacceptable downtime during server maintenance | GCP provides managed uptime |
| Disaster recovery | Backups must be off-site | Cloud Storage solves this without full migration |

**Recommendation:** Before committing to GCP, first try:
1. Remote access via IAP tunnel to the existing local server
2. Offsite backup to Cloud Storage (add to `scripts/backup.sh`)

A partial migration (backups + tunnel) may be all that's needed.

---

## Architecture on GCP

```
┌─────────────────────────────────────────────────────────────┐
│  GCP Project: chca-aios                                      │
│                                                              │
│  ┌─────────────────────┐    ┌──────────────────────────┐    │
│  │  Cloud Run / GKE    │    │  Cloud SQL (PostgreSQL)   │    │
│  │  Agent containers   │───▶│  + pgvector extension    │    │
│  │  (one per agent)    │    └──────────────────────────┘    │
│  └─────────────────────┘                                     │
│           │                  ┌──────────────────────────┐    │
│           ▼                  │  Secret Manager           │    │
│  ┌─────────────────────┐     │  chca-agents/*/           │    │
│  │  Cloud Run: Pulse   │────▶│  MEMORY_ENCRYPTION_KEY    │    │
│  │  (FastAPI)          │     │  ANTHROPIC_API_KEY        │    │
│  └─────────────────────┘     │  POSTGRES_PASSWORD        │    │
│           │                  └──────────────────────────┘    │
│           │                                                  │
│  ┌────────▼────────────┐    ┌──────────────────────────┐    │
│  │  Identity-Aware     │    │  Cloud Storage            │    │
│  │  Proxy (IAP)        │    │  aios-backups bucket      │    │
│  │  (no open internet) │    └──────────────────────────┘    │
│  └─────────────────────┘                                     │
└─────────────────────────────────────────────────────────────┘
                    │
           (IAP-authenticated)
                    │
         ┌──────────▼──────────┐
         │  Staff browsers     │
         │  Tauri desktop apps │
         └─────────────────────┘
```

---

## GCP Services to Use

| Local | GCP Equivalent | Notes |
|-------|---------------|-------|
| Docker containers | Cloud Run or GKE | Cloud Run simpler; GKE if >20 agents |
| PostgreSQL in Docker | Cloud SQL (PostgreSQL 16) | Enable pgvector via Cloud SQL extension |
| Redis in Docker | Memorystore for Redis | Or Cloud Run with sidecar Redis |
| `.env` files | Secret Manager | Per-agent secret prefix: `chca-agents/{agent_id}/` |
| Local disk backups | Cloud Storage | Automate via Cloud Scheduler |
| nginx + SSL | Cloud Load Balancing | Or IAP alone for access control |
| Local network | VPC (private) | Agents in private subnet |
| `docker exec` access | IAP SSH tunnel | No public SSH |

---

## Migration Steps (8 steps)

### Step 1 — Create GCP Project

```bash
gcloud projects create chca-aios --name="CHCA AIOS"
gcloud config set project chca-aios
```

Set billing account:
```bash
gcloud billing accounts list
gcloud billing projects link chca-aios --billing-account=XXXXXX-XXXXXX-XXXXXX
```

### Step 2 — Enable Required APIs

```bash
gcloud services enable \
    run.googleapis.com \
    sqladmin.googleapis.com \
    redis.googleapis.com \
    secretmanager.googleapis.com \
    iap.googleapis.com \
    artifactregistry.googleapis.com \
    cloudscheduler.googleapis.com \
    storage.googleapis.com \
    compute.googleapis.com
```

### Step 3 — Migrate Secrets to Secret Manager

For each agent and for the Pulse app:

```bash
# Pulse app secrets
echo -n "$POSTGRES_PASSWORD"  | gcloud secrets create pulse-postgres-password --data-file=-
echo -n "$ANTHROPIC_API_KEY"  | gcloud secrets create pulse-anthropic-api-key --data-file=-
echo -n "$NVIDIA_API_KEY"     | gcloud secrets create pulse-nvidia-api-key --data-file=-

# Per-agent secrets (repeat for each agent)
AGENT_ID="president-dave"
ENCRYPTION_KEY="$(cat agents/$AGENT_ID/.env | grep MEMORY_ENCRYPTION_KEY | cut -d= -f2)"
echo -n "$ENCRYPTION_KEY" | gcloud secrets create "chca-agents-${AGENT_ID}-memory-key" --data-file=-
```

Grant access to Cloud Run service accounts:
```bash
# Service account for Pulse
gcloud iam service-accounts create pulse-api \
    --display-name="Pulse API Service Account"

gcloud secrets add-iam-policy-binding pulse-postgres-password \
    --member="serviceAccount:pulse-api@chca-aios.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

See [upstream Secret Manager integration](https://github.com/openclaw/openclaw/pull/16663) for
OpenClaw-specific Secret Manager support.

### Step 4 — Push Docker Images to Artifact Registry

```bash
# Create registry
gcloud artifacts repositories create aios-images \
    --repository-format=docker \
    --location=us-east4 \
    --description="AIOS Docker images"

# Authenticate
gcloud auth configure-docker us-east4-docker.pkg.dev

# Build and push Pulse API image
docker build -t us-east4-docker.pkg.dev/chca-aios/aios-images/pulse:latest \
    -f docker/Dockerfile.pulse .
docker push us-east4-docker.pkg.dev/chca-aios/aios-images/pulse:latest

# Build and push agent image
docker build -t us-east4-docker.pkg.dev/chca-aios/aios-images/openclaw-agent:latest \
    -f docker/Dockerfile .
docker push us-east4-docker.pkg.dev/chca-aios/aios-images/openclaw-agent:latest
```

### Step 5 — Migrate Database to Cloud SQL

```bash
# Create Cloud SQL instance (PostgreSQL 16)
gcloud sql instances create aios-postgres \
    --database-version=POSTGRES_16 \
    --tier=db-g1-small \
    --region=us-east4 \
    --no-assign-ip \
    --network=default

# Create database and user
gcloud sql databases create aios_pulse --instance=aios-postgres
gcloud sql users create pulse --instance=aios-postgres --password="$(openssl rand -base64 32)"

# Enable pgvector
gcloud sql instances patch aios-postgres --database-flags=cloudsql.enable_pglogical=on
# Then via psql:
# CREATE EXTENSION IF NOT EXISTS vector;

# Export local PostgreSQL data
./scripts/backup.sh  # creates ./backups/YYYY-MM-DD/postgres.sql.gz

# Import to Cloud SQL
zcat ./backups/$(date +%Y-%m-%d)/postgres.sql.gz \
    | gcloud sql connect aios-postgres --user=pulse --database=aios_pulse
```

### Step 6 — Deploy Agent Containers to Cloud Run

For each agent, create a Cloud Run service:

```bash
AGENT_ID="president-dave"

gcloud run deploy "openclaw-${AGENT_ID}" \
    --image=us-east4-docker.pkg.dev/chca-aios/aios-images/openclaw-agent:latest \
    --region=us-east4 \
    --no-allow-unauthenticated \
    --service-account="agent-${AGENT_ID}@chca-aios.iam.gserviceaccount.com" \
    --set-secrets="MEMORY_ENCRYPTION_KEY=chca-agents-${AGENT_ID}-memory-key:latest" \
    --set-env-vars="AGENT_ID=${AGENT_ID},PLANE_NAME=chca-agents" \
    --memory=512Mi \
    --cpu=1 \
    --min-instances=1 \
    --max-instances=1
```

**Note on Ollama:** Ollama (GPU) cannot run in Cloud Run. Options:
- Keep Ollama on a local machine and expose it via a VPN/tunnel
- Use a GCP Compute Engine VM with NVIDIA GPU for Ollama
- Switch to a managed AI service for non-sensitive tasks (breaks the privacy model)

**Recommendation:** Keep Ollama on-premises connected via Cloud VPN or IAP tunnel.

### Step 7 — Configure Identity-Aware Proxy (IAP)

IAP provides authentication without exposing the application to the open internet.
Only users with IAP-secured-web-app-user role can access the service.

```bash
# Set up OAuth consent screen and IAP
# (requires manual steps in GCP Console — see:
# https://cloud.google.com/iap/docs/enabling-cloud-run)

# Grant access to specific users
gcloud projects add-iam-policy-binding chca-aios \
    --member="user:dave@chca1199ne.org" \
    --role="roles/iap.httpsResourceAccessor"
```

### Step 8 — Test All Workflows with GCP Endpoints

Before decommissioning local deployment:

```bash
# Health check
curl https://pulse-XXXX-ue.a.run.app/api/v1/health/full

# Run the Phase 9c smoke test suite against GCP
PULSE_BASE_URL=https://pulse-XXXX-ue.a.run.app pytest integrations/pulse/tests/

# Test agent check-ins for each agent
aios agents status --agent president-dave  # (update CLI to support GCP backend)

# Verify backups are running
# Check Cloud Scheduler for backup job
# Verify Cloud Storage bucket has today's backup
```

---

## Cost Estimates (8 agents)

| Service | Tier | Monthly Est. |
|---------|------|-------------|
| Cloud Run (8 agents + Pulse) | min-instances=1, f1-micro | ~$30–50 |
| Cloud SQL | db-g1-small | ~$25 |
| Memorystore (Redis) | 1GB basic | ~$30 |
| Cloud Storage | Backup storage | ~$1–5 |
| Secret Manager | <100 secrets | ~$1 |
| **Total** | | **~$90–110/month** |

This compares to $0/month for local Docker. The cost is only justified if
remote access or high availability is required.

---

## Terraform (Phase 10 Stretch Goal)

IaC definitions for the above will live in `provisioning/terraform/`. The
`aios` CLI is designed to be backend-agnostic — same `aios agents` commands,
different infrastructure. See CLAUDE.md §Agents Plane Architecture for the
full design context.

Key Terraform modules needed:
- `modules/gcp-project` — project, APIs, VPC
- `modules/cloud-sql` — PostgreSQL instance + pgvector
- `modules/agent-service` — Cloud Run service per agent
- `modules/secrets` — Secret Manager secrets per agent
- `modules/iap` — IAP configuration

---

## References

- [OpenClaw Agents Plane proposal (issue #17299)](https://github.com/openclaw/openclaw/issues/17299)
- [GCP Secret Manager integration (PR #16663)](https://github.com/openclaw/openclaw/pull/16663)
- [Cloud SQL pgvector documentation](https://cloud.google.com/sql/docs/postgres/extensions)
- [Identity-Aware Proxy for Cloud Run](https://cloud.google.com/iap/docs/enabling-cloud-run)
