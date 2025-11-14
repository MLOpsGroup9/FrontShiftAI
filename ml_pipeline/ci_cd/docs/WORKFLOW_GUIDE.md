# Workflow Guide - FrontShiftAI CI/CD Pipeline

This guide explains each GitHub Actions workflow, their triggers, jobs, and how to interpret results.

---

## Table of Contents

1. [RAG Pipeline Workflow](#rag-pipeline-workflow)
2. [Component Test Workflow](#component-test-workflow)
3. [Model Deploy Workflow](#model-deploy-workflow)
4. [Rollback Workflow](#rollback-workflow)
5. [Manual Workflow Triggers](#manual-workflow-triggers)
6. [Interpreting Results](#interpreting-results)

---

## RAG Pipeline Workflow

**File:** `.github/workflows/rag_pipeline.yml`

### Overview

The main CI/CD pipeline that runs the complete ML evaluation workflow: setup validation, evaluation, quality gates, deployment, and notifications.

### Trigger Conditions

- **Automatic:** Push to `main` branch
- **Automatic:** Pull request to `main` branch
- **Manual:** Workflow dispatch from GitHub Actions UI

### Jobs

#### 1. Setup & Validation
- **Purpose:** Validates environment before running pipeline
- **Duration:** ~5-10 minutes
- **Checks:**
  - Python version (3.12)
  - Required packages installed
  - ChromaDB accessibility
  - Model file exists
  - Environment variables set
  - System resources (disk space, memory)

**Success Criteria:** All validation checks pass

#### 2. Run Evaluation Pipeline
- **Purpose:** Executes the complete ML evaluation pipeline
- **Duration:** ~10-20 minutes
- **Steps:**
  - Runs `ml_pipeline/eval_pipeline_runner.py`
  - Executes RAG evaluation, bias detection, sensitivity analysis
  - Generates unified summary
  - Logs metrics to W&B
- **Outputs:**
  - `eval-results` artifact (30-day retention)
  - Metrics exported to GitHub Actions output

**Success Criteria:** All evaluation stages complete, unified_summary.json generated

#### 3. Quality Gate Check
- **Purpose:** Validates evaluation metrics against thresholds
- **Duration:** ~2-5 minutes
- **Process:**
  - Loads thresholds from `ml_pipeline/configs/quality_gates.yml`
  - Compares metrics from `unified_summary.json`
  - Determines environment (production/staging/development) based on branch
  - Sets `deployment_approved` output
- **Outputs:**
  - `quality-gate-results` artifact
  - `deployment_approved` (true/false)
  - `quality_gate_status` (PASS/PASS_WITH_WARNINGS/FAIL)

**Success Criteria:** All critical thresholds pass, deployment approved

#### 4. Deploy Model to Registry
- **Purpose:** Deploys evaluated model to versioned registry
- **Duration:** ~5-10 minutes
- **Condition:** Only runs if `deployment_approved == true`
- **Steps:**
  - Downloads evaluation artifacts
  - Calls `ml_pipeline/ci_cd/deploy_model.py`
  - Creates versioned directory in `models_registry/`
  - Updates latest symlink
  - Logs deployment to W&B
- **Outputs:**
  - `model-registry` artifact (90-day retention)

**Success Criteria:** Model deployed, metadata.json created, symlink updated

#### 5. Send Email Notification
- **Purpose:** Sends email notification with pipeline results
- **Duration:** ~1-2 minutes
- **Condition:** Always runs (even if previous jobs fail)
- **Content:**
  - Pipeline status (success/failure)
  - Key metrics
  - Quality gate result
  - Links to GitHub Actions run and W&B dashboard

**Success Criteria:** Email sent (non-blocking if email fails)

### Workflow Diagram

```
Push to main
    ↓
Setup & Validation
    ↓
Run Evaluation Pipeline
    ↓
Quality Gate Check
    ↓ (if approved)
Deploy Model to Registry
    ↓
Send Email Notification (always)
```

---

## Component Test Workflow

**File:** `.github/workflows/component_test.yml`

### Overview

Fast feedback workflow for feature branches. Runs lightweight tests without full evaluation pipeline.

### Trigger Conditions

- **Automatic:** Push to `feature/**`, `fix/**`, or `dev` branches
- **Automatic:** Pull request to `main` or `dev`

### Jobs

#### 1. Unit Tests
- **Purpose:** Run pytest unit tests
- **Duration:** ~3-5 minutes
- **Note:** Non-blocking if no tests exist

#### 2. Integration Smoke Test
- **Purpose:** Quick validation of key components
- **Duration:** ~5-10 minutes
- **Tests:**
  - ChromaDB connectivity (if available)
  - Single RAG query test
- **Note:** Non-blocking if components unavailable

#### 3. Code Quality
- **Purpose:** Check code formatting and linting
- **Duration:** ~2-5 minutes
- **Tools:**
  - Black (formatting check)
  - Flake8 (linting)
- **Note:** Non-blocking warnings

#### 4. Test Summary
- **Purpose:** Generate summary of all test results
- **Duration:** ~1 minute
- **Output:** GitHub Actions step summary

### When to Use

Use this workflow for:
- Quick feedback on feature branches
- Validating code changes before merging
- Catching issues early in development

---

## Model Deploy Workflow

**File:** `.github/workflows/model_deploy.yml`

### Overview

Standalone deployment workflow that can be called from other workflows or triggered manually.

### Trigger Conditions

- **Workflow Call:** Called from `rag_pipeline.yml` after quality gates pass
- **Manual:** Workflow dispatch from GitHub Actions UI

### Inputs

- `model_path` (optional): Path to model file (default: from config)
- `quality_gate_status` (optional): Quality gate status (default: PASS)

### Jobs

#### 1. Pre-deployment Validation
- **Purpose:** Validate model before deployment
- **Duration:** ~3-5 minutes
- **Checks:**
  - Model file exists and is valid
  - Model file integrity
  - Model loading test (if applicable)

#### 2. Deploy to Registry
- **Purpose:** Deploy model to versioned registry
- **Duration:** ~5-10 minutes
- **Steps:**
  - Downloads evaluation artifacts (if available)
  - Calls `deploy_model.py`
  - Creates versioned directory
  - Updates metadata with deployment info

#### 3. Post-deployment Smoke Test
- **Purpose:** Verify deployed model works
- **Duration:** ~3-5 minutes
- **Tests:**
  - Verify deployed model metadata
  - Run sample queries (if RAG available)

### When to Use

Use this workflow for:
- Manual deployment of specific models
- Re-deploying previous versions
- Testing deployment process

---

## Rollback Workflow

**File:** `.github/workflows/rollback.yml`

### Overview

Manual workflow for rolling back to a previous model version. Requires approval for production.

### Trigger Conditions

- **Manual Only:** Workflow dispatch from GitHub Actions UI

### Inputs

- `target_version` (optional): Version to rollback to (e.g., "v5")
- `reason` (required): Reason for rollback (audit trail)
- `use_previous` (optional): Rollback to previous version (boolean)

### Jobs

#### 1. Validate Rollback Target
- **Purpose:** Validate target version exists and is acceptable
- **Duration:** ~2-5 minutes
- **Steps:**
  - Lists available versions
  - Validates target version exists
  - Loads target version metadata
  - Verifies target metrics were acceptable
  - **Requires manual approval for production**

#### 2. Execute Rollback
- **Purpose:** Perform the rollback
- **Duration:** ~3-5 minutes
- **Steps:**
  - Backs up current version
  - Restores target version
  - Updates symlinks
  - Creates rollback log

#### 3. Post-rollback Validation
- **Purpose:** Verify rollback was successful
- **Duration:** ~2-5 minutes
- **Tests:**
  - Verify rolled-back model is active
  - Run smoke tests (if applicable)

#### 4. Notification & Incident Log
- **Purpose:** Send notifications and create tracking issue
- **Duration:** ~1-2 minutes
- **Actions:**
  - Sends rollback notification email
  - Creates GitHub issue for incident tracking

### When to Use

Use this workflow when:
- Model performance degrades in production
- Critical bugs are discovered
- Need to revert to a known-good version

### Rollback Process

1. Go to GitHub Actions → Rollback workflow
2. Click "Run workflow"
3. Enter target version or select "use_previous"
4. Enter reason (required)
5. For production: Approve the manual approval step
6. Monitor workflow execution
7. Verify rollback in post-deployment validation

---

## Manual Workflow Triggers

### How to Trigger Workflows Manually

1. **Navigate to GitHub Actions:**
   - Go to your repository on GitHub
   - Click "Actions" tab

2. **Select Workflow:**
   - Choose the workflow from the left sidebar
   - Click "Run workflow" button

3. **Configure Inputs:**
   - Select branch (usually `main`)
   - Enter required inputs (for rollback, model_deploy)
   - Click "Run workflow"

### Available Manual Workflows

- **RAG Pipeline:** Full evaluation and deployment
- **Model Deploy:** Standalone deployment
- **Rollback:** Model version rollback

---

## Interpreting Results

### Success Indicators

✅ **All jobs green:** Pipeline completed successfully
- Model evaluated and deployed
- Quality gates passed
- Email notification sent

### Warning Indicators

⚠️ **Some jobs yellow/orange:** Non-critical issues
- Code quality warnings (non-blocking)
- Missing optional components (non-blocking)
- Email notification failed (non-blocking)

### Failure Indicators

❌ **Red jobs:** Critical failures
- Environment validation failed
- Evaluation pipeline failed
- Quality gates failed (deployment blocked)
- Deployment failed

### Common Failure Scenarios

1. **Environment Validation Failed:**
   - Missing dependencies
   - ChromaDB not accessible
   - Model file not found
   - **Solution:** Check prerequisites, ensure data pipeline has run

2. **Evaluation Pipeline Failed:**
   - Error in evaluation script
   - W&B connection issue
   - **Solution:** Check logs, verify W&B credentials

3. **Quality Gates Failed:**
   - Metrics below thresholds
   - **Solution:** Review metrics, adjust thresholds if needed, or fix model

4. **Deployment Failed:**
   - Registry path issues
   - Permission errors
   - **Solution:** Check file permissions, verify registry path

### Accessing Logs

1. **GitHub Actions Logs:**
   - Click on failed job
   - Expand failed step
   - View detailed logs

2. **W&B Dashboard:**
   - Link provided in email notification
   - View experiment tracking data

3. **Artifacts:**
   - Download `eval-results` artifact
   - Check `unified_summary.json` for metrics
   - Review `quality_gate_result.json` for gate details

---

## Best Practices

1. **Monitor Workflows:** Set up email notifications to stay informed
2. **Review Quality Gates:** Regularly review and adjust thresholds
3. **Test Locally First:** Run validation scripts locally before pushing
4. **Use Feature Branches:** Leverage component tests for fast feedback
5. **Document Rollbacks:** Always provide clear reasons for rollbacks
6. **Review Metrics:** Check W&B dashboard for detailed evaluation results

---

## Troubleshooting

For detailed troubleshooting steps, see [TROUBLESHOOTING.md](./TROUBLESHOOTING.md).

For configuration details, see [CONFIGURATION_GUIDE.md](./CONFIGURATION_GUIDE.md).

