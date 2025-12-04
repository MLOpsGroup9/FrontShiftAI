# FrontShiftAI - GCP Deployment Commands Reference

Complete list of all commands used during the deployment setup process.

---

## Table of Contents
1. [GCP Project Setup](#gcp-project-setup)
2. [Cloud SQL Setup](#cloud-sql-setup)
3. [Docker Commands](#docker-commands)
4. [GCS Commands](#gcs-commands)
5. [GitHub Actions Setup](#github-actions-setup)
6. [Secret Manager](#secret-manager)
7. [Local Development](#local-development)
8. [Troubleshooting](#troubleshooting)

---

## GCP Project Setup

### Initial Authentication
```bash
# Login to GCP
gcloud auth login

# Set default project
gcloud config set project frontshiftai

# Verify current project
gcloud config get-value project

# List all projects
gcloud projects list
```

### Enable Required APIs
```bash
# Cloud SQL Admin API
gcloud services enable sqladmin.googleapis.com

# Cloud Storage API (usually already enabled)
gcloud services enable storage.googleapis.com

# Artifact Registry API
gcloud services enable artifactregistry.googleapis.com

# Cloud Run API
gcloud services enable run.googleapis.com

# IAM Credentials API
gcloud services enable iamcredentials.googleapis.com

# Secret Manager API
gcloud services enable secretmanager.googleapis.com

# Verify enabled APIs
gcloud services list --enabled
```

---

## Cloud SQL Setup

### Create Cloud SQL Instance
```bash
# Create PostgreSQL instance
gcloud sql instances create frontshiftai-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1

# Describe instance
gcloud sql instances describe frontshiftai-db

# Get connection name
gcloud sql instances describe frontshiftai-db --format="value(connectionName)"
```

### Create Database
```bash
# Create database
gcloud sql databases create frontshiftai --instance=frontshiftai-db

# List databases
gcloud sql databases list --instance=frontshiftai-db
```

### Set Database Password
```bash
# Set postgres user password
gcloud sql users set-password postgres \
  --instance=frontshiftai-db \
  --password=MLOpsgroup@9
```

### Cloud SQL Proxy Setup
```bash
# Download Cloud SQL Proxy (macOS)
curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.8.0/cloud-sql-proxy.darwin.arm64
chmod +x cloud-sql-proxy
sudo mv cloud-sql-proxy /usr/local/bin/

# Start Cloud SQL Proxy
cloud-sql-proxy frontshiftai:us-central1:frontshiftai-db

# Start in background
cloud-sql-proxy frontshiftai:us-central1:frontshiftai-db &

# Stop Cloud SQL Proxy
pkill -f cloud-sql-proxy
```

### Connect to Database
```bash
# Via Cloud SQL Proxy (local)
psql "host=127.0.0.1 port=5432 dbname=frontshiftai user=postgres password=MLOpsgroup@9"

# Via gcloud (direct)
gcloud sql connect frontshiftai-db --user=postgres --database=frontshiftai

# Check PostgreSQL version
psql "host=127.0.0.1 port=5432 dbname=frontshiftai user=postgres password=MLOpsgroup@9" -c "SELECT version();"
```

### Database Management
```bash
# Restart instance
gcloud sql instances restart frontshiftai-db

# Stop instance (save costs)
gcloud sql instances patch frontshiftai-db --activation-policy=NEVER

# Start instance
gcloud sql instances patch frontshiftai-db --activation-policy=ALWAYS

# Delete instance (CAREFUL!)
gcloud sql instances delete frontshiftai-db
```

---

## Docker Commands

### Building Images

**Build Backend Image:**
```bash
# From project root
docker build -f Dockerfile.backend -t frontshiftai-backend:test .

# Build for specific platform (Cloud Run compatible)
docker build -f Dockerfile.backend \
  --platform linux/amd64 \
  -t frontshiftai-backend:cloudrun .

# Build with no cache
docker build -f Dockerfile.backend \
  --no-cache \
  -t frontshiftai-backend:test .
```

### Running Containers

**Single Container (Manual):**
```bash
# Clean up first
docker rm -f frontshiftai-backend-dev 2>/dev/null || true

# Run container
docker run --rm --name frontshiftai-backend-dev \
  -p 9000:8000 \
  -e DATABASE_URL="postgresql://postgres:MLOpsgroup%409@host.docker.internal:5432/frontshiftai" \
  -e ENVIRONMENT="development" \
  -e GROQ_API_KEY="your_key" \
  -e INCEPTION_API_KEY="your_key" \
  frontshiftai-backend:test

# Run with platform specification
docker run --rm \
  --platform linux/amd64 \
  --name frontshiftai-backend-dev \
  -p 9000:8000 \
  frontshiftai-backend:cloudrun
```

**Docker Compose:**
```bash
# Start services
docker-compose up

# Start with build
docker-compose up --build

# Start in background
docker-compose up -d

# Stop services
docker-compose down

# Stop and remove volumes (fresh database)
docker-compose down -v

# Remove orphan containers
docker-compose up --remove-orphans

# View logs
docker-compose logs backend
docker-compose logs postgres
docker-compose logs -f  # Follow logs
```

### Container Management
```bash
# List running containers
docker ps

# List all containers (including stopped)
docker ps -a

# Stop container
docker stop backend-1

# Remove container
docker rm backend-1

# Force remove running container
docker rm -f backend-1

# Execute command in running container
docker exec -it backend-1 /bin/bash
docker exec -it backend-1 python --version

# Connect to PostgreSQL in container
docker exec -it $(docker ps -qf "name=postgres") psql -U postgres -d frontshiftai

# View container logs
docker logs backend-1
docker logs -f backend-1  # Follow logs
docker logs --tail 100 backend-1  # Last 100 lines
```

### Image Management
```bash
# List images
docker images

# List images for specific repository
docker images | grep frontshiftai

# Remove image
docker rmi frontshiftai-backend:test

# Remove unused images
docker image prune

# Remove all unused images
docker image prune -a

# Check image details
docker inspect frontshiftai-backend:test

# Check image size
docker images frontshiftai-backend:test --format "{{.Size}}"

# View image history
docker history frontshiftai-backend:test
```

### Cleanup Commands
```bash
# Remove all stopped containers
docker container prune -f

# Remove all unused images
docker image prune -a -f

# Remove all unused volumes
docker volume prune -f

# Remove everything (nuclear option)
docker system prune -a --volumes -f

# Check Docker disk usage
docker system df
```

### Debugging Commands
```bash
# Check container resource usage
docker stats

# Inspect container
docker inspect backend-1

# View container processes
docker top backend-1

# Check container health
docker inspect --format='{{.State.Health.Status}}' backend-1

# View container logs with timestamps
docker logs -t backend-1
```

---

## GCS Commands

### Bucket Management
```bash
# List buckets
gsutil ls

# Create bucket (already exists)
gsutil mb -p frontshiftai -l us-central1 gs://frontshiftai-data

# List bucket contents
gsutil ls gs://frontshiftai-data/

# List with details
gsutil ls -lh gs://frontshiftai-data/

# List recursively
gsutil ls -r gs://frontshiftai-data/
```

### Upload Files
```bash
# Upload single file
gsutil cp models/Llama-3.2-3B-Instruct-Q4_K_M.gguf gs://frontshiftai-data/models/

# Upload directory
gsutil -m cp -r data_pipeline/data/vector_db/ gs://frontshiftai-data/data/

# Upload with progress
gsutil -o GSUtil:parallel_process_count=8 cp -r directory/ gs://bucket/
```

### Download Files
```bash
# Download single file
gsutil cp gs://frontshiftai-data/models/Llama-3.2-3B-Instruct-Q4_K_M.gguf ./models/

# Download directory
gsutil -m cp -r gs://frontshiftai-data/data/vector_db/ ./data/
```

### Sync Directories
```bash
# Upload local to GCS (sync)
gsutil -m rsync -r data_pipeline/data/vector_db/ gs://frontshiftai-data/data/vector_db/

# Download GCS to local (sync)
gsutil -m rsync -r gs://frontshiftai-data/data/vector_db/ data_pipeline/data/vector_db/

# Sync with delete (removes files not in source)
gsutil -m rsync -r -d local_dir/ gs://bucket/remote_dir/
```

### File Management
```bash
# Check file size
gsutil du -sh gs://frontshiftai-data/models/

# Get file metadata
gsutil stat gs://frontshiftai-data/models/Llama-3.2-3B-Instruct-Q4_K_M.gguf

# Delete file
gsutil rm gs://frontshiftai-data/path/to/file

# Delete directory
gsutil -m rm -r gs://frontshiftai-data/path/to/directory/

# Make file public
gsutil acl ch -u AllUsers:R gs://bucket/file

# Make file private
gsutil acl ch -d AllUsers gs://bucket/file
```

---

## GitHub Actions Setup

### Artifact Registry
```bash
# Create repository
gcloud artifacts repositories create frontshiftai-backend \
  --repository-format=docker \
  --location=us-central1 \
  --description="FrontShiftAI backend Docker images"

# List repositories
gcloud artifacts repositories list --location=us-central1

# Delete repository
gcloud artifacts repositories delete frontshiftai-backend --location=us-central1

# List images in repository
gcloud artifacts docker images list \
  us-central1-docker.pkg.dev/frontshiftai/frontshiftai-backend

# Delete specific image
gcloud artifacts docker images delete \
  us-central1-docker.pkg.dev/frontshiftai/frontshiftai-backend/backend:TAG
```

### Workload Identity Federation
```bash
# Create Workload Identity Pool
gcloud iam workload-identity-pools create "github-actions-pool" \
  --project="frontshiftai" \
  --location="global" \
  --display-name="GitHub Actions Pool"

# List Workload Identity Pools
gcloud iam workload-identity-pools list --location=global

# Describe pool
gcloud iam workload-identity-pools describe github-actions-pool \
  --location=global

# Create Workload Identity Provider
gcloud iam workload-identity-pools providers create-oidc "github-provider" \
  --project="frontshiftai" \
  --location="global" \
  --workload-identity-pool="github-actions-pool" \
  --display-name="GitHub Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --attribute-condition="assertion.repository_owner=='MLOpsGroup9'" \
  --issuer-uri="https://token.actions.githubusercontent.com"

# List providers
gcloud iam workload-identity-pools providers list \
  --workload-identity-pool=github-actions-pool \
  --location=global

# Describe provider
gcloud iam workload-identity-pools providers describe github-provider \
  --workload-identity-pool=github-actions-pool \
  --location=global
```

### Service Account
```bash
# Create service account
gcloud iam service-accounts create github-actions \
  --project="frontshiftai" \
  --display-name="GitHub Actions Service Account"

# List service accounts
gcloud iam service-accounts list

# Describe service account
gcloud iam service-accounts describe github-actions@frontshiftai.iam.gserviceaccount.com

# Delete service account
gcloud iam service-accounts delete github-actions@frontshiftai.iam.gserviceaccount.com
```

### Grant IAM Permissions
```bash
# Storage Admin
gcloud projects add-iam-policy-binding frontshiftai \
  --member="serviceAccount:github-actions@frontshiftai.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

# Artifact Registry Writer
gcloud projects add-iam-policy-binding frontshiftai \
  --member="serviceAccount:github-actions@frontshiftai.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

# Cloud Run Admin
gcloud projects add-iam-policy-binding frontshiftai \
  --member="serviceAccount:github-actions@frontshiftai.iam.gserviceaccount.com" \
  --role="roles/run.admin"

# Service Account User
gcloud projects add-iam-policy-binding frontshiftai \
  --member="serviceAccount:github-actions@frontshiftai.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

# Cloud SQL Client
gcloud projects add-iam-policy-binding frontshiftai \
  --member="serviceAccount:github-actions@frontshiftai.iam.gserviceaccount.com" \
  --role="roles/cloudsql.client"

# View IAM policy
gcloud projects get-iam-policy frontshiftai

# Remove permission
gcloud projects remove-iam-policy-binding frontshiftai \
  --member="serviceAccount:github-actions@frontshiftai.iam.gserviceaccount.com" \
  --role="roles/storage.admin"
```

### Link GitHub Repository to Service Account
```bash
# Allow GitHub repo to impersonate service account
gcloud iam service-accounts add-iam-policy-binding \
  github-actions@frontshiftai.iam.gserviceaccount.com \
  --project=frontshiftai \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/558177025654/locations/global/workloadIdentityPools/github-actions-pool/attribute.repository/MLOpsGroup9/FrontShiftAI"

# View service account IAM policy
gcloud iam service-accounts get-iam-policy \
  github-actions@frontshiftai.iam.gserviceaccount.com
```

---

## Secret Manager

### Create Secrets
```bash
# GROQ API Key
echo -n "YOUR_GROQ_API_KEY_HERE" | \
  gcloud secrets create GROQ_API_KEY \
  --data-file=- \
  --replication-policy="automatic"

# BRAVE API Key
echo -n "BSAV_N6Fzxw97Sowd4YaJoIQ11XKXUC" | \
  gcloud secrets create BRAVE_API_KEY \
  --data-file=- \
  --replication-policy="automatic"

# JWT Secret Key (random generation)
openssl rand -base64 32 | tr -d '\n' | \
  gcloud secrets create JWT_SECRET_KEY \
  --data-file=- \
  --replication-policy="automatic"

# Mercury/Inception API Key
echo -n "sk_2efcb384d7733fe0ed6b3b708125e9ea" | \
  gcloud secrets create INCEPTION_API_KEY \
  --data-file=- \
  --replication-policy="automatic"

# Database URL (Cloud Run with Unix socket)
echo -n "postgresql://postgres:MLOpsgroup%409@/frontshiftai?host=/cloudsql/frontshiftai:us-central1:frontshiftai-db" | \
  gcloud secrets create DATABASE_URL \
  --data-file=- \
  --replication-policy="automatic"
```

### Manage Secrets
```bash
# List all secrets
gcloud secrets list

# View secret metadata
gcloud secrets describe GROQ_API_KEY

# List secret versions
gcloud secrets versions list GROQ_API_KEY

# Access secret value
gcloud secrets versions access latest --secret=GROQ_API_KEY

# Add new version to existing secret
echo -n "new_value" | gcloud secrets versions add GROQ_API_KEY --data-file=-

# Delete secret
gcloud secrets delete GROQ_API_KEY

# Delete specific version
gcloud secrets versions destroy 1 --secret=GROQ_API_KEY
```

### Grant Secret Access
```bash
# Grant single secret access
gcloud secrets add-iam-policy-binding GROQ_API_KEY \
  --member="serviceAccount:github-actions@frontshiftai.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Grant access to all secrets (loop)
for secret in GROQ_API_KEY BRAVE_API_KEY JWT_SECRET_KEY INCEPTION_API_KEY DATABASE_URL; do
  gcloud secrets add-iam-policy-binding $secret \
    --member="serviceAccount:github-actions@frontshiftai.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
done

# View secret IAM policy
gcloud secrets get-iam-policy GROQ_API_KEY

# Remove access
gcloud secrets remove-iam-policy-binding GROQ_API_KEY \
  --member="serviceAccount:github-actions@frontshiftai.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

---

## Cloud Run Commands

### Deploy Service
```bash
# Deploy from local image
gcloud run deploy frontshiftai-backend \
  --image us-central1-docker.pkg.dev/frontshiftai/frontshiftai-backend/backend:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars ENVIRONMENT=production,GENERATION_BACKEND=mercury \
  --set-secrets GROQ_API_KEY=GROQ_API_KEY:latest,BRAVE_API_KEY=BRAVE_API_KEY:latest,JWT_SECRET_KEY=JWT_SECRET_KEY:latest,INCEPTION_API_KEY=INCEPTION_API_KEY:latest,DATABASE_URL=DATABASE_URL:latest \
  --add-cloudsql-instances frontshiftai:us-central1:frontshiftai-db \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --max-instances 10 \
  --min-instances 0

# Deploy with specific tag
gcloud run deploy frontshiftai-backend \
  --image us-central1-docker.pkg.dev/frontshiftai/frontshiftai-backend/backend:abc123 \
  --region us-central1
```

### Manage Services
```bash
# List services
gcloud run services list --region=us-central1

# Describe service
gcloud run services describe frontshiftai-backend --region=us-central1

# Get service URL
gcloud run services describe frontshiftai-backend \
  --region=us-central1 \
  --format='value(status.url)'

# Delete service
gcloud run services delete frontshiftai-backend --region=us-central1

# Update service (change memory)
gcloud run services update frontshiftai-backend \
  --region=us-central1 \
  --memory=4Gi

# Update service (change CPU)
gcloud run services update frontshiftai-backend \
  --region=us-central1 \
  --cpu=4

# Update environment variable
gcloud run services update frontshiftai-backend \
  --region=us-central1 \
  --update-env-vars GENERATION_BACKEND=groq
```

### View Logs
```bash
# View service logs
gcloud run services logs read frontshiftai-backend --region=us-central1

# Follow logs (tail)
gcloud run services logs tail frontshiftai-backend --region=us-central1

# Filter logs by severity
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" \
  --limit 50 \
  --format json
```

### Revisions & Traffic
```bash
# List revisions
gcloud run revisions list \
  --service=frontshiftai-backend \
  --region=us-central1

# Describe revision
gcloud run revisions describe REVISION_NAME \
  --region=us-central1

# Route traffic to specific revision
gcloud run services update-traffic frontshiftai-backend \
  --to-revisions=REVISION_NAME=100 \
  --region=us-central1

# Split traffic between revisions
gcloud run services update-traffic frontshiftai-backend \
  --to-revisions=REVISION_1=50,REVISION_2=50 \
  --region=us-central1

# Delete revision
gcloud run revisions delete REVISION_NAME --region=us-central1
```

---

## Local Development

### Python Environment
```bash
# Activate virtual environment
pyenv shell 3.12.9
pyenv activate frontshiftai

# Install dependencies
cd backend
pip install -r requirements.txt

# Run backend locally
cd backend
python main.py

# Run with specific port
PORT=9000 python main.py

# Run with environment variable
DATABASE_URL="postgresql://..." python main.py
```

### Environment Variables
```bash
# Set environment variable for current session
export DATABASE_URL="postgresql://postgres:MLOpsgroup%409@127.0.0.1:5432/frontshiftai"
export GROQ_API_KEY="your_key"

# Unset environment variable
unset GOOGLE_APPLICATION_CREDENTIALS

# View environment variable
echo $DATABASE_URL

# View all environment variables
env | grep -E "DATABASE|API_KEY"

# Load from .env file (if using direnv)
direnv allow .
```

### Testing API Endpoints
```bash
# Health check
curl http://localhost:8000/health

# Login (get token)
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@crousemedical.com","password":"password123"}'

# Get user info
curl -X GET "http://localhost:8000/api/auth/me" \
  -H "Authorization: Bearer YOUR_TOKEN"

# PTO chat
curl -X POST "http://localhost:8000/api/pto/chat" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "I need vacation from Dec 15 to Dec 20"}'

# Get PTO balance
curl -X GET "http://localhost:8000/api/pto/balance" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get PTO requests
curl -X GET "http://localhost:8000/api/pto/requests" \
  -H "Authorization: Bearer YOUR_TOKEN"

# View API docs
open http://localhost:8000/docs
```

---

## Git Commands

### Branch Management
```bash
# Check current branch
git branch

# Create new branch
git checkout -b new-branch

# Switch to branch
git checkout krishna-branch

# Pull latest changes
git pull origin krishna-branch

# Merge main into your branch
git checkout krishna-branch
git merge main
```

### Commit & Push
```bash
# Check status
git status

# Check what changed
git diff

# Add files
git add .
git add specific-file.py

# Commit
git commit -m "Add Cloud Run deployment workflow"

# Push to remote
git push origin krishna-branch

# Force push (CAREFUL!)
git push -f origin krishna-branch
```

### Viewing Changes
```bash
# See uncommitted changes
git status -s

# See modified files only
git diff --name-only

# See untracked files
git ls-files --others --exclude-standard

# View commit history
git log --oneline -10

# View specific file history
git log --oneline -- backend/main.py
```

---

## Troubleshooting

### Fix Cloud SQL Proxy Authentication
```bash
# Unset incorrect credentials
unset GOOGLE_APPLICATION_CREDENTIALS

# Login with application default credentials
gcloud auth application-default login

# Verify authentication
gcloud auth list

# Should show your email with * (active account)
```

### Fix Port Conflicts
```bash
# Check what's using port 8000
lsof -i:8000

# Kill Python process
kill -9 PID

# Kill all Python processes on port 8000
lsof -ti:8000 | xargs kill -9

# NEVER kill com.docke processes!

# Check if Docker is running
docker info
```

### Fix Docker Issues
```bash
# Restart Docker Desktop (if daemon crashed)
# Applications → Docker → Restart

# Check Docker daemon status
docker info

# Clean up Docker system
docker system prune -a --volumes -f

# Reset Docker to factory defaults
# Docker Desktop → Troubleshoot → Reset to factory defaults
```

### Database Issues
```bash
# Reset database (docker-compose)
docker-compose down -v
docker-compose up

# Check database connection
psql "host=127.0.0.1 port=5432 dbname=frontshiftai user=postgres password=MLOpsgroup@9" -c "SELECT 1;"

# View database tables
psql "..." -c "\dt"

# Drop and recreate database
gcloud sql databases delete frontshiftai --instance=frontshiftai-db
gcloud sql databases create frontshiftai --instance=frontshiftai-db
```

### View PostgreSQL Database
```bash
# List all tables
\dt

# Describe table structure
\d users
\d companies

# Check table contents
SELECT * FROM companies;
SELECT email, role FROM users;
SELECT * FROM pto_balances;

# Count rows
SELECT COUNT(*) FROM companies;

# Exit psql
\q
```

---

## Monitoring & Debugging

### Cloud Run Logs
```bash
# Read recent logs
gcloud run services logs read frontshiftai-backend --region=us-central1 --limit=100

# Tail logs (follow)
gcloud run services logs tail frontshiftai-backend --region=us-central1

# Filter by severity
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" --limit=50

# Filter by time
gcloud logging read "resource.type=cloud_run_revision AND timestamp>\"2025-12-03T00:00:00Z\"" --limit=100
```

### Service Health
```bash
# Check service status
gcloud run services describe frontshiftai-backend \
  --region=us-central1 \
  --format="value(status.conditions)"

# Get service metrics
gcloud monitoring time-series list \
  --filter='metric.type="run.googleapis.com/request_count"' \
  --format=json

# Test deployed service
curl https://frontshiftai-backend-*.run.app/health
```

### Performance
```bash
# Check container resource usage (local)
docker stats

# Check Cloud Run metrics (via console)
# https://console.cloud.google.com/run/detail/us-central1/frontshiftai-backend/metrics

# View Cloud SQL performance
gcloud sql operations list --instance=frontshiftai-db
```

---

## Useful Shortcuts

### Check Everything is Running
```bash
# One-liner health check
lsof -i:5432 && echo "✅ Cloud SQL Proxy running" || echo "❌ Cloud SQL Proxy not running"
lsof -i:8000 && echo "✅ Backend running" || echo "❌ Backend not running"
docker ps && echo "✅ Docker running" || echo "❌ Docker not running"
```

### Quick Cleanup
```bash
# Stop everything
pkill -f cloud-sql-proxy
docker-compose down
docker container prune -f
```

### Quick Start
```bash
# Start Cloud SQL Proxy
cloud-sql-proxy frontshiftai:us-central1:frontshiftai-db &

# Start backend
cd backend && python main.py

# OR start with docker-compose
docker-compose up
```

### Environment Check
```bash
# Check Python version
python --version

# Check Docker version
docker --version

# Check gcloud version
gcloud --version

# Check if authenticated
gcloud auth list

# Check current project
gcloud config list
```

---

## Production Deployment Commands

### First Time Deployment
```bash
# 1. Merge PR to main (via GitHub UI)

# 2. Monitor deployment
gh run watch

# 3. Get deployed URL
gcloud run services describe frontshiftai-backend \
  --region=us-central1 \
  --format='value(status.url)'

# 4. Test deployed service
BACKEND_URL=$(gcloud run services describe frontshiftai-backend --region=us-central1 --format='value(status.url)')
curl $BACKEND_URL/health
```

### Rollback Deployment
```bash
# List revisions
gcloud run revisions list --service=frontshiftai-backend --region=us-central1

# Rollback to previous revision
gcloud run services update-traffic frontshiftai-backend \
  --to-revisions=PREVIOUS_REVISION=100 \
  --region=us-central1
```

### Update Secrets
```bash
# Update secret value
echo -n "new_api_key" | gcloud secrets versions add GROQ_API_KEY --data-file=-

# Cloud Run will automatically use new version on next deployment
# Or force redeploy to pick up new secret
gcloud run services update frontshiftai-backend \
  --region=us-central1 \
  --update-secrets=GROQ_API_KEY=GROQ_API_KEY:latest
```

---

## Emergency Commands

### Kill All Processes
```bash
# Kill backend processes
pkill -f "python.*main.py"
pkill -f "uvicorn"

# Kill Cloud SQL Proxy
pkill -f cloud-sql-proxy

# Kill Docker containers
docker kill $(docker ps -q)
```

### Complete Reset
```bash
# Stop all services
docker-compose down -v
pkill -f cloud-sql-proxy

# Clean Docker
docker system prune -a --volumes -f

# Restart Docker Desktop
# Applications → Docker → Restart
```

### Fix Authentication
```bash
# Reset gcloud auth
gcloud auth revoke
gcloud auth login
gcloud auth application-default login

# Set project
gcloud config set project frontshiftai
```

---

## Quick Reference Table

| Task | Command |
|------|---------|
| Start Cloud SQL Proxy | `cloud-sql-proxy frontshiftai:us-central1:frontshiftai-db` |
| Run backend locally | `cd backend && python main.py` |
| Start docker-compose | `docker-compose up --build` |
| Stop docker-compose | `docker-compose down` |
| Connect to DB | `psql "host=127.0.0.1 port=5432 dbname=frontshiftai user=postgres password=MLOpsgroup@9"` |
| View logs | `docker logs backend-1` |
| Test API | `curl http://localhost:8000/health` |
| Check Git status | `git status` |
| Push to branch | `git push origin krishna-branch` |
| Enable API | `gcloud services enable API_NAME` |
| List secrets | `gcloud secrets list` |
| View Cloud Run services | `gcloud run services list --region=us-central1` |

---

**Last Updated:** December 3, 2025 (8:00 PM EST)  
**Document Version:** 1.0  
**Status:** Complete command reference for all deployment phases