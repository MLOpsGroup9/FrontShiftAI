# FrontShiftAI - GCP Deployment Documentation

## 🎉 PROJECT STATUS: FULLY DEPLOYED TO PRODUCTION! 🎉

**Backend URL:** https://frontshiftai-backend-vvukpmzsxa-uc.a.run.app  
**Frontend URL:** https://frontshiftai-frontend-558177025654.us-central1.run.app  
**Status:** ✅ Full-Stack Application Live  
**Deployment Date:** December 4-5, 2025  
**Total Development Time:** ~16 hours across 7 sessions

---

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     GitHub Repository                        │
│  (Push to krishna-branch triggers deployment)               │
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
│  │   Cloud Run ✅   │◄────►│   Cloud Run ✅   │            │
│  │   (Backend)      │      │   (Frontend)     │            │
│  │   LIVE & RUNNING │      │   LIVE & RUNNING │            │
│  │ • FastAPI        │      │ • React + Vite   │            │
│  │ • LangGraph      │      │ • Nginx          │            │
│  │ • Mercury API    │      │ • Tailwind CSS   │            │
│  │ • Port 8080      │      │ • Port 80        │            │
│  └────┬─────────────┘      └──────────────────┘            │
│       │                                                     │
│       │ Downloads at startup (production):                 │
│       └────► GCS: ChromaDB Vector Store (tar.gz)           │
│                                                             │
│  ┌──────────────────┐      ┌──────────────────┐           │
│  │  Cloud SQL ✅    │      │  Cloud Storage ✅│           │
│  │  (PostgreSQL)    │      │  (GCS Bucket)    │           │
│  │                  │      │                  │           │
│  │ • User data      │      │ • ChromaDB       │           │
│  │ • PTO requests   │      │ • chroma_db.tar  │           │
│  │ • HR tickets     │      │ • Documents      │           │
│  └──────────────────┘      └──────────────────┘           │
│                                                             │
│  ┌──────────────────┐      ┌──────────────────┐           │
│  │ Artifact Registry│      │  Secret Manager  │           │
│  │  (2 Repositories)│      │   (6 Secrets) ✅ │           │
│  └──────────────────┘      └──────────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

### Application Layer
- **Backend:** FastAPI + Python 3.12 ✅
- **Frontend:** React 18 + Vite + Tailwind CSS ✅
- **AI Agents:** LangGraph workflows (PTO, HR Ticket, Website Extraction) ✅
- **LLMs:** Mercury Labs API (primary) ✅

### Data Layer
- **Vector Store:** ChromaDB (tar.gz from GCS, pre-cached embedding model) ✅
- **Relational DB:** PostgreSQL 15 on Cloud SQL ✅
- **Object Storage:** Google Cloud Storage ✅

### Infrastructure
- **CI/CD:** GitHub Actions (dual workflows for backend + frontend) ✅
- **Container Registry:** Google Artifact Registry (2 repositories) ✅
- **Compute:** Cloud Run (2 services, auto-scaling 0-10) ✅
- **Build:** Docker multi-stage builds (linux/amd64) ✅

### Security
- **Secrets:** Google Secret Manager (6 secrets) ✅
- **Authentication:** Workload Identity Federation (keyless) ✅
- **Database:** Unix socket connection to Cloud SQL ✅

---

## Completed Phases

### Phase 1: Infrastructure Setup ✅ COMPLETE
**Session 1 (Dec 2, 2025) - 2 hours**

- Created Cloud SQL PostgreSQL instance (db-f1-micro)
- Initialized database with 9 tables
- Seeded 19 companies with test data
- Installed Cloud SQL Proxy
- Created GCS bucket: `frontshiftai-data`
- Uploaded ChromaDB as `chroma_db.tar.gz`

### Phase 2: Docker Containerization ✅ COMPLETE
**Session 2 (Dec 2, 2025) - 3 hours**

- Created `Dockerfile.backend` with multi-stage build
- Port 8080 configuration (Cloud Run requirement)
- Created `docker-compose.yml` for local testing
- Fixed module import issues
- Successfully tested containers

### Phase 2.5: Integration Testing ✅ COMPLETE
**Session 3 (Dec 3, 2025) - 1 hour**

- Tested local SQLite (auto-detection working)
- Tested Cloud SQL via proxy
- Verified all API endpoints
- Confirmed multi-tenancy working

### Phase 3: GitHub Actions CI/CD ✅ COMPLETE
**Session 5 (Dec 3, 2025) - 2 hours**

- Enabled required GCP APIs
- Created Artifact Registry repositories (backend + frontend)
- Configured Workload Identity Federation
- Created service accounts with proper permissions
- Stored 6 secrets in Secret Manager
- Created backend deployment workflow
- Created frontend deployment workflow

### Phase 4: Backend Deployment ✅ COMPLETE
**Session 6 (Dec 4, 2025) - 4 hours**

**Issues Resolved:**

#### Issue 1: Secret Manager Permissions ❌ → ✅
**Problem:** Cloud Run service account couldn't access secrets

**Solution:**
```bash
gcloud projects add-iam-policy-binding frontshiftai \
  --member="serviceAccount:558177025654-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

#### Issue 2: Port Mismatch ❌ → ✅
**Problem:** Container listening on 8000, Cloud Run expects 8080

**Solution:** Updated Dockerfile:
```dockerfile
EXPOSE 8080
CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:8080"]
```

**Note:** Local development uses 8000, Cloud Run requires 8080

#### Issue 3: ChromaDB Download ❌ → ✅
**Problem:** ChromaDB not downloading from GCS

**Solution:** Updated `data_loader.py` to download and extract tar.gz

#### Issue 4: GitHub Actions Disk Space ❌ → ✅
**Problem:** Build failed with "no space left on device"

**Solution:** Added cleanup step to workflow:
```yaml
- name: Free up disk space
  run: |
    sudo rm -rf /usr/share/dotnet
    sudo rm -rf /opt/ghc
    docker system prune -af
```

**Deployment Success:**
- URL: https://frontshiftai-backend-vvukpmzsxa-uc.a.run.app
- Memory: 2Gi
- CPU: 2 cores
- Auto-scaling: 0-10 instances
- Status: ✅ LIVE

### Phase 5: Frontend Deployment ✅ COMPLETE
**Session 7 (Dec 5, 2025) - 4 hours**

**Accomplishments:**

#### 1. Frontend Build Configuration ✅
- Created `.env` for local development
- Created `.env.production` for Cloud Run
- Configured production backend URL
- Built optimized production bundle

#### 2. Nginx Configuration ✅
- Created `nginx.conf` with health check
- Configured static file serving
- Set up proper MIME types

#### 3. Frontend Dockerfile ✅
Created `Dockerfile.frontend`:
- Multi-stage build (Node 18 + Nginx Alpine)
- Production bundle optimization
- Port 80 exposure
- Health check endpoint

#### 4. Artifact Registry ✅
```bash
gcloud artifacts repositories create frontshiftai-frontend \
  --repository-format=docker \
  --location=us-central1
```

#### 5. Deployment Workflow ✅
Created `.github/workflows/deploy-frontend.yml`:
- Triggers on push to krishna-branch
- Builds and deploys automatically
- Memory: 512Mi, CPU: 1
- Auto-scaling: 0-10 instances

**Deployment Success:**
- URL: https://frontshiftai-frontend-558177025654.us-central1.run.app
- Status: ✅ LIVE
- Features: Login, Chat, PTO Requests, HR Tickets

### Phase 6: ChromaDB & HuggingFace Integration ✅ COMPLETE
**Session 7 (Dec 5, 2025) - Continued**

**Issues Resolved:**

#### Issue 5: ChromaDB tar.gz Missing ❌ → ✅
**Problem:** ChromaDB stored as individual files, not tar.gz

**Solution:**
```bash
cd data_pipeline/data
tar -czf chroma_db.tar.gz vector_db/
gsutil cp chroma_db.tar.gz gs://frontshiftai-data/
```

#### Issue 6: Missing CHROMA_REMOTE_URI ❌ → ✅
**Problem:** Backend didn't know where to download ChromaDB

**Solution:** Added to deployment workflow:
```yaml
--set-env-vars ENVIRONMENT=production,GENERATION_BACKEND=mercury,CHROMA_REMOTE_URI=gs://frontshiftai-data/chroma_db.tar.gz \
```

#### Issue 7: HuggingFace Rate Limiting ❌ → ✅
**Problem:** 429 Too Many Requests from HuggingFace

**Solution:**
```bash
# Created HF token and stored in Secret Manager
echo -n "hf_..." | gcloud secrets create HF_TOKEN --data-file=-

# Updated Cloud Run to mount HF_TOKEN
gcloud run services update frontshiftai-backend \
  --set-secrets=HF_TOKEN=HF_TOKEN:latest
```

#### Issue 8: Dockerfile Directory Structure ❌ → ✅
**Problem:** Wrong directory created for ChromaDB

**Solution:** Changed Dockerfile from:
```dockerfile
RUN mkdir -p /app/models /app/data/vector_db
```
To:
```dockerfile
RUN mkdir -p /app/models /app/data_pipeline/data
```

#### Issue 9: Embedding Model Download at Runtime ❌ → ✅
**Problem:** Model download at runtime caused delays and rate limits

**Solution:** Pre-download model during Docker build:
```dockerfile
# In builder stage
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

# Copy cache to final image
COPY --from=builder /root/.cache/huggingface /root/.cache/huggingface
ENV HF_HOME=/root/.cache/huggingface
```

**Result:** Model cached in Docker image, no runtime download needed!

---

## Current Production Status

### Live Services ✅

| Service | URL | Status |
|---------|-----|--------|
| Backend API | https://frontshiftai-backend-vvukpmzsxa-uc.a.run.app | ✅ LIVE |
| Frontend UI | https://frontshiftai-frontend-558177025654.us-central1.run.app | ✅ LIVE |
| API Docs | https://frontshiftai-backend-vvukpmzsxa-uc.a.run.app/docs | ✅ LIVE |

### Infrastructure ✅

| Component | Status | Details |
|-----------|--------|---------|
| Cloud SQL | ✅ Running | PostgreSQL 15, db-f1-micro |
| Cloud Storage | ✅ Active | ChromaDB tar.gz uploaded |
| Artifact Registry | ✅ Active | 2 repositories (backend + frontend) |
| Secret Manager | ✅ Active | 6 secrets stored |
| Cloud Run Backend | ✅ Live | Auto-scaling 0-10 instances |
| Cloud Run Frontend | ✅ Live | Auto-scaling 0-10 instances |

### Features Working ✅

- ✅ User authentication (JWT)
- ✅ Multi-tenant data isolation (19 companies)
- ✅ AI chat with unified agent router
- ✅ PTO request management
- ✅ HR ticket system
- ✅ RAG with ChromaDB vector store
- ✅ Mercury Labs API integration
- ✅ Website extraction fallback
- ✅ Chat history persistence
- ✅ Role-based access control

---

## Secret Manager Configuration

### All Secrets (6 total)

| Secret Name | Purpose | Status |
|-------------|---------|--------|
| `GROQ_API_KEY` | Groq API (fallback LLM) | ✅ Active |
| `BRAVE_API_KEY` | Brave Search API | ✅ Active |
| `JWT_SECRET_KEY` | JWT token signing | ✅ Active |
| `INCEPTION_API_KEY` | Mercury Labs API | ✅ Active |
| `DATABASE_URL` | PostgreSQL connection | ✅ Active |
| `HF_TOKEN` | HuggingFace API token | ✅ Active |

### Service Account Permissions

**GitHub Actions Service Account:**
- `github-actions@frontshiftai.iam.gserviceaccount.com`
- Roles: storage.admin, artifactregistry.writer, run.admin, iam.serviceAccountUser, cloudsql.client

**Cloud Run Runtime Service Account:**
- `558177025654-compute@developer.gserviceaccount.com`
- Roles: secretmanager.secretAccessor, cloudsql.client

---

## GitHub Actions Workflows

### Backend Deployment (deploy-backend.yml)

**Trigger:**
```yaml
on:
  push:
    branches:
      - krishna-branch
    paths:
      - 'backend/**'
      - 'chat_pipeline/**'
      - 'data_pipeline/**'
      - 'Dockerfile.backend'
      - '.github/workflows/deploy-backend.yml'
```

**Key Steps:**
1. Free up disk space (cleanup)
2. Authenticate via Workload Identity
3. Build Docker image with pre-cached embedding model
4. Push to Artifact Registry
5. Deploy to Cloud Run with all secrets and env vars

**Environment Variables:**
```yaml
ENVIRONMENT=production
GENERATION_BACKEND=mercury
CHROMA_REMOTE_URI=gs://frontshiftai-data/chroma_db.tar.gz
```

**Secrets Mounted:**
- GROQ_API_KEY, BRAVE_API_KEY, JWT_SECRET_KEY
- INCEPTION_API_KEY, DATABASE_URL, HF_TOKEN

### Frontend Deployment (deploy-frontend.yml)

**Trigger:**
```yaml
on:
  push:
    branches:
      - krishna-branch
```

**Key Steps:**
1. Authenticate via Workload Identity
2. Build React production bundle
3. Build Nginx container
4. Push to Artifact Registry
5. Deploy to Cloud Run

**Configuration:**
- Memory: 512Mi
- CPU: 1
- Port: 80
- Min instances: 0 (scales to zero)
- Max instances: 10

---

## Deployment Optimizations

### Backend Optimizations

**1. Pre-cached Embedding Model:**
```dockerfile
# Download model during build (not runtime!)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

# Copy cache to final image
COPY --from=builder /root/.cache/huggingface /root/.cache/huggingface
```

**Benefits:**
- No runtime download delays
- No HuggingFace rate limit issues
- Faster cold starts
- Consistent performance

**2. ChromaDB as Single Archive:**
- Stored as `chroma_db.tar.gz` (~500MB compressed)
- Single download instead of many small files
- Faster startup, fewer GCS API calls

**3. Disk Space Management:**
- GitHub Actions cleanup before build
- Frees ~14GB for large Docker builds

### Frontend Optimizations

**1. Multi-stage Build:**
- Build stage: Node 18 Alpine
- Production stage: Nginx Alpine
- Final image: ~50MB

**2. Production Environment:**
- Separate `.env.production` with Cloud Run backend URL
- Optimized Vite build with code splitting

**3. Nginx Configuration:**
- Static file serving optimized
- Health check endpoint
- Proper MIME type handling

---

## Cost Breakdown

### Monthly Costs (After Free Credits)

| Service | Configuration | Monthly Cost |
|---------|---------------|--------------|
| Cloud SQL | db-f1-micro (PostgreSQL 15) | ~$10 |
| Cloud Storage | ChromaDB tar.gz + data (~600MB) | ~$0.02 |
| Cloud Run Backend | 2Gi RAM, 2 CPU, scales to 0 | ~$0-2 |
| Cloud Run Frontend | 512Mi RAM, 1 CPU, scales to 0 | ~$0-1 |
| Artifact Registry | Docker images (~2GB total) | ~$0.20 |
| Secret Manager | 6 secrets | ~$0.01 |
| **Total** | | **~$10-13/month** |

**With $300 Free Credits:** FREE for ~23-30 months! 🎉

---

## Testing & Validation

### Production Testing Results ✅

**Health Checks:**
```bash
curl https://frontshiftai-backend-vvukpmzsxa-uc.a.run.app/health
# Response: {"status":"healthy","database":"connected","service":"backend"}

curl https://frontshiftai-frontend-558177025654.us-central1.run.app/health
# Response: healthy
```

**Authentication:**
```bash
curl -X POST .../api/auth/login -d '{"email":"user@crousemedical.com","password":"password123"}'
# Response: {"access_token":"...","company":"Crouse Medical Practice"}
```

**RAG System:**
```bash
curl -X POST .../api/chat/message -d '{"message":"What is the PTO policy?"}'
# Response: Full PTO policy from handbook with sources
```

**All Tests Passed:** ✅
- Frontend loads and displays correctly
- Login authentication working
- RAG queries returning handbook information
- PTO agent creating requests
- HR ticket agent working
- Multi-tenancy confirmed
- Database queries successful
- Auto-scaling verified

---

## Session Summary

| Session | Date | Focus | Time | Status |
|---------|------|-------|------|--------|
| 1 | Dec 2 (AM) | Cloud SQL setup | 2h | ✅ |
| 2 | Dec 2 (PM) | Docker containerization | 3h | ✅ |
| 3 | Dec 3 (AM) | Integration testing | 1h | ✅ |
| 4 | Dec 3 (PM) | Mercury API integration | 2h | ✅ |
| 5 | Dec 3 (Eve) | GitHub Actions setup | 2h | ✅ |
| 6 | Dec 4 (PM) | Backend deployment | 4h | ✅ |
| 7 | Dec 5 (AM) | Frontend deployment & fixes | 4h | ✅ |
| **Total** | | | **18h** | ✅ |

---

## Commands Reference

### Backend Commands

**View Logs:**
```bash
gcloud run services logs read frontshiftai-backend --region=us-central1 --limit=100
```

**Update Service:**
```bash
gcloud run services update frontshiftai-backend \
  --region=us-central1 \
  --memory=4Gi
```

**Redeploy:**
```bash
gcloud run deploy frontshiftai-backend \
  --image=us-central1-docker.pkg.dev/frontshiftai/frontshiftai-backend/backend:latest \
  --region=us-central1
```

### Frontend Commands

**View Logs:**
```bash
gcloud run services logs read frontshiftai-frontend --region=us-central1 --limit=100
```

**Redeploy:**
```bash
gcloud run deploy frontshiftai-frontend \
  --image=us-central1-docker.pkg.dev/frontshiftai/frontshiftai-frontend/frontend:latest \
  --region=us-central1
```

### ChromaDB Management

**Update ChromaDB:**
```bash
# After running data pipeline locally
cd data_pipeline/data
tar -czf chroma_db.tar.gz vector_db/
gsutil cp chroma_db.tar.gz gs://frontshiftai-data/

# Restart backend to download new version
gcloud run services update frontshiftai-backend --region=us-central1
```

---

## What We Built

### Infrastructure
- Cloud SQL PostgreSQL database
- Cloud Storage for ChromaDB
- Artifact Registry (2 repositories)
- Secret Manager (6 secrets)
- Workload Identity Federation

### Application
- FastAPI backend with 3 AI agents
- React frontend with Tailwind CSS
- Multi-tenant architecture (19 companies)
- JWT authentication
- PTO request management
- HR ticket system
- RAG-powered chat

### DevOps
- Dual GitHub Actions workflows
- Automated deployments
- Docker containerization
- Cloud Run serverless hosting
- Auto-scaling infrastructure
- Pre-cached models for performance

---

## What's Next (Optional)

### Phase 7: Model Validation & Bias Detection
**Time:** 4-6 hours | **Priority:** HIGH (coursework)

- Implement model evaluation metrics
- Compare Mercury vs Groq performance
- Data slicing by company
- Bias detection reports
- Visualizations

### Phase 8: Monitoring Dashboard
**Time:** 3-4 hours | **Priority:** HIGH (coursework requirement)

- Admin monitoring page at `/admin/monitoring`
- Request counts, response times, error rates
- Agent usage breakdown
- Real-time metrics

### Phase 9: Data Drift Detection
**Time:** 3-4 hours | **Priority:** HIGH (coursework)

- Evidently AI integration
- Data drift monitoring
- Automated reports

---

## Resources

### Live URLs
- **Frontend:** https://frontshiftai-frontend-558177025654.us-central1.run.app
- **Backend:** https://frontshiftai-backend-vvukpmzsxa-uc.a.run.app
- **API Docs:** https://frontshiftai-backend-vvukpmzsxa-uc.a.run.app/docs

### GitHub
- **Repository:** https://github.com/MLOpsGroup9/FrontShiftAI
- **Actions:** https://github.com/MLOpsGroup9/FrontShiftAI/actions

### GCP Console
- **Cloud Run:** https://console.cloud.google.com/run?project=frontshiftai
- **Cloud SQL:** https://console.cloud.google.com/sql/instances?project=frontshiftai
- **Artifact Registry:** https://console.cloud.google.com/artifacts?project=frontshiftai
- **Secret Manager:** https://console.cloud.google.com/security/secret-manager?project=frontshiftai

---

**Last Updated:** December 5, 2025  
**Status:** 🎉 FULL-STACK APPLICATION LIVE IN PRODUCTION 🎉  
**Progress:** Infrastructure & Deployment Complete (~50% of total coursework)  
**Remaining:** MLOps features (model validation, monitoring, drift detection)