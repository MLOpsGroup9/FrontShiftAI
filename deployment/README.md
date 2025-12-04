# FrontShiftAI - GCP Deployment Progress

## Project Overview

**Goal:** Deploy FrontShiftAI (multi-tenant HR/PTO management system with AI agents) to Google Cloud Platform using Cloud Run, with automated CI/CD via GitHub Actions.

**Current Status:** ✅ Phase 1, 2, 3 Complete | ✅ Ready for Production Deployment 🚀

---

## Deployment Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                     GitHub Repository                        │
│  (Push to main branch triggers deployment)                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   GitHub Actions CI/CD                       │
│  • Authenticate via Workload Identity                        │
│  • Build Docker images (linux/amd64)                         │
│  • Push to Artifact Registry                                 │
│  • Deploy to Cloud Run                                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  Google Cloud Platform                       │
│                                                              │
│  ┌──────────────────┐      ┌──────────────────┐            │
│  │   Cloud Run      │      │   Cloud Run      │            │
│  │   (Backend)      │◄────►│   (Frontend)     │            │
│  │                  │      │    (Planned)     │            │
│  │ • FastAPI        │      │ • React + Nginx  │            │
│  │ • LangGraph      │      │                  │            │
│  │ • Mercury API    │      │                  │            │
│  └────┬─────────────┘      └──────────────────┘            │
│       │                                                     │
│       │ Downloads at startup (production):                 │
│       └────► GCS: ChromaDB Vector Store                    │
│                                                             │
│  ┌──────────────────┐      ┌──────────────────┐           │
│  │  Cloud SQL       │      │  Cloud Storage   │           │
│  │  (PostgreSQL)    │      │  (GCS Bucket)    │           │
│  │                  │      │                  │           │
│  │ • User data      │      │ • Models         │           │
│  │ • PTO requests   │      │ • Vector DB      │           │
│  │ • HR tickets     │      │ • Documents      │           │
│  └──────────────────┘      └──────────────────┘           │
│                                                             │
│  ┌──────────────────┐      ┌──────────────────┐           │
│  │ Artifact Registry│      │  Secret Manager  │           │
│  │  (Docker Images) │      │   (API Keys)     │           │
│  └──────────────────┘      └──────────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

### Application Layer
- **Backend:** FastAPI + Python 3.12
- **Frontend:** React + Nginx (planned)
- **AI Agents:** LangGraph workflows (PTO, HR Ticket, Website Extraction)
- **LLMs:** Mercury Labs API (primary), Groq API (fallback)

### Data Layer
- **Vector Store:** ChromaDB (file-based, synced from GCS)
- **Relational DB:** PostgreSQL 15 on Cloud SQL (with auto-detection fallback to SQLite)
- **Object Storage:** Google Cloud Storage (bucket: `frontshiftai-data`)

### Orchestration & Deployment
- **CI/CD:** GitHub Actions (auto-deploy on push to main)
- **Container Registry:** Google Artifact Registry
- **Compute:** Cloud Run (serverless containers, auto-scaling)
- **Build:** Docker multi-stage builds (linux/amd64)

### Security
- **Secrets:** Google Secret Manager
- **Authentication:** Workload Identity Federation (keyless)
- **Database:** Unix socket connection to Cloud SQL

### Monitoring (Planned)
- **Application Monitoring:** Cloud Monitoring
- **Data Drift Detection:** Evidently AI
- **Alerting:** Cloud Monitoring alerts + email notifications

---

## Phase 1: Infrastructure Setup ✅ COMPLETE

[Keep all Phase 1 content exactly as is from the previous README]

---

## Phase 2: Docker Containerization ✅ COMPLETE

[Keep all Phase 2 content exactly as is from the previous README]

---

## Phase 2.5: Complete Integration Testing ✅ COMPLETE

[Keep all Phase 2.5 content exactly as is from the previous README]

---

## Phase 3: GitHub Actions CI/CD ✅ COMPLETE

### Session 5 (December 3, 2025 - Evening)
**Time:** ~2 hours
**Focus:** GitHub Actions setup and Cloud Run deployment configuration

### What We Accomplished ✅

#### 1. GCP Infrastructure Setup
**Enabled Required APIs:**
- ✅ Artifact Registry API (`artifactregistry.googleapis.com`)
- ✅ Cloud Run API (`run.googleapis.com`)
- ✅ IAM Credentials API (`iamcredentials.googleapis.com`)
- ✅ Secret Manager API (`secretmanager.googleapis.com`)

**Created Artifact Registry Repository:**
- Repository: `frontshiftai-backend`
- Location: `us-central1`
- Format: Docker
- Purpose: Store backend Docker images for Cloud Run deployment

#### 2. Workload Identity Federation Setup ✅
**Created Workload Identity Pool:**
- Pool: `github-actions-pool`
- Location: `global`
- Purpose: Secure authentication between GitHub Actions and GCP without service account keys

**Created Workload Identity Provider:**
- Provider: `github-provider`
- Pool: `github-actions-pool`
- Issuer: `https://token.actions.githubusercontent.com`
- Attribute Mapping: Maps GitHub repository to GCP identity
- Attribute Condition: `assertion.repository_owner=='MLOpsGroup9'`
- Repository: `MLOpsGroup9/FrontShiftAI`

**Benefits:**
- ✅ No service account keys needed (more secure)
- ✅ GitHub Actions authenticates via OIDC tokens
- ✅ Automatic credential rotation
- ✅ Fine-grained access control
- ✅ Industry best practice for CI/CD

#### 3. Service Account Configuration ✅
**Created GitHub Actions Service Account:**
- Account: `github-actions@frontshiftai.iam.gserviceaccount.com`
- Purpose: Execute deployments from GitHub Actions workflows

**Granted IAM Permissions:**
```bash
roles/storage.admin              # Access GCS bucket for ChromaDB
roles/artifactregistry.writer    # Push Docker images to registry
roles/run.admin                  # Deploy and manage Cloud Run services
roles/iam.serviceAccountUser     # Run services as service account
roles/cloudsql.client            # Connect to Cloud SQL database
```

**Linked to GitHub Repository:**
- Repository: `MLOpsGroup9/FrontShiftAI`
- Authentication Method: Workload Identity Federation
- Scope: Repository-level access only
- Security: No downloadable keys, OIDC-based authentication

#### 4. Secret Manager Setup ✅
**Stored Production Secrets:**
| Secret Name | Purpose | Version |
|-------------|---------|---------|
| `GROQ_API_KEY` | Groq API credentials | latest |
| `BRAVE_API_KEY` | Brave Search API credentials | latest |
| `JWT_SECRET_KEY` | Secure random key for JWT tokens | latest |
| `INCEPTION_API_KEY` | Mercury Labs API credentials | latest |
| `DATABASE_URL` | PostgreSQL connection with Unix socket | latest |

**Secret Configuration:**
- Replication: Automatic (multi-region)
- Encryption: At rest and in transit
- Access: Via `secretAccessor` role
- Versioning: Enabled (can rollback)

**Database URL Format (Cloud Run):**
```bash
postgresql://postgres:MLOpsgroup%409@/frontshiftai?host=/cloudsql/frontshiftai:us-central1:frontshiftai-db
```
Note: Uses Unix socket (`/cloudsql/...`) instead of IP for better security and performance

#### 5. GitHub Repository Secrets ✅
**Added Configuration Secrets:**
| Secret Name | Value | Purpose |
|-------------|-------|---------|
| `GCP_PROJECT_ID` | `frontshiftai` | GCP project identifier |
| `GCP_PROJECT_NUMBER` | `558177025654` | Numerical project ID |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | `projects/558177025654/locations/global/workloadIdentityPools/github-actions-pool/providers/github-provider` | Workload Identity provider path |
| `GCP_SERVICE_ACCOUNT` | `github-actions@frontshiftai.iam.gserviceaccount.com` | Service account email |

**Purpose:**
- Configure GitHub Actions workflow
- Enable Workload Identity authentication
- Reference GCP resources securely

#### 6. GitHub Actions Workflow ✅
**Created `.github/workflows/deploy-cloudrun.yml`**

**Workflow Trigger:**
```yaml
on:
  push:
    branches:
      - main  # Only deploys when pushing to main
    paths:    # Only when these files change
      - 'backend/**'
      - 'chat_pipeline/**'
      - 'data_pipeline/**'
      - 'Dockerfile.backend'
      - '.github/workflows/deploy-cloudrun.yml'
```

**Workflow Jobs:**
1. **Checkout Code** - Gets latest code from repository
2. **Authenticate to GCP** - Uses Workload Identity Federation (keyless!)
3. **Setup Cloud SDK** - Installs gcloud CLI tools
4. **Configure Docker** - Authenticates to Artifact Registry
5. **Build Docker Image** - Builds for `linux/amd64` platform (Cloud Run compatible)
6. **Push to Artifact Registry** - Pushes both SHA-tagged and latest-tagged images
7. **Deploy to Cloud Run** - Deploys with full configuration
8. **Show Deployment URL** - Outputs public backend URL in logs

**Cloud Run Service Configuration:**
```yaml
Service Name: frontshiftai-backend
Region: us-central1
Memory: 2Gi
CPU: 2
Timeout: 300s (5 minutes)
Min Instances: 0 (scales to zero when idle)
Max Instances: 10 (auto-scales based on traffic)
Authentication: allow-unauthenticated (public API)

Environment Variables:
  - ENVIRONMENT=production
  - GENERATION_BACKEND=mercury

Secrets (from Secret Manager):
  - GROQ_API_KEY=GROQ_API_KEY:latest
  - BRAVE_API_KEY=BRAVE_API_KEY:latest
  - JWT_SECRET_KEY=JWT_SECRET_KEY:latest
  - INCEPTION_API_KEY=INCEPTION_API_KEY:latest
  - DATABASE_URL=DATABASE_URL:latest

Cloud SQL Connection:
  - Instance: frontshiftai:us-central1:frontshiftai-db
  - Method: Unix socket (/cloudsql/...)
```

**Multi-Platform Build:**
- Platform: `linux/amd64` (Intel/AMD compatible)
- Compatible with: Cloud Run servers
- Solves: ARM64/M4 Mac compatibility issue
- Build Time: ~3-5 minutes

#### 7. Deployment Workflow ✅

**Full Deployment Flow:**
```
Developer merges PR to main branch
    ↓
GitHub Actions workflow triggered automatically
    ↓
Authenticate to GCP via Workload Identity
    ↓
Build Docker image (linux/amd64)
    ↓
Push image to Artifact Registry
  - Tag 1: backend:{github.sha}
  - Tag 2: backend:latest
    ↓
Deploy to Cloud Run
  - Pull image from Artifact Registry
  - Configure environment variables
  - Mount secrets from Secret Manager
  - Connect to Cloud SQL via Unix socket
  - Set resource limits (2Gi RAM, 2 CPU)
    ↓
Cloud Run service starts
  1. Container initialization
  2. Sync ChromaDB from GCS (ensure_chroma_store)
  3. Connect to Cloud SQL database
  4. Read secrets from Secret Manager
  5. Initialize database tables
  6. Seed initial data (if needed)
  7. Start Gunicorn with Uvicorn workers
  8. Health check endpoint ready: /health
    ↓
Backend live at: https://frontshiftai-backend-*.run.app
```

**Deployment Time Estimate:**
- Build Docker image: ~3-5 minutes
- Push to Artifact Registry: ~1-2 minutes
- Deploy to Cloud Run: ~2-3 minutes
- **Total: ~6-10 minutes** per deployment

### Architecture Decisions ✅

**Why Workload Identity Federation?**
- ✅ Eliminates need for service account keys
- ✅ Automatic credential rotation (no manual key management)
- ✅ More secure (no keys to leak or steal)
- ✅ Industry best practice for CI/CD
- ✅ Reduces attack surface significantly

**Why Secret Manager?**
- ✅ Centralized secret storage
- ✅ Encrypted at rest and in transit
- ✅ Automatic versioning and rollback capability
- ✅ Fine-grained IAM access control
- ✅ Audit logs for secret access
- ✅ Better than environment variables in GitHub

**Why Cloud Run?**
- ✅ Serverless (no server management or patching)
- ✅ Auto-scaling (0 to 1000+ instances automatically)
- ✅ Pay per use (scales to zero when idle = $0)
- ✅ Automatic HTTPS with managed certificates
- ✅ Built-in load balancing and health checks
- ✅ Fast deployments (~2-3 minutes)
- ✅ Easy rollbacks to previous versions

**Why Artifact Registry?**
- ✅ Private Docker registry (secure)
- ✅ Integrated with Cloud Run
- ✅ Automatic vulnerability scanning
- ✅ Image lifecycle management
- ✅ Better than Docker Hub for GCP
- ✅ Regional storage (faster pulls)

**Why linux/amd64 Build?**
- ✅ Cloud Run uses Intel/AMD servers
- ✅ M4 Mac builds ARM64 by default (incompatible)
- ✅ GitHub Actions runners are x86_64
- ✅ Ensures production compatibility

### Current Status ✅

**Committed to `krishna-branch`:**
- ✅ Workflow file created (`.github/workflows/deploy-cloudrun.yml`)
- ✅ All GCP infrastructure configured
- ✅ All secrets stored securely in Secret Manager
- ✅ GitHub repository secrets added
- ✅ Service account permissions granted
- ✅ Workload Identity Federation configured
- ✅ Artifact Registry repository created
- ✅ Ready for deployment

**Not Yet Deployed:**
- ⏳ Waiting for Pull Request creation
- ⏳ Waiting for PR review and merge to `main`
- ⏳ GitHub Actions workflow will trigger on merge
- ⏳ First production deployment pending

**Next Steps to Deploy:**
1. Create Pull Request: `krishna-branch` → `main`
2. Review changes in PR
3. Merge PR to `main` branch
4. GitHub Actions automatically triggers
5. Monitor deployment in Actions tab
6. Verify backend at Cloud Run URL
7. Test all API endpoints

---

## Issues Resolved

[Keep all issues 1-8 from previous README]

### Issue 9: Workload Identity Provider Creation ❌ → ✅
**Problem:** `INVALID_ARGUMENT: The attribute condition must reference one of the provider's claims`

**Root Cause:** Missing attribute condition in provider configuration

**Solution:**
```bash
# Added attribute condition to restrict to specific GitHub org
--attribute-condition="assertion.repository_owner=='MLOpsGroup9'"
```

### Issue 10: Secret Manager API Not Enabled ❌ → ✅
**Problem:** `Secret Manager API has not been used in project`

**Solution:**
```bash
gcloud services enable secretmanager.googleapis.com
```

---

## Files Created/Modified (Complete List)

### New Files Created

**Root Level:**
1. `Dockerfile.backend` - Multi-stage backend container
2. `docker-compose.yml` - Local testing orchestration

**Backend:**
1. `backend/api/health.py` - Health check endpoint

**GitHub Workflows:**
1. `.github/workflows/deploy-cloudrun.yml` - Cloud Run deployment workflow

### Files Modified

[Keep all modifications from previous README]

---

## Testing Progress

### Phase 1: Infrastructure ✅
- [x] Cloud SQL instance created
- [x] Database initialized
- [x] Tables created (9 tables)
- [x] Initial data seeded (19 companies)
- [x] Cloud SQL Proxy working
- [x] ChromaDB confirmed in GCS

### Phase 2: Docker ✅
- [x] Dockerfile.backend created
- [x] Multi-stage build working
- [x] Image builds successfully (~680MB)
- [x] docker-compose.yml created
- [x] All services running
- [x] Health checks passing
- [x] Authentication tested

### Phase 2.5: Integration Testing ✅
- [x] Local SQLite tested (auto-detection)
- [x] Local PostgreSQL tested (Cloud SQL Proxy)
- [x] Docker PostgreSQL tested (docker-compose)
- [x] Database seeding verified
- [x] Multi-tenancy confirmed
- [x] All API endpoints verified
- [x] Database auto-detection verified
- [x] Mercury API integration tested

### Phase 3: GitHub Actions ✅
- [x] Artifact Registry repository created
- [x] Workload Identity Federation configured
- [x] Service account created and permissions granted
- [x] Secrets stored in Secret Manager
- [x] GitHub repository secrets configured
- [x] Workflow file created and pushed to branch
- [ ] Pull Request created (pending)
- [ ] Merged to main (pending)
- [ ] Backend deployed to Cloud Run (pending)
- [ ] Live backend tested (pending)

### Phase 4: Monitoring 🔄
- [ ] Cloud Monitoring integration
- [ ] Custom metrics configured
- [ ] Alert policies created
- [ ] Performance dashboards

---

## Commands Reference

[Keep all commands from previous README sections, then add:]

### GitHub Actions Commands

**View Workflow Runs:**
```bash
# In GitHub UI: Actions tab
# Or via GitHub CLI
gh run list --workflow=deploy-cloudrun.yml
```

**View Workflow Logs:**
```bash
# Get latest run
gh run view --log
```

**Manually Trigger Workflow:**
```bash
# Only if workflow_dispatch is enabled
gh workflow run deploy-cloudrun.yml
```

### Cloud Run Commands

**List Services:**
```bash
gcloud run services list --region=us-central1
```

**Describe Service:**
```bash
gcloud run services describe frontshiftai-backend --region=us-central1
```

**View Logs:**
```bash
gcloud run services logs read frontshiftai-backend --region=us-central1
```

**Update Service:**
```bash
gcloud run services update frontshiftai-backend \
  --region=us-central1 \
  --memory=4Gi  # Example: increase memory
```

**Rollback to Previous Revision:**
```bash
# List revisions
gcloud run revisions list --service=frontshiftai-backend --region=us-central1

# Rollback
gcloud run services update-traffic frontshiftai-backend \
  --to-revisions=REVISION_NAME=100 \
  --region=us-central1
```

### Secret Manager Commands

**List Secrets:**
```bash
gcloud secrets list
```

**View Secret Versions:**
```bash
gcloud secrets versions list GROQ_API_KEY
```

**Access Secret Value:**
```bash
gcloud secrets versions access latest --secret=GROQ_API_KEY
```

**Update Secret:**
```bash
echo -n "new_secret_value" | gcloud secrets versions add GROQ_API_KEY --data-file=-
```

---

## Environment Variables Summary

[Keep all environment sections from previous README]

---

## GitHub Actions Workflow Details

### Workflow File Location
`.github/workflows/deploy-cloudrun.yml`

### Environment Variables
```yaml
PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
REGION: us-central1
SERVICE_NAME: frontshiftai-backend
REPOSITORY: frontshiftai-backend
```

### Key Features
- ✅ Only runs on `main` branch
- ✅ Only runs when backend/pipeline code changes
- ✅ Uses Workload Identity (no service account keys!)
- ✅ Builds for linux/amd64 platform
- ✅ Tags images with both commit SHA and 'latest'
- ✅ Deploys with full Cloud Run configuration
- ✅ Mounts secrets from Secret Manager
- ✅ Connects to Cloud SQL via Unix socket
- ✅ Shows deployment URL in logs

### Workflow Permissions
```yaml
permissions:
  contents: read      # Read repository code
  id-token: write     # Generate OIDC token for Workload Identity
```

### Estimated Costs per Deployment
- GitHub Actions: FREE (2000 minutes/month free tier)
- Artifact Registry Storage: ~$0.10/GB/month
- Cloud Run Build: No charge (runs on GitHub)
- Data Egress: Minimal (GCP → GCP transfer)

---

## Cost Breakdown (Updated)

### Current Monthly Costs (After Free Credits)

**Cloud SQL:**
- Instance: db-f1-micro
- Cost: ~$10/month
- Storage: 10GB (auto-increase enabled)
- Backups: Automated daily at 3:00 AM

**Cloud Storage:**
- Model storage: 2GB
- Vector DB: ~500MB
- Documents: ~100MB
- Cost: ~$1/month

**Cloud Run:**
- First 2M requests/month: FREE
- First 360K GB-seconds: FREE
- Estimated: ~$5-10/month (backend, low-medium traffic)

**Artifact Registry:**
- First 0.5GB storage: FREE
- Estimated: ~$0.50/month per additional GB

**Secret Manager:**
- First 10,000 operations: FREE
- Estimated: ~$0.10/month per 10K operations

**Total New Monthly Costs:**
- Cloud SQL: ~$10/month
- Cloud Storage: ~$1/month
- Cloud Run: ~$5-10/month
- Artifact Registry: ~$0.50/month
- Secret Manager: ~$0.10/month
- **Grand Total: ~$17-22/month**

**With $300 Credits:** Still FREE for 13-17 months! 🎉

### Cost Optimization Tips
- ✅ Cloud Run scales to zero (pay only for requests)
- ✅ Use free tier limits (2M requests, 360K GB-seconds/month)
- ✅ Artifact Registry lifecycle policies (delete old images)
- ✅ Cloud SQL automatic storage increase (pay only for used)
- ✅ Secret Manager caching (reduce access operations)

---

## Session Summary

### Session 1 (Dec 2, 2025 - Morning)
**Time:** ~2 hours | **Focus:** Infrastructure setup
- Created Cloud SQL PostgreSQL instance
- Set up database and tables
- Installed Cloud SQL Proxy

### Session 2 (Dec 2, 2025 - Afternoon)
**Time:** ~3 hours | **Focus:** Docker containerization
- Created Dockerfile.backend
- Created docker-compose.yml
- Resolved module import issues
- Successfully tested full stack

### Session 3 (Dec 3, 2025 - Morning)
**Time:** ~1 hour | **Focus:** Integration testing
- Tested local and Docker PostgreSQL
- Verified database seeding
- Confirmed API endpoints working

### Session 4 (Dec 3, 2025 - Afternoon)
**Time:** ~2 hours | **Focus:** Mercury API integration
- Removed local LLaMA model dependencies
- Implemented database auto-detection
- Fixed ChromaDB integration
- Tested 3 scenarios successfully
- Optimized for production deployment

### Session 5 (Dec 3, 2025 - Evening)
**Time:** ~2 hours | **Focus:** GitHub Actions & Cloud Run
**Accomplished:**
- Enabled GCP APIs (Artifact Registry, Cloud Run, Secret Manager)
- Created Artifact Registry repository
- Configured Workload Identity Federation (keyless authentication)
- Created and configured GitHub Actions service account
- Stored all secrets in Secret Manager
- Added GitHub repository secrets
- Created GitHub Actions deployment workflow
- Pushed workflow to krishna-branch
- Ready for production deployment

**Total Time Investment:** ~10 hours (across 5 sessions)
**Status:** Phase 3 Complete ✅ | Ready for Production Deployment 🚀

---

## What Happens on First Deployment

When you merge to `main`, here's what will happen:

1. **GitHub Actions Triggers** (~1 second)
   - Workflow detects push to main with backend changes
   - Job starts on Ubuntu runner

2. **Authentication** (~5 seconds)
   - Exchanges GitHub OIDC token for GCP credentials
   - No keys involved - completely keyless!

3. **Build Phase** (~3-5 minutes)
   - Checks out code
   - Builds Docker image for linux/amd64
   - Multi-stage build optimizes image size

4. **Registry Push** (~1-2 minutes)
   - Authenticates to Artifact Registry
   - Pushes image with SHA and latest tags

5. **Deployment** (~2-3 minutes)
   - Cloud Run pulls image from Artifact Registry
   - Mounts secrets from Secret Manager
   - Connects to Cloud SQL via Unix socket
   - Sets environment variables
   - Starts container

6. **Container Startup** (~30-60 seconds)
   - Downloads ChromaDB from GCS
   - Connects to Cloud SQL database
   - Initializes database tables
   - Seeds initial data (if needed)
   - Starts Gunicorn server
   - Health check passes

7. **Live!** 🎉
   - Backend accessible at: `https://frontshiftai-backend-*.run.app`
   - All API endpoints ready
   - Auto-scales based on traffic
   - Logs available in Cloud Run console

**First deployment Total Time: ~6-10 minutes**
**Subsequent deployments: ~5-8 minutes** (cached layers)

---

## Resources & Documentation

### Official Documentation
- [Cloud Run](https://cloud.google.com/run/docs)
- [Cloud SQL for PostgreSQL](https://cloud.google.com/sql/docs/postgres)
- [Artifact Registry](https://cloud.google.com/artifact-registry/docs)
- [Secret Manager](https://cloud.google.com/secret-manager/docs)
- [Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation)
- [GitHub Actions](https://docs.github.com/en/actions)
- [Docker Multi-stage Builds](https://docs.docker.com/build/building/multi-stage/)

### FrontShiftAI Documentation
- Backend README: `backend/README.md`
- Agents README: `backend/agents/README.md`
- Data Pipeline: `data_pipeline/README.md`
- Chat Pipeline: `chat_pipeline/README.md`

### GCP Console Links
- [Cloud Run Services](https://console.cloud.google.com/run)
- [Artifact Registry](https://console.cloud.google.com/artifacts)
- [Secret Manager](https://console.cloud.google.com/security/secret-manager)
- [Cloud SQL Instances](https://console.cloud.google.com/sql/instances)
- [Cloud Storage](https://console.cloud.google.com/storage/browser/frontshiftai-data)
- [IAM & Admin](https://console.cloud.google.com/iam-admin)

### GitHub Links
- [Repository](https://github.com/MLOpsGroup9/FrontShiftAI)
- [Actions](https://github.com/MLOpsGroup9/FrontShiftAI/actions)
- [Secrets](https://github.com/MLOpsGroup9/FrontShiftAI/settings/secrets/actions)

---

**Last Updated:** December 3, 2025 (7:30 PM EST)  
**Status:** Phase 3 Complete ✅ | Ready for Production Deployment 🚀  
**Next Milestone:** Merge to main and deploy backend to Cloud Run  
**Deployment Status:** Pending PR merge to `main` branch