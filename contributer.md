# FrontShiftAI – Contributor Workflow Guide

This guide lists all commands required to **clone**, **synchronize**, **reproduce**, **push**, and **deploy** updates for the FrontShiftAI repository, including DVC and CI/CD integration.

---

## 1. Clone the Repository

```bash
# Clone your fork
git clone https://github.com/<your-username>/FrontShiftAI.git
cd FrontShiftAI

# Add the upstream repository (main shared repo)
git remote add upstream https://github.com/MLOpsGroup9/FrontShiftAI.git

# Verify remotes
git remote -v
```

---

## 2. Set Up the Environment

```bash
# Create and activate a new environment
conda create -n frontshiftai python=3.12 -y
conda activate frontshiftai

# Install all dependencies
pip install -r requirements.txt

# Pull DVC-tracked data and artifacts
dvc pull

# Optional: verify DVC remote configuration
dvc remote list
```

---

## 2.1 Local Environment Variables and Secrets

The FrontShiftAI repository uses **GitHub Secrets** for secure credential management in CI/CD.  
These secrets (for example, `WANDB_API_KEY`, `EMAIL_SENDER`, etc.) are **not included** when the repository is cloned.  
To run the pipeline or Streamlit app locally, you must create a local `.env` file.

### Step 1. Copy the Example Environment File

```bash
cp .env.example .env
```

### Step 2. Edit `.env` with Your Own Keys

Open `.env` in a text editor and update your credentials:

```bash
WANDB_API_KEY=your_wandb_api_key_here
WANDB_ENTITY=group9mlops-northeastern-university
WANDB_PROJECT=FrontShiftAI

EMAIL_SENDER=youremail@gmail.com
EMAIL_PASSWORD=your_gmail_app_password
EMAIL_RECEIVER=youremail@gmail.com
```

> Note: The Gmail password must be an **App Password**, not your regular password.  
> App passwords can be generated in your Google Account → Security → 2-Step Verification → App Passwords.

### Step 3. Automatic Loading in Code

Your pipeline and Streamlit app automatically read this `.env` file using `python-dotenv`.

If you add new scripts that depend on secrets, include this at the top of your Python files:

```python
from dotenv import load_dotenv
load_dotenv()
```

This ensures:
- CI/CD uses GitHub Secrets.
- Local runs use `.env` file values.

### Step 4. Verify the Environment

```bash
echo $WANDB_API_KEY
echo $EMAIL_SENDER
```

If these print your values, the `.env` file is correctly loaded.

---

## 3. Synchronize with Upstream

Before you begin working, make sure your local branch is up to date.

```bash
# Fetch all updates
git fetch --all

# Switch to your working branch (e.g., krishna)
git checkout <your-branch-name>

# Rebase your branch on the latest upstream main
git pull upstream main --rebase
```

If merge conflicts appear, resolve them manually, then continue:

```bash
git add .
git rebase --continue
```

---

## 4. Run or Reproduce the Pipeline

You can either run each script manually or reproduce all stages through DVC.

```bash
# Manual pipeline execution
python data_pipeline/scripts/pipeline_runner.py

# Or reproduce automatically with DVC
dvc repro
```

---

## 5. Verify DVC Pipeline State

```bash
# Check current DVC pipeline graph
dvc dag

# Check tracked files and dependencies
dvc status

# Lock versions after successful repro
dvc commit
dvc push

# Verify lock file
cat dvc.lock
```

---

## 6. Run ML Evaluation Pipeline

```bash
# Run evaluation for RAG + bias + sensitivity + summary
python ml_pipeline/eval_pipeline_runner.py
```

Outputs generated under:
```
ml_pipeline/evaluation/eval_results/
models/
models_registry/
```

---

## 7. Inspect Model Registry

```bash
# List all registered model versions
ls -l models_registry/

# View metadata of latest version
cat models_registry/llama_3b_instruct_v*/metadata.json
```

---

## 8. Commit and Push Changes

```bash
# Stage all modified and new tracked files
git add .

# Commit with a descriptive message
git commit -m "Update pipeline, evaluation, and model registry"

# Push to your personal branch
git push origin <your-branch-name>
```

---

## 9. Push DVC Artifacts

If model files, embeddings, or vector databases changed:

```bash
# Push large data artifacts to remote DVC storage
dvc push

# Verify pushed artifacts
dvc status -c
```

---

## 10. Create a Pull Request

1. Go to your fork on GitHub.  
2. Click **Compare & Pull Request**.  
3. Target branch → `main` of `MLOpsGroup9/FrontShiftAI`.  
4. Write a clear description and submit.

---

## 11. CI/CD Automation Trigger

When a PR is merged or a push occurs on `main`, the GitHub Actions workflow runs automatically:

```yaml
Train → Validate → Deploy → Notify
```

Stages:
- Runs `eval_pipeline_runner.py`
- Uploads evaluation artifacts (`eval-results`)
- Deploys the best model to the registry
- Sends Gmail notification with metrics

Monitor results under the **Actions** tab in GitHub.

---

## 12. Update Local Repository Post-Merge

Once your PR is merged into the main repo:

```bash
# Switch to main
git checkout main

# Pull the latest changes
git pull upstream main

# Push synced version to your fork
git push origin main
```

---

## 13. Full Workflow Summary

```bash
# 1. Sync and update
git fetch --all
git pull upstream main --rebase

# 2. Run pipelines
dvc repro
python ml_pipeline/eval_pipeline_runner.py

# 3. Validate outputs
ls models_registry/
cat models_registry/llama_3b_instruct_v*/metadata.json

# 4. Commit and push
git add .
git commit -m "Updated ML evaluation pipeline"
git push origin <branch>

# 5. Push large artifacts
dvc push

# 6. Open PR and merge
# CI/CD auto-runs upon merge
```

---

## 14. Optional: Streamlit App Test

To validate the Streamlit integration locally after CI/CD runs:

```bash
# Launch the HR Copilot app
streamlit run streamlit_app/app.py

# Ensure preload loads the latest model from models_registry/
```

---

This workflow ensures all code, data, and models remain **version-controlled, reproducible, and automatically deployed**.
