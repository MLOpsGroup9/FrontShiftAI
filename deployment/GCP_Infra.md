# FrontShiftAI - Google Cloud Platform Infrastructure

**Project:** FrontShiftAI Multi-Tenant HR/PTO Management  
**GCP Project ID:** frontshiftai  
**GCP Project Number:** 558177025654  
**Region:** us-central1  
**Last Updated:** December 5, 2025

---

## Overview

FrontShiftAI uses 7 core Google Cloud Platform services to provide a serverless, auto-scaling, production-grade application.

**Total Monthly Cost:** ~$10-13/month (FREE for 30 months with $300 credits)

---

## 1. Cloud Run (Serverless Compute)

### What It Is
Fully managed serverless platform that runs containerized applications without managing servers.

### How We Use It

**We have 2 Cloud Run services:**

#### Service 1: Backend API
- **Name:** `frontshiftai-backend`
- **URL:** https://frontshiftai-backend-vvukpmzsxa-uc.a.run.app
- **Image:** `us-central1-docker.pkg.dev/frontshiftai/frontshiftai-backend/backend:latest`
- **Port:** 8080
- **Memory:** 2Gi
- **CPU:** 2 cores
- **Timeout:** 300 seconds (5 minutes)
- **Scaling:** 0-10 instances (auto-scales based on traffic)
- **Cost:** ~$0-2/month (scales to zero when idle)

**What It Does:**
- Serves FastAPI backend
- Runs AI agents (PTO, HR Ticket, Website Extraction, RAG)
- Handles authentication (JWT)
- Processes chat messages
- Connects to Cloud SQL database
- Downloads ChromaDB from GCS on startup
- Calls Mercury Labs API for LLM responses

**Environment Variables:**
- `ENVIRONMENT=production`
- `GENERATION_BACKEND=mercury`
- `CHROMA_REMOTE_URI=gs://frontshiftai-data/chroma_db.tar.gz`

**Secrets Mounted:**
- GROQ_API_KEY, BRAVE_API_KEY, JWT_SECRET_KEY
- INCEPTION_API_KEY, DATABASE_URL, HF_TOKEN

#### Service 2: Frontend UI
- **Name:** `frontshiftai-frontend`
- **URL:** https://frontshiftai-frontend-558177025654.us-central1.run.app
- **Image:** `us-central1-docker.pkg.dev/frontshiftai/frontshiftai-frontend/frontend:latest`
- **Port:** 80
- **Memory:** 512Mi
- **CPU:** 1 core
- **Timeout:** 60 seconds
- **Scaling:** 0-10 instances
- **Cost:** ~$0-1/month

**What It Does:**
- Serves React frontend (built with Vite)
- Runs Nginx web server
- Serves static files (HTML, CSS, JS)
- Proxies API calls to backend

**Why Cloud Run?**
- ✅ No server management
- ✅ Auto-scaling (0 to thousands of instances)
- ✅ Pay only for actual usage
- ✅ Automatic HTTPS certificates
- ✅ Built-in load balancing
- ✅ Fast deployments (~2-3 minutes)
- ✅ Easy rollbacks

---

## 2. Cloud SQL (Managed Database)

### What It Is
Fully managed relational database service (PostgreSQL, MySQL, SQL Server).

### How We Use It

**Instance Details:**
- **Name:** `frontshiftai-db`
- **Type:** PostgreSQL 15
- **Tier:** db-f1-micro (shared CPU, 0.6GB RAM)
- **Region:** us-central1
- **Storage:** 10GB SSD (auto-increase enabled)
- **Backups:** Automated daily at 3:00 AM UTC
- **Cost:** ~$10/month (biggest cost component)

**Connection Methods:**

**From Cloud Run (Production):**
- Unix socket: `/cloudsql/frontshiftai:us-central1:frontshiftai-db`
- More secure and faster than TCP
- No public IP needed

**From Local Development:**
- Cloud SQL Proxy: `./cloud-sql-proxy frontshiftai:us-central1:frontshiftai-db`
- Connects via TCP: `localhost:5432`

**What Data We Store:**
- Users (email, password hash, role, company)
- Companies (name, domain, handbook URL)
- PTO requests (dates, status, approvals)
- PTO balances (total, used, pending days)
- HR tickets (subject, description, status, queue)
- Chat conversations (chat history)
- Chat messages (user/assistant messages)
- Agent logs (execution tracking)

**9 Tables Total:**
- `companies`, `users`, `pto_requests`, `pto_balances`
- `hr_tickets`, `conversations`, `messages`
- `company_holidays`, `company_blackout_dates`

**Why Cloud SQL?**
- ✅ Fully managed (automatic backups, updates, patches)
- ✅ High availability
- ✅ Automatic storage scaling
- ✅ Point-in-time recovery
- ✅ Secure connections (Unix socket)

---

## 3. Cloud Storage (Object Storage / GCS)

### What It Is
Scalable object storage for unstructured data (files, backups, archives).

### How We Use It

**Bucket Details:**
- **Name:** `frontshiftai-data`
- **Region:** us-central1
- **Storage Class:** Standard
- **Total Size:** ~600MB
- **Cost:** ~$0.02/month

**What We Store:**

**1. ChromaDB Vector Store:**
- **File:** `chroma_db.tar.gz` (~500MB compressed)
- **Location:** `gs://frontshiftai-data/chroma_db.tar.gz`
- **Contains:** Embeddings for 19 company handbooks
- **Usage:** Downloaded by backend on startup

**2. Data Pipeline Outputs:**
- `gs://frontshiftai-data/data/raw/` - Original PDF handbooks
- `gs://frontshiftai-data/data/parsed/` - Extracted text (Markdown)
- `gs://frontshiftai-data/data/chunked/` - Text chunks (JSONL)
- `gs://frontshiftai-data/data/validated/` - Validated chunks
- `gs://frontshiftai-data/data/vector_db/` - ChromaDB files (uncompressed)
- `gs://frontshiftai-data/data/bias_analysis/` - Bias reports

**How Backend Downloads ChromaDB:**
```python
# Uses gsutil (installed in Docker image)
subprocess.run(
    ["gsutil", "cp", "gs://frontshiftai-data/chroma_db.tar.gz", "/tmp/"],
    check=True
)

# Extract
with tarfile.open("/tmp/chroma_db.tar.gz", "r:gz") as tar:
    tar.extractall(path="/app/data_pipeline/data/")
```

**Why GCS?**
- ✅ Cheap storage (~$0.02/GB/month)
- ✅ Fast download speeds
- ✅ Versioning support
- ✅ Integrated with Cloud Run
- ✅ No need to rebuild Docker for data updates

---

## 4. Artifact Registry (Container Registry)

### What It Is
Managed repository for Docker images, packages, and artifacts.

### How We Use It

**We have 2 repositories:**

#### Repository 1: Backend Images
- **Name:** `frontshiftai-backend`
- **Location:** us-central1
- **Format:** Docker
- **Images Stored:**
  - `backend:latest` (always points to newest)
  - `backend:{git-sha}` (specific versions for rollback)
- **Image Size:** ~680MB
- **Cost:** ~$0.10/month

#### Repository 2: Frontend Images
- **Name:** `frontshiftai-frontend`
- **Location:** us-central1
- **Format:** Docker
- **Images Stored:**
  - `frontend:latest`
  - `frontend:{git-sha}`
- **Image Size:** ~50MB
- **Cost:** ~$0.05/month

**How It Works:**

**GitHub Actions:**
1. Builds Docker image
2. Tags with commit SHA + latest
3. Pushes to Artifact Registry
4. Cloud Run pulls image from registry

**Why Artifact Registry?**
- ✅ Private registry (secure)
- ✅ Integrated with Cloud Run
- ✅ Automatic vulnerability scanning
- ✅ Version control for images
- ✅ Fast pulls (same region as Cloud Run)
- ✅ Better than Docker Hub for GCP

---

## 5. Secret Manager (Secrets Storage)

### What It Is
Secure storage for API keys, passwords, certificates, and sensitive configuration.

### How We Use It

**We store 6 secrets:**

| Secret Name | Purpose | Where Used |
|-------------|---------|------------|
| `GROQ_API_KEY` | Groq API (fallback LLM) | Backend RAG fallback |
| `BRAVE_API_KEY` | Brave Search API | Website extraction agent |
| `JWT_SECRET_KEY` | JWT token signing | Backend authentication |
| `INCEPTION_API_KEY` | Mercury Labs API | Primary LLM for agents |
| `DATABASE_URL` | PostgreSQL connection | Backend database |
| `HF_TOKEN` | HuggingFace API token | Embedding model downloads |

**How Secrets Are Accessed:**

**In Cloud Run:**
```yaml
# Secrets are mounted as environment variables
--set-secrets GROQ_API_KEY=GROQ_API_KEY:latest,HF_TOKEN=HF_TOKEN:latest,...
```

**In Code:**
```python
import os
groq_key = os.getenv("GROQ_API_KEY")  # Reads from Secret Manager!
```

**Security Features:**
- Encrypted at rest and in transit
- Automatic versioning (can rollback)
- Access controlled via IAM
- Audit logs for all access
- Never stored in code or GitHub

**Why Secret Manager?**
- ✅ Centralized secret storage
- ✅ Automatic encryption
- ✅ Version control
- ✅ Fine-grained access control
- ✅ Audit logging
- ✅ No secrets in code!

---

## 6. IAM & Service Accounts (Authentication)

### What It Is
Identity and Access Management - controls who can access what in GCP.

### How We Use It

**We have 2 service accounts:**

#### Service Account 1: GitHub Actions
- **Email:** `github-actions@frontshiftai.iam.gserviceaccount.com`
- **Purpose:** Deploy from GitHub Actions (CI/CD)
- **Authentication:** Workload Identity Federation (no keys!)

**Roles:**
- `roles/storage.admin` - Upload/download from GCS
- `roles/artifactregistry.writer` - Push Docker images
- `roles/run.admin` - Deploy Cloud Run services
- `roles/iam.serviceAccountUser` - Act as service account
- `roles/cloudsql.client` - Connect to database

#### Service Account 2: Cloud Run Runtime
- **Email:** `558177025654-compute@developer.gserviceaccount.com`
- **Purpose:** Run the backend/frontend containers
- **Authentication:** Automatic (default compute account)

**Roles:**
- `roles/secretmanager.secretAccessor` - Read secrets
- `roles/cloudsql.client` - Connect to database

### Workload Identity Federation

**What It Is:** Keyless authentication between GitHub Actions and GCP.

**Traditional Approach (INSECURE):**
```
GitHub Actions → Download service account key → Use key → Security risk!
```

**Our Approach (SECURE):**
```
GitHub Actions → Request OIDC token → Exchange for GCP credentials → No keys!
```

**Components:**
- **Pool:** `github-actions-pool`
- **Provider:** `github-provider`
- **Issuer:** `https://token.actions.githubusercontent.com`
- **Condition:** Only `MLOpsGroup9` organization

**Why This Matters:**
- ✅ No service account keys to manage
- ✅ No keys to leak or steal
- ✅ Automatic credential rotation
- ✅ Industry best practice
- ✅ More secure than traditional keys

---

## 7. Cloud Monitoring (Observability)

### What It Is
Monitoring, logging, and alerting for GCP resources.

### How We Use It (Partial)

**Currently Active:**
- Cloud Run automatic metrics (requests, latency, errors)
- Cloud SQL metrics (connections, queries)
- Automatic logging for all services

**Planned:**
- Custom dashboards
- Alert policies
- Uptime checks
- Log-based metrics

**Available Metrics:**
- Request count per service
- Response time (p50, p95, p99)
- Error rates
- Memory usage
- CPU usage
- Database connections
- Container instance count

**Cost:** FREE (within generous free tier)

---

## Infrastructure Diagram

```
GitHub Repository (MLOpsGroup9/FrontShiftAI)
    |
    | Push to krishna-branch
    ▼
GitHub Actions (2 Workflows)
    |
    ├─► Backend Workflow
    |    |
    |    ├─ Authenticate (Workload Identity - no keys!)
    |    ├─ Build Docker image (linux/amd64)
    |    ├─ Push to Artifact Registry
    |    └─ Deploy to Cloud Run Backend
    |
    └─► Frontend Workflow
         |
         ├─ Authenticate (Workload Identity)
         ├─ Build Docker image
         ├─ Push to Artifact Registry
         └─ Deploy to Cloud Run Frontend

Cloud Run Backend (frontshiftai-backend)
    |
    ├─► Cloud SQL (PostgreSQL)
    |    └─ Unix socket connection (/cloudsql/...)
    |
    ├─► Cloud Storage (GCS)
    |    └─ Download chroma_db.tar.gz on startup
    |
    ├─► Secret Manager
    |    └─ Read 6 secrets (API keys, passwords)
    |
    └─► External APIs
         ├─ Mercury Labs API (primary LLM)
         ├─ Groq API (fallback LLM)
         ├─ Brave Search API (website extraction)
         └─ HuggingFace (embedding models)

Cloud Run Frontend (frontshiftai-frontend)
    |
    └─► Cloud Run Backend
         └─ All API calls proxied to backend
```

---

## Service-by-Service Breakdown

### Cloud Run Backend

**Startup Process:**
1. Container starts (pulls image from Artifact Registry)
2. Reads secrets from Secret Manager
3. Connects to Cloud SQL via Unix socket
4. Downloads ChromaDB from GCS (if not cached)
5. Extracts ChromaDB to `/app/data_pipeline/data/vector_db/`
6. Initializes database tables
7. Seeds initial data (if needed)
8. Starts Gunicorn server on port 8080
9. Health check passes → Container marked ready
10. Begins serving traffic

**Auto-Scaling:**
- **Min instances:** 0 (scales to zero when idle = $0)
- **Max instances:** 10 (can handle traffic spikes)
- **Scale-up trigger:** Incoming requests
- **Scale-down:** No requests for ~15 minutes
- **Cold start time:** ~30-60 seconds (ChromaDB download)

**Traffic Flow:**
```
User Request → Cloud Run Load Balancer → Backend Container → Response
```

### Cloud Run Frontend

**What's Deployed:**
- React app (built with Vite)
- Nginx web server
- Static files (HTML, CSS, JS)

**Nginx Configuration:**
- Serves static files from `/usr/share/nginx/html`
- Health check endpoint at `/health`
- All `/api` calls proxied to backend (not used currently)

**Build Process:**
- Node.js builds React app → `dist/` folder
- Nginx container serves `dist/` files
- Environment variable `VITE_API_URL` baked into build

---

### Cloud SQL

**Connection Details:**
```
Host: /cloudsql/frontshiftai:us-central1:frontshiftai-db (Unix socket)
Database: frontshiftai
User: postgres
Password: (stored in Secret Manager)
```

**Features Enabled:**
- Automated backups (daily at 3 AM UTC)
- Point-in-time recovery
- Automatic storage increase
- High availability (optional, not enabled to save cost)

**Database Size:**
- 9 tables
- 19 companies
- ~100 users
- ~50 PTO requests
- ~30 HR tickets
- Total: ~50MB (within 10GB limit)

---

### Cloud Storage (GCS)

**Bucket Structure:**
```
gs://frontshiftai-data/
├── chroma_db.tar.gz (500MB) ← Downloaded by backend
└── data/
    ├── raw/ (PDF handbooks)
    ├── parsed/ (Markdown text)
    ├── chunked/ (JSONL chunks)
    ├── validated/ (Validated chunks + reports)
    ├── vector_db/ (ChromaDB files - uncompressed)
    └── bias_analysis/ (Bias reports with visualizations)
```

**Access Pattern:**
- Backend downloads `chroma_db.tar.gz` on startup
- Data pipeline uploads new data after processing
- ChromaDB stays in container memory (not re-downloaded)

---

### Artifact Registry

**Registry URLs:**
```
us-central1-docker.pkg.dev/frontshiftai/frontshiftai-backend
us-central1-docker.pkg.dev/frontshiftai/frontshiftai-frontend
```

**Image Tagging Strategy:**
```
backend:latest             ← Always newest version
backend:abc123def          ← Specific commit SHA
backend:v1.0.0             ← Version tags (if used)
```

**Image Lifecycle:**
- New images pushed on every deployment
- Old images kept for rollback
- Can set retention policies (delete after 30 days)

---

### Secret Manager

**Security Model:**
```
Secret Creation:
echo -n "api_key" | gcloud secrets create SECRET_NAME --data-file=-

Access Control:
gcloud secrets add-iam-policy-binding SECRET_NAME \
  --member="serviceAccount:EMAIL" \
  --role="roles/secretmanager.secretAccessor"

Mount in Cloud Run:
--set-secrets SECRET_NAME=SECRET_NAME:latest
```

**Secrets Are:**
- Encrypted with Google-managed keys
- Replicated across regions
- Versioned (can rollback to old values)
- Audited (who accessed when)

---

### IAM & Workload Identity

**Authentication Flow (GitHub → GCP):**

```
1. Developer pushes to krishna-branch
2. GitHub Actions starts
3. GitHub generates OIDC token
4. Token sent to GCP Workload Identity Provider
5. Provider validates:
   - Token is from GitHub
   - Repository is MLOpsGroup9/FrontShiftAI
   - Request is legitimate
6. Issues temporary GCP credentials (1 hour)
7. GitHub Actions uses credentials
8. Credentials expire automatically
```

**No Keys Involved!** 🔐

---

## Data Flow Diagrams

### User Chat Request Flow

```
User (Browser)
    ↓
Frontend (Vercel or Cloud Run)
    ↓ HTTPS
Backend Cloud Run (FastAPI)
    ↓
Unified Agent Router
    ↓
├─► RAG Agent
│    ├─ Query ChromaDB (local vector store)
│    ├─ Retrieve relevant chunks
│    └─ Call Mercury API → Generate answer
│
├─► PTO Agent
│    ├─ Parse request (LLM)
│    ├─ Query Cloud SQL (check balance)
│    ├─ Create request in Cloud SQL
│    └─ Return confirmation
│
└─► HR Ticket Agent
     ├─ Parse request (LLM)
     ├─ Create ticket in Cloud SQL
     └─ Return ticket details
```

### Container Startup Flow

```
Cloud Run receives deployment
    ↓
Pull image from Artifact Registry
    ↓
Start container
    ↓
Read environment variables
    ↓
Mount secrets from Secret Manager
    ↓
Connect to Cloud SQL (Unix socket)
    ↓
Check: Does ChromaDB exist locally?
    ↓ NO (fresh container)
Download: gsutil cp gs://frontshiftai-data/chroma_db.tar.gz
    ↓
Extract: tar -xzf chroma_db.tar.gz
    ↓
Initialize database tables
    ↓
Seed initial data (if empty)
    ↓
Start Gunicorn → Health check passes
    ↓
Container READY - Accept traffic ✅
```

---

## Cost Optimization Strategies

### What We Do

**1. Cloud Run Scales to Zero:**
- No traffic = 0 instances = $0 cost
- Only pay for actual request processing

**2. Artifact Registry Cleanup:**
- Keep last 10 versions
- Delete old images after 30 days
- Saves storage costs

**3. Cloud SQL Auto-Increase:**
- Start with 10GB
- Only increase when needed
- Pay for actual usage

**4. Secret Manager Caching:**
- Secrets cached in application
- Reduce API calls to Secret Manager
- Stay within free tier

**5. Single Region:**
- Everything in us-central1
- No cross-region data transfer costs
- Faster communication

---

## Security Architecture

### Defense in Depth

**Layer 1: Network**
- HTTPS only (automatic certificates)
- No public IPs for Cloud SQL
- Unix socket connections

**Layer 2: Authentication**
- JWT tokens for API access
- Workload Identity (no service account keys)
- Password hashing with bcrypt

**Layer 3: Authorization**
- Role-based access control (user, company_admin, super_admin)
- Multi-tenancy isolation (companies can't see each other's data)
- Service account permissions (least privilege)

**Layer 4: Secrets**
- All secrets in Secret Manager
- Never in code or environment variables
- Automatic encryption

**Layer 5: Data**
- Database encrypted at rest
- TLS connections
- Automated backups

---

## Scalability

### Current Limits
- **Backend:** 0-10 instances (can handle ~1000 concurrent requests)
- **Frontend:** 0-10 instances (can handle ~10,000 concurrent users)
- **Database:** db-f1-micro (shared CPU, suitable for <100 concurrent connections)

### How to Scale Up

**If traffic increases:**

**Backend:**
```bash
gcloud run services update frontshiftai-backend \
  --region=us-central1 \
  --max-instances=50 \
  --cpu=4 \
  --memory=4Gi
```

**Database:**
```bash
# Upgrade to larger instance
gcloud sql instances patch frontshiftai-db \
  --tier=db-n1-standard-1
```

**Frontend:** Already handles high traffic (static files)

---

## Monitoring & Observability

### What's Automatically Available

**Cloud Run Metrics:**
- Request count
- Request latency
- Error rates (4xx, 5xx)
- Container CPU usage
- Container memory usage
- Instance count

**Cloud SQL Metrics:**
- Connection count
- Query performance
- Storage usage
- Backup status

**Logs:**
- Application logs (stdout/stderr)
- Access logs (requests/responses)
- Error logs (exceptions, failures)
- Audit logs (who did what)

**Where to View:**
- Cloud Console: https://console.cloud.google.com/run?project=frontshiftai
- Logs Explorer: https://console.cloud.google.com/logs?project=frontshiftai

---

## Disaster Recovery

### Backup Strategy

**Database:**
- Automated daily backups (3 AM UTC)
- 7-day retention
- Point-in-time recovery available

**ChromaDB:**
- Stored in GCS (11-nines durability)
- Can re-generate from data pipeline

**Docker Images:**
- All versions stored in Artifact Registry
- Can rollback to any previous deployment

**Secrets:**
- Versioned in Secret Manager
- Can rollback to previous values

### Rollback Procedures

**Rollback Cloud Run:**
```bash
# List revisions
gcloud run revisions list --service=frontshiftai-backend --region=us-central1

# Rollback
gcloud run services update-traffic frontshiftai-backend \
  --to-revisions=frontshiftai-backend-00005-abc=100 \
  --region=us-central1
```

**Restore Database:**
```bash
gcloud sql backups restore BACKUP_ID \
  --backup-instance=frontshiftai-db
```

---

## Summary

**We use 7 GCP services:**

1. **Cloud Run** (2 services) - Serverless compute for backend + frontend
2. **Cloud SQL** - Managed PostgreSQL database
3. **Cloud Storage** - ChromaDB and data pipeline storage
4. **Artifact Registry** - Docker image repository
5. **Secret Manager** - Secure secrets storage
6. **IAM & Service Accounts** - Authentication and access control
7. **Cloud Monitoring** - Logging and metrics

**Total Cost:** ~$10-13/month (mostly Cloud SQL)  
**With $300 Credits:** FREE for 23-30 months!

**Architecture Highlights:**
- Serverless (no servers to manage)
- Auto-scaling (0 to thousands of instances)
- Secure (keyless auth, encrypted secrets)
- Cost-effective (pay only for usage)
- Production-ready (backups, monitoring, rollbacks)

---

**Last Updated:** December 5, 2025  
**Status:** All services operational and production-ready ✅