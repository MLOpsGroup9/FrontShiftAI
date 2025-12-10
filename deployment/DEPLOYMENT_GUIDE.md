# FrontShiftAI - Deployment Guide

This guide explains how to deploy the FrontShiftAI application to Google Cloud Platform (GCP) from scratch. It is designed for developers who want to set up their own instance of the application.

## Prerequisites

1.  **GCP Account**: A Google Cloud Platform account with billing enabled.
2.  **Domain Name (Optional)**: For custom domains (Cloud Run provides default URLs).
3.  **Third-Party API Keys**:
    - [Mercury Labs](https://mercurylabs.org/) (LLM)
    - [Groq](https://groq.com/) (Fallback LLM)
    - [Brave Search](https://brave.com/search/api/) (Web extraction)
    - [HuggingFace](https://huggingface.co/) (Embedding models)
4.  **Tools**:
    - [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) (`gcloud`)
    - [Docker](https://docs.docker.com/get-docker/)
    - [Git](https://git-scm.com/)

---

## Step 1: GCP Project Setup

1.  **Create a Project**:
    ```bash
    gcloud projects create frontshiftai-deploy --name="FrontShiftAI Deploy"
    gcloud config set project frontshiftai-deploy
    ```

2.  **Enable Required APIs**:
    ```bash
    gcloud services enable \
      run.googleapis.com \
      sqladmin.googleapis.com \
      storage.googleapis.com \
      artifactregistry.googleapis.com \
      secretmanager.googleapis.com \
      iamcredentials.googleapis.com \
      cloudbuild.googleapis.com
    ```

---

## Step 2: Infrastructure Setup

### 1. Artifact Registry (Docker Images)
Create repositories for backend and frontend images.

```bash
gcloud artifacts repositories create frontshiftai-backend \
    --repository-format=docker \
    --location=us-central1 \
    --description="Backend Docker repository"

gcloud artifacts repositories create frontshiftai-frontend \
    --repository-format=docker \
    --location=us-central1 \
    --description="Frontend Docker repository"
```

### 2. Cloud Storage (Data & Vectors)
Create a bucket for data and upload the ChromaDB vector store.

```bash
# Create bucket
gsutil mb -l us-central1 gs://frontshiftai-deploy-data

# Upload ChromaDB (packaged from your local data pipeline)
# Assuming you have the tar.gz locally
gsutil cp path/to/chroma_db.tar.gz gs://frontshiftai-deploy-data/chroma_db.tar.gz
```

### 3. Cloud SQL (Database)
Create a PostgreSQL instance.

```bash
# Create instance
gcloud sql instances create frontshiftai-db \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=us-central1 \
    --root-password=YourStrongPassword123

# Create database
gcloud sql databases create frontshiftai --instance=frontshiftai-db
```

### 4. Secret Manager (Configuration)
Store sensitive keys safely.

```bash
# Create and set secrets (repeat for each key)
echo -n "your-mercury-key" | gcloud secrets create INCEPTION_API_KEY --data-file=-
echo -n "your-groq-key" | gcloud secrets create GROQ_API_KEY --data-file=-
echo -n "your-brave-key" | gcloud secrets create BRAVE_API_KEY --data-file=-
echo -n "your-jwt-secret" | gcloud secrets create JWT_SECRET_KEY --data-file=-
echo -n "your-huggingface-token" | gcloud secrets create HF_TOKEN --data-file=-

# Database URL format: postgresql://postgres:PASSWORD@/frontshiftai?host=/cloudsql/PROJECT_ID:us-central1:frontshiftai-db
echo -n "your-db-url" | gcloud secrets create DATABASE_URL --data-file=-
```

---

## Step 3: GitHub Actions Integration (CI/CD)

To deploy automatically on push, we use **Workload Identity Federation** (Keyless Authentication).

### 1. Setup Workload Identity
Run these commands to verify trust between GitHub and GCP.

```bash
# Create Service Account for GitHub Actions
gcloud iam service-accounts create github-actions-deploy \
    --display-name="GitHub Actions Deployer"

# Create Workload Identity Pool
gcloud iam workload-identity-pools create github-actions-pool \
    --location="global" \
    --description="Pool for GitHub Actions" \
    --display-name="GitHub Actions Pool"

# Create Provider
gcloud iam workload-identity-pools providers create-oidc github-provider \
    --workload-identity-pool="github-actions-pool" \
    --location="global" \
    --display-name="GitHub Provider" \
    --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
    --issuer-uri="https://token.actions.githubusercontent.com"

# Allow GitHub Repo to impersonate Service Account
# REPLACE 'YOUR_GITHUB_USER/YOUR_REPO' with your actual repo (e.g., 'johndoe/FrontShiftAI')
gcloud iam service-accounts add-iam-policy-binding "github-actions-deploy@frontshiftai-deploy.iam.gserviceaccount.com" \
    --role="roles/iam.workloadIdentityUser" \
    --member="principalSet://iam.googleapis.com/projects/YOUR_PROJECT_NUMBER/locations/global/workloadIdentityPools/github-actions-pool/attribute.repository/YOUR_GITHUB_USER/YOUR_REPO"
```

### 2. Grant Permissions
Give the service account access to resources.

```bash
SA_EMAIL="github-actions-deploy@frontshiftai-deploy.iam.gserviceaccount.com"

gcloud projects add-iam-policy-binding frontshiftai-deploy --member="serviceAccount:$SA_EMAIL" --role="roles/run.admin"
gcloud projects add-iam-policy-binding frontshiftai-deploy --member="serviceAccount:$SA_EMAIL" --role="roles/storage.admin"
gcloud projects add-iam-policy-binding frontshiftai-deploy --member="serviceAccount:$SA_EMAIL" --role="roles/artifactregistry.writer"
gcloud projects add-iam-policy-binding frontshiftai-deploy --member="serviceAccount:$SA_EMAIL" --role="roles/iam.serviceAccountUser"
```

### 3. Configure GitHub Secrets
Go to your GitHub Repository -> Settings -> Secrets and Variables -> Actions -> New Repository Secret.

| Secret Name | Value |
|-------------|-------|
| `GCP_PROJECT_ID` | `frontshiftai-deploy` |
| `GCP_SERVICE_ACCOUNT` | `github-actions-deploy@frontshiftai-deploy.iam.gserviceaccount.com` |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | `projects/YOUR_PROJECT_NUMBER/locations/global/workloadIdentityPools/github-actions-pool/providers/github-provider` |
| `JWT_SECRET_KEY` | (Same as in Secret Manager) |
| `VERCEL_TOKEN` | (If deploying frontend to Vercel) |

---

## Step 4: Deploying Your Application

### Automatic Deployment
1.  Push code to the `main` branch.
2.  GitHub Actions will:
    - Run Backend Tests (`test_backend.yml`)
    - Run Frontend Tests (`test_frontend.yml`)
    - If tests pass, deploy Backend (`deploy-backend.yml`)
    - If tests pass, deploy Frontend (`deploy-frontend.yml`)

### Manual Deployment (from local machine)
If you want to deploy without GitHub Actions:

```bash
# Backend
gcloud run deploy frontshiftai-backend \
    --source backend/ \
    --region us-central1 \
    --allow-unauthenticated \
    --set-secrets GROQ_API_KEY=GROQ_API_KEY:latest,DATABASE_URL=DATABASE_URL:latest

# Frontend
docker build -t gcr.io/frontshiftai-deploy/frontend ./frontend
docker push gcr.io/frontshiftai-deploy/frontend
gcloud run deploy frontshiftai-frontend --image gcr.io/frontshiftai-deploy/frontend --platform managed
```

---

## Step 5: Post-Deployment Verification

1.  **Check URLs**:
    - Go to Cloud Run console and get the service URLs.
    - Visit the Frontend URL.
2.  **Verify Database Connection**:
    - Try to log in (default user logic in code).
    - If you see "Backend Offline", check the browser console and backend logs.
3.  **Check Logs**:
    - `gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=frontshiftai-backend" --limit 20`

## Troubleshooting

- **504 Gateway Timeout**: The backend might be taking too long to start (downloading ChromaDB). Increase timeout to 300s.
- **Database Connection Error**: Ensure the Cloud Run service account has `roles/cloudsql.client` and the instance name is correct.
- **Permission Denied**: Check IAM roles for the deployment service account.
