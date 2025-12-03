# FrontShiftAI - GCP Deployment Progress

## Project Overview

**Goal:** Deploy FrontShiftAI (multi-tenant HR/PTO management system with AI agents) to Google Cloud Platform using Cloud Run, with automated CI/CD via GitHub Actions.

**Current Status:** ✅ Phase 1 & 2 Complete & Verified | ✅ Mercury API Integration Complete | 🔄 Ready for Phase 3 (GitHub Actions)

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
│  • Run tests                                                 │
│  • Build Docker images (backend + frontend)                  │
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
│  │                  │      │                  │            │
│  │ • FastAPI        │      │ • React + Nginx  │            │
│  │ • LangGraph      │      │                  │            │
│  │ • Mercury API    │      │                  │            │
│  └────┬─────────────┘      └──────────────────┘            │
│       │                                                     │
│       │ Downloads at startup (production only):            │
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
└─────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

### Application Layer
- **Backend:** FastAPI + Python 3.12
- **Frontend:** React + Nginx
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
- **Build:** Docker multi-stage builds

### Monitoring (Planned)
- **Application Monitoring:** Cloud Monitoring
- **Data Drift Detection:** Evidently AI
- **Alerting:** Cloud Monitoring alerts + email notifications

---

## Phase 1: Infrastructure Setup ✅ COMPLETE

### What We Accomplished

#### 1. Model & Data Storage Setup ✅
**ChromaDB Vector Store in GCS**
- Location: `gs://frontshiftai-data/data/vector_db/`
- Synced and ready for download
- Contains embeddings for all company handbooks

#### 2. PostgreSQL Database Setup ✅
**Created Cloud SQL Instance**
```bash
Instance name: frontshiftai-db
Version: PostgreSQL 15
Tier: db-f1-micro (free tier eligible)
Region: us-central1
Connection name: frontshiftai:us-central1:frontshiftai-db
Public IP: 34.56.213.8
Status: RUNNABLE
```

**Created Database**
```bash
Database name: frontshiftai
Tables: 9 tables created
  - users
  - companies (19 companies across 9 industries)
  - pto_requests
  - pto_balances
  - company_holidays
  - company_blackout_dates
  - hr_tickets
  - conversations
  - messages
Initial data: Seeded successfully
```

**Local Connection Setup**
- Cloud SQL Proxy installed: `/usr/local/bin/cloud-sql-proxy`
- PostgreSQL client (psql) installed via Homebrew
- Successfully tested local connection via proxy

#### 3. Backend Code Updates ✅

**Updated `backend/db/connection.py`**
```python
# Added PostgreSQL support with auto-detection
def get_database_url():
    """Auto-detect which database to use based on availability"""
    postgres_url = "postgresql://postgres:MLOpsgroup%409@127.0.0.1:5432/frontshiftai"
    sqlite_url = "sqlite:///./frontshiftai.db"
    
    # Try PostgreSQL first
    try:
        test_engine = create_engine(postgres_url, poolclass=NullPool)
        with test_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        test_engine.dispose()
        print("✅ Using PostgreSQL (Cloud SQL)")
        return postgres_url
    except Exception:
        print("⚠️  PostgreSQL unavailable, falling back to SQLite")
        return sqlite_url
```

**Features:**
- Uses `NullPool` for Cloud Run (connection pooling managed by Cloud SQL)
- Auto-detects PostgreSQL availability, falls back to SQLite
- `pool_pre_ping=True` verifies connections before use

**Updated `backend/requirements.txt`**
```txt
Added dependencies:
- psycopg2-binary==2.9.9        # PostgreSQL driver
- google-cloud-storage==2.14.0   # GCS integration
- google-cloud-secret-manager==2.16.4  # Secrets management
- gunicorn==21.2.0               # Production WSGI server
```

#### 4. GCP Project Configuration ✅
**Project Details**
- Project ID: `frontshiftai`
- Project Number: `558177025654`
- Default Region: `us-central1`
- Billing: Enabled with $300 free credits

**APIs Enabled**
- Cloud SQL Admin API (`sqladmin.googleapis.com`)
- Cloud Storage API (already enabled)

**Authentication**
- Application Default Credentials configured
- Cloud SQL Proxy authentication working
- Service account: `github-deploy@frontshiftai.iam.gserviceaccount.com`

---

## Phase 2: Docker Containerization ✅ COMPLETE

### What We Built

#### 1. Backend Dockerfile ✅
**Created `Dockerfile.backend` at project root**

**Multi-stage Build:**
```dockerfile
Stage 1 (builder): Compile Python dependencies
  - Base: python:3.12-slim
  - Installs: gcc, g++ (build tools)
  - Output: Compiled Python packages in /root/.local

Stage 2 (runtime): Application container
  - Base: python:3.12-slim
  - Installs: curl, gnupg, gsutil (Google Cloud CLI)
  - Copies: backend/, chat_pipeline/, data_pipeline/
  - Working directory: /app/backend
  - PYTHONPATH: /app:/app/backend
  - CMD: gunicorn with 1 worker
```

**Key Features:**
- Image size: ~680MB
- `gsutil` installed for ChromaDB sync from GCS
- Health check configured (curl to /health every 30s)
- Gunicorn + Uvicorn workers for production serving
- **No local model** - Uses Mercury API exclusively

#### 2. ChromaDB Integration ✅

**Uses `chat_pipeline/rag/data_loader.py`:**
```python
Function: ensure_chroma_store()
  - Syncs ChromaDB vector store from GCS in production
  - Skips download in development (uses local files)
  - Target: /app/data/vector_db/
```

**`backend/api/health.py`**
```python
Endpoint: GET /health
Returns: {"status": "healthy", "database": "connected", "service": "backend"}
Tests: Database connection with SELECT 1
Status Code: 200 (healthy) or 503 (unhealthy)
```

#### 3. Updated `backend/main.py` ✅

**Added Imports:**
```python
from api import health
from chat_pipeline.rag.data_loader import ensure_chroma_store
```

**Added Startup Event:**
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure ChromaDB is available in production
    if os.getenv("ENVIRONMENT") == "production":
        ensure_chroma_store()
    
    # Initialize database
    init_db()
    seed_initial_data()
    yield
```

**Key Changes:**
- Removed local LLaMA model download (uses Mercury API only)
- Only syncs ChromaDB from GCS in production
- Simplified startup process

#### 4. Database Auto-Detection ✅

**Features:**
- Automatically detects PostgreSQL availability
- Falls back to SQLite if PostgreSQL unavailable
- No manual configuration switching needed
- Respects `DATABASE_URL` environment variable override

**Usage:**
```bash
# With Cloud SQL Proxy running
✅ Using PostgreSQL (Cloud SQL)

# Without Cloud SQL Proxy
⚠️  PostgreSQL unavailable, falling back to SQLite
```

#### 5. Docker Compose Configuration ✅

**Created `docker-compose.yml` at project root**

**Services:**
```yaml
postgres:
  - Image: postgres:15-alpine
  - Port: 5432
  - Database: frontshiftai
  - Credentials: postgres/MLOpsgroup@9
  - Health check: pg_isready every 10s
  - Volume: postgres_data (persistent)

backend:
  - Build: Dockerfile.backend from root context
  - Port: 8000:8000 (host:container)
  - Database: postgresql://postgres:MLOpsgroup%409@postgres:5432/frontshiftai
  - Environment: development
  - GENERATION_BACKEND: mercury (forces Mercury API)
  - Depends on: postgres (waits for health check)
  - Workers: 1
```

---

## Phase 2.5: Complete Integration Testing ✅ COMPLETE

### Session 3 (December 3, 2025 - Morning)
**Time:** ~1 hour
**Focus:** End-to-end verification of PostgreSQL integration

**Tests Completed:**
- ✅ Local PostgreSQL (via Cloud SQL Proxy)
- ✅ Docker PostgreSQL (docker-compose)
- ✅ Database seeding verified (19 companies)
- ✅ All API endpoints working
- ✅ Multi-tenant data isolation confirmed

### Session 4 (December 3, 2025 - Afternoon)
**Time:** ~2 hours
**Focus:** Mercury API integration, database auto-detection, and final testing

### Changes Implemented ✅

#### 1. Removed Local LLaMA Model Dependencies
**Problem:** Local model not needed for Cloud Run (2GB file, slow downloads)

**Solution:**
- Deleted `/backend/utils/model_loader.py` (obsolete)
- Updated `chat_pipeline/rag/generator.py` to force Mercury API
- Modified startup to only sync ChromaDB
- Reduced Docker image complexity

**Benefits:**
- Faster Cloud Run startup times
- Smaller deployment footprint
- No model download delays

#### 2. Implemented Database Auto-Detection
**Problem:** Manual switching between SQLite and PostgreSQL

**Solution:**
- Added `get_database_url()` function
- Automatically tries PostgreSQL first
- Falls back to SQLite if unavailable
- No manual `.env` changes needed

**Testing Results:**
```bash
Local (no proxy):    ⚠️  PostgreSQL unavailable, falling back to SQLite
Local (with proxy):  ✅ Using PostgreSQL (Cloud SQL)
Docker Compose:      ✅ Using PostgreSQL (forced via env var)
```

#### 3. Fixed ChromaDB Integration
**Solution:**
- Changed import to `ensure_chroma_store` from `data_loader.py`
- Uses existing function from chat_pipeline
- Only runs in production environment

#### 4. Comprehensive Testing ✅

**Test 1: Local with SQLite (Auto-Detection)**
```bash
✅ Backend starts successfully
✅ Health check: {"status":"healthy"}
✅ Authentication working
✅ Database auto-detected as SQLite
```

**Test 2: Local with PostgreSQL (Cloud SQL Proxy)**
```bash
✅ Database auto-detected as PostgreSQL
✅ All API endpoints functional
✅ Health check passing
```

**Test 3: Docker Compose (Full Stack)**
```bash
✅ PostgreSQL container healthy
✅ Backend container running
✅ Database seeded (19 companies)
✅ Mercury API configured
```

### Architecture Decisions ✅

**LLM Backend:**
- **Production:** Mercury API only
- **Development:** Mercury API (configurable)
- **Rationale:** Simpler deployment, faster startup

**Database Strategy:**
- **Production:** PostgreSQL (Cloud SQL)
- **Local Development:** Auto-detect
- **Docker:** PostgreSQL (containerized)
- **Rationale:** Seamless local development

---

## Issues Resolved

### Issue 1: Module Import Error ❌ → ✅
**Problem:** `ModuleNotFoundError: No module named 'chat_pipeline'`

**Solution:** 
- Moved Dockerfile to project root as `Dockerfile.backend`
- Changed build context to `.` (root)
- Set `PYTHONPATH=/app:/app/backend`

### Issue 2: Duplicate ENUM Type Error ❌ → ✅
**Problem:** `duplicate key value violates unique constraint`

**Solution:** Reduced workers from 2 to 1 in Dockerfile

### Issue 3: Port Conflicts ❌ → ✅
**Solution:** Used `docker rm -f` and `--rm` flag for auto-cleanup

### Issue 4: Docker Daemon Crashes ❌ → ✅
**Solution:** Never kill `com.docke` processes (that's Docker itself!)

### Issue 5: Cloud SQL Proxy Authentication ❌ → ✅
**Solution:**
```bash
unset GOOGLE_APPLICATION_CREDENTIALS
gcloud auth application-default login
```

### Issue 6: Local Model Dependencies ❌ → ✅
**Solution:**
- Removed local LLaMA model support
- Configured Mercury API as primary
- Deleted obsolete `model_loader.py`

### Issue 7: Manual Database Switching ❌ → ✅
**Solution:**
- Implemented auto-detection in `connection.py`
- Zero-configuration database switching

### Issue 8: ChromaDB Import Error ❌ → ✅
**Solution:**
- Changed to `ensure_chroma_store` from `data_loader.py`
- Uses existing chat_pipeline function

---

## Files Created/Modified (Complete List)

### New Files Created

**Root Level:**
1. `Dockerfile.backend` - Multi-stage backend container
2. `docker-compose.yml` - Local testing orchestration

**Backend:**
1. `backend/api/health.py` - Health check endpoint

### Files Modified

**Backend:**
1. `backend/db/connection.py`
   - Added database auto-detection
   - PostgreSQL support with NullPool
   
2. `backend/main.py`
   - Removed local model download
   - Changed to `ensure_chroma_store` import
   - Simplified lifespan handler

3. `backend/requirements.txt`
   - Added PostgreSQL and GCS dependencies

4. `backend/.env`
   - Removed `DATABASE_URL` (auto-detected)

**Chat Pipeline:**
1. `chat_pipeline/rag/generator.py`
   - Forced Mercury API backend

**Docker:**
1. `docker-compose.yml`
   - Added `GENERATION_BACKEND=mercury`

### Files Deleted

1. `backend/Dockerfile` - Old Dockerfile
2. `backend/utils/model_loader.py` - Obsolete

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

### Phase 3: GitHub Actions 🔄
- [ ] Workflow file created
- [ ] GitHub secrets configured
- [ ] Workload Identity Federation setup
- [ ] Artifact Registry configured
- [ ] Backend deployed to Cloud Run

### Phase 4: Monitoring 🔄
- [ ] Cloud Monitoring integration
- [ ] Custom metrics configured
- [ ] Alert policies created

---

## Commands Reference

### Local Development

**Start Cloud SQL Proxy:**
```bash
cloud-sql-proxy frontshiftai:us-central1:frontshiftai-db
```

**Run Backend Locally:**
```bash
cd backend
python main.py
# Database auto-detected!
```

**Connect to Database:**
```bash
psql "host=127.0.0.1 port=5432 dbname=frontshiftai user=postgres password=MLOpsgroup@9"
```

### Docker Commands

**Build Backend Image:**
```bash
docker build -f Dockerfile.backend -t frontshiftai-backend:test .
```

**Run with Docker Compose:**
```bash
# Start services
docker-compose up --build

# Stop services
docker-compose down

# Fresh start
docker-compose down -v
docker-compose up --build
```

**Useful Commands:**
```bash
# List containers
docker ps -a

# View logs
docker logs backend-1

# Connect to PostgreSQL
docker exec -it $(docker ps -qf "name=postgres") psql -U postgres -d frontshiftai

# Remove stopped containers
docker container prune -f
```

### GCS Commands

**Verify Uploads:**
```bash
# Check vector DB
gsutil ls -r gs://frontshiftai-data/data/vector_db/

# Check all bucket contents
gsutil ls -r gs://frontshiftai-data/
```

**Sync ChromaDB:**
```bash
# Upload local to GCS
gsutil -m rsync -r data_pipeline/data/vector_db/ gs://frontshiftai-data/data/vector_db/

# Download GCS to local
gsutil -m rsync -r gs://frontshiftai-data/data/vector_db/ data_pipeline/data/vector_db/
```

### Cloud SQL Commands
```bash
# Describe instance
gcloud sql instances describe frontshiftai-db

# List databases
gcloud sql databases list --instance=frontshiftai-db

# Connect via gcloud
gcloud sql connect frontshiftai-db --user=postgres --database=frontshiftai
```

---

## Environment Variables Summary

### Local Development

**backend/.env:**
```bash
# Generation Settings (Mercury API)
GENERATION_BACKEND=mercury
INCEPTION_API_KEY=your_mercury_key

# Other API Keys
GROQ_API_KEY=your_groq_key
BRAVE_API_KEY=your_brave_key
JWT_SECRET_KEY=your_jwt_secret

# GCS Configuration
GCS_BUCKET_NAME=frontshiftai-data
CHROMA_REMOTE_URI=gs://frontshiftai-data/data/vector_db

# Database auto-detected (no configuration needed!)
```

### Docker Environment

**docker-compose.yml:**
```yaml
DATABASE_URL=postgresql://postgres:MLOpsgroup%409@postgres:5432/frontshiftai
ENVIRONMENT=development
GENERATION_BACKEND=mercury
GROQ_API_KEY=${GROQ_API_KEY}
BRAVE_API_KEY=${BRAVE_API_KEY}
JWT_SECRET_KEY=${JWT_SECRET_KEY}
INCEPTION_API_KEY=${INCEPTION_API_KEY}
```

### Production (Cloud Run)

**Environment Variables:**
```bash
ENVIRONMENT=production
GENERATION_BACKEND=mercury
GCS_BUCKET_NAME=frontshiftai-data
CHROMA_REMOTE_URI=gs://frontshiftai-data/data/vector_db
CHROMA_DIR=/app/data/vector_db
```

**Secrets (from Secret Manager):**
```bash
DATABASE_URL=postgresql://postgres:MLOpsgroup%409@/frontshiftai?host=/cloudsql/frontshiftai:us-central1:frontshiftai-db
GROQ_API_KEY=<secret>
BRAVE_API_KEY=<secret>
JWT_SECRET_KEY=<secret>
INCEPTION_API_KEY=<secret>
```

---

## Troubleshooting Guide

### Cloud SQL Proxy Issues

**Error:** `error getting credentials using GOOGLE_APPLICATION_CREDENTIALS`
```bash
# Solution
unset GOOGLE_APPLICATION_CREDENTIALS
gcloud auth application-default login
```

### Docker Build Issues

**Error:** `ModuleNotFoundError: No module named 'chat_pipeline'`
```bash
# Solution: Build from project root
docker build -f Dockerfile.backend -t frontshiftai-backend:test .
```

### Database Connection Issues

**Error:** `could not translate host name`
```bash
# Solution: URL-encode password
# MLOpsgroup@9 → MLOpsgroup%409
```

### Port Conflicts
```bash
# Find what's using port
lsof -i:8000

# If container
docker rm -f container_name

# If Python process
kill -9 PID

# NEVER kill com.docke processes!
```

---

## Cost Breakdown

### Current Monthly Costs (After Free Credits)

**Cloud SQL:** ~$10/month (db-f1-micro)
**Cloud Storage:** ~$1/month
**Cloud Run:** ~$5-10/month (backend, low traffic)

**Total Estimated:** $16-21/month

**With $300 Credits:** FREE for 14-18 months

---

## GCS Bucket Structure
```
gs://frontshiftai-data/
├── models/
│   └── Llama-3.2-3B-Instruct-Q4_K_M.gguf (NOT used - Mercury API instead)
│
├── data/
│   ├── vector_db/ (ChromaDB - synced at startup)
│   │   ├── chroma.sqlite3
│   │   ├── index/
│   │   └── ... (embedding data)
│   │
│   ├── raw/ (Original PDF handbooks)
│   ├── cleaned/ (Processed text)
│   ├── chunked/ (Tokenized chunks)
│   └── validated/ (Quality-checked data)
```

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

**Total Time Investment:** ~8 hours
**Status:** Backend fully containerized, tested, optimized, and ready for deployment ✅

---

## Resources & Documentation

### Official Documentation
- [Cloud Run](https://cloud.google.com/run/docs)
- [Cloud SQL for PostgreSQL](https://cloud.google.com/sql/docs/postgres)
- [Docker Multi-stage Builds](https://docs.docker.com/build/building/multi-stage/)
- [GitHub Actions](https://docs.github.com/en/actions)

### FrontShiftAI Documentation
- Backend README: `backend/README.md`
- Agents README: `backend/agents/README.md`
- Data Pipeline: `data_pipeline/README.md`
- Chat Pipeline: `chat_pipeline/README.md`

### Support & Help
- GCP Console: https://console.cloud.google.com/
- Cloud SQL Instances: https://console.cloud.google.com/sql/instances
- Cloud Storage: https://console.cloud.google.com/storage/browser/frontshiftai-data

---

**Last Updated:** December 3, 2025 (2:50 PM EST)  
**Status:** Phase 2 Complete & Optimized ✅ | Mercury API Integrated ✅ | Ready for Phase 3 (GitHub Actions) 🚀  
**Next Milestone:** Automated deployment pipeline via GitHub Actions