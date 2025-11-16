# Configuration Guide - FrontShiftAI CI/CD Pipeline

This guide explains how to configure the CI/CD pipeline, modify thresholds, and customize settings.

---

## Table of Contents

1. [Configuration Files Overview](#configuration-files-overview)
2. [Quality Gates Configuration](#quality-gates-configuration)
3. [Pipeline Configuration](#pipeline-configuration)
4. [Notification Configuration](#notification-configuration)
5. [Environment Variables](#environment-variables)
6. [Modifying Thresholds](#modifying-thresholds)
7. [Adding New Metrics](#adding-new-metrics)

---

## Configuration Files Overview

All configuration files are located in `ml_pipeline/configs/`:

- **`quality_gates.yml`:** Quality gate thresholds for different environments
- **`pipeline_config.yml`:** Pipeline paths, model settings, and evaluation configuration
- **`notification_config.yml`:** Email and Slack notification settings

---

## Quality Gates Configuration

**File:** `ml_pipeline/configs/quality_gates.yml`

### Structure

```yaml
environments:
  development:
    critical:
      mean_semantic_sim:
        min: 0.40
      mean_precision_at_k:
        min: 0.70
    warning:
      mean_semantic_sim:
        min: 0.45
  staging:
    # Similar structure with higher thresholds
  production:
    # Similar structure with highest thresholds
```

### Environment-Specific Thresholds

#### Development
- **Purpose:** Local development and testing
- **Thresholds:** Most lenient
- **Use Case:** Quick iteration, experimental changes

#### Staging
- **Purpose:** Pre-production testing
- **Thresholds:** Moderate
- **Use Case:** Validating changes before production

#### Production
- **Purpose:** Production deployment
- **Thresholds:** Strictest
- **Use Case:** Final deployment after validation

### Threshold Types

#### Critical Thresholds
- **Behavior:** Must pass for deployment approval
- **Failure:** Blocks deployment
- **Examples:**
  - `mean_semantic_sim.min: 0.45`
  - `mean_precision_at_k.min: 0.80`
  - `max_bias_gap.max: 0.15`

#### Warning Thresholds
- **Behavior:** Generate warnings but may not block deployment
- **Failure:** May block deployment if `allow_warnings: false`
- **Examples:**
  - `mean_semantic_sim.min: 0.50` (warning level)
  - `sensitivity_variance.max: 0.10`

#### Performance Thresholds
- **Behavior:** Monitor execution time and memory
- **Failure:** Logs warning, doesn't block deployment
- **Examples:**
  - `max_execution_time_seconds: 600`
  - `max_memory_mb: 4096`

### Deployment Decision Rules

```yaml
deployment_decision:
  require_all_critical: true  # All critical thresholds must pass
  allow_warnings: true         # Allow deployment with warnings
```

- **`require_all_critical: true`:** All critical thresholds must pass
- **`allow_warnings: true`:** Deployment allowed even with warning threshold failures
- **`allow_warnings: false`:** Deployment blocked if any warning threshold fails

### Metric Mapping

Maps metric names from `unified_summary.json` to threshold keys:

```yaml
metric_mapping:
  mean_semantic_sim: "rag.mean_semantic_sim"
  mean_precision_at_k: "rag.mean_precision_at_k"
  max_bias_gap: "bias.max_sim_gap"
  sensitivity_variance: "sensitivity.variance"
```

---

## Pipeline Configuration

**File:** `ml_pipeline/configs/pipeline_config.yml`

### Vector Database Settings

```yaml
vector_db:
  path: "data_pipeline/data/vector_db"
  collection_name: "frontshift_handbooks"
  embedding_model: "all-MiniLM-L6-v2"
```

**Modify if:**
- ChromaDB is in a different location
- Using a different collection name
- Changing embedding model

### RAG Evaluation Settings

```yaml
rag_evaluation:
  top_k: 5
  semantic_similarity_model: "all-MiniLM-L6-v2"
```

**Modify if:**
- Changing number of retrieved documents
- Using different similarity model

### Model Configuration

```yaml
model:
  name: "llama_3b_instruct"
  file_name: "Llama-3.2-3B-Instruct-Q4_K_S.gguf"
  path: "models/Llama-3.2-3B-Instruct-Q4_K_S.gguf"
```

**Modify if:**
- Using a different model
- Model file is in a different location
- Changing model name

### Evaluation Results Paths

```yaml
evaluation:
  results_dir: "ml_pipeline/evaluation/eval_results"
  unified_summary_file: "ml_pipeline/evaluation/eval_results/unified_summary.json"
```

**Modify if:**
- Changing output directory structure
- Using different file names

### Model Registry Configuration

```yaml
registry:
  path: "models_registry"
  metadata_file: "metadata.json"
  latest_symlink: "latest"
```

**Modify if:**
- Changing registry location
- Using different metadata format

### Experiment Tracking

```yaml
tracking:
  platform: "wandb"
  entity: "${WANDB_ENTITY}"
  project: "${WANDB_PROJECT}"
```

**Modify if:**
- Switching to different tracking platform (MLflow, etc.)
- Changing W&B project/entity

---

## Notification Configuration

**File:** `ml_pipeline/configs/notification_config.yml`

### Email Configuration

```yaml
email:
  enabled: true
  smtp:
    server: "smtp.gmail.com"
    port_ssl: 465
    port_tls: 587
  credentials:
    sender_env: "EMAIL_SENDER"
    password_env: "EMAIL_PASSWORD"
    receiver_env: "EMAIL_RECEIVER"
```

**Modify if:**
- Using different email provider
- Changing SMTP settings
- Using different environment variable names

### Slack Configuration

```yaml
slack:
  enabled: false
  webhook_url_env: "SLACK_WEBHOOK_URL"
  channel: "#ml-pipeline"
```

**To Enable Slack:**
1. Set `enabled: true`
2. Add `SLACK_WEBHOOK_URL` to GitHub Secrets
3. Update notification rules to include "slack" in channels

### Notification Rules

```yaml
rules:
  triggers:
    - event: "pipeline_success"
      send: true
      channels: ["email"]
    - event: "pipeline_failure"
      send: true
      channels: ["email"]
```

**Modify if:**
- Changing when notifications are sent
- Adding/removing notification channels
- Customizing notification content

---

## Environment Variables

### Required Variables

Set in GitHub Secrets or environment:

- **`WANDB_API_KEY`:** Weights & Biases API key
- **`WANDB_ENTITY`:** W&B entity (e.g., "group9mlops-northeastern-university")
- **`WANDB_PROJECT`:** W&B project name (e.g., "FrontShiftAI")
- **`PYTHONPATH`:** Project root directory (set automatically in workflows)

### Optional Variables

- **`EMAIL_SENDER`:** Email sender address
- **`EMAIL_PASSWORD`:** Email app password
- **`EMAIL_RECEIVER`:** Email recipient
- **`TOKENIZERS_PARALLELISM`:** Set to "false" to avoid warnings
- **`SLACK_WEBHOOK_URL`:** Slack webhook URL (if using Slack)

### Setting GitHub Secrets

1. Go to repository → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Add each secret:
   - Name: `WANDB_API_KEY`
   - Value: Your W&B API key
4. Repeat for other secrets

---

## Modifying Thresholds

### Step-by-Step Guide

1. **Open Configuration File:**
   ```bash
   vim ml_pipeline/configs/quality_gates.yml
   ```

2. **Locate Environment:**
   - Find the environment section (development/staging/production)

3. **Modify Threshold:**
   ```yaml
   critical:
     mean_semantic_sim:
       min: 0.50  # Changed from 0.45
   ```

4. **Save and Commit:**
   ```bash
   git add ml_pipeline/configs/quality_gates.yml
   git commit -m "Update quality gate thresholds"
   git push
   ```

5. **Test Changes:**
   - Push to feature branch
   - Run component tests
   - Verify thresholds work as expected

### Best Practices

- **Start Conservative:** Begin with stricter thresholds, relax if needed
- **Test in Development:** Test threshold changes in development environment first
- **Document Changes:** Add comments explaining why thresholds changed
- **Monitor Impact:** Check how many deployments are blocked/allowed after changes

---

## Adding New Metrics

### Step 1: Add Metric to Evaluation

Ensure your evaluation script outputs the new metric in `unified_summary.json`:

```json
{
  "rag": {
    "mean_semantic_sim": 0.52,
    "new_metric": 0.85
  }
}
```

### Step 2: Add Metric Mapping

In `quality_gates.yml`:

```yaml
metric_mapping:
  new_metric: "rag.new_metric"
```

### Step 3: Add Thresholds

In `quality_gates.yml`:

```yaml
environments:
  production:
    critical:
      new_metric:
        min: 0.80
        description: "New metric threshold"
```

### Step 4: Update Quality Gate Checker

The `quality_gate_checker.py` will automatically pick up new metrics if they're in the mapping. If you need custom calculation logic, modify the checker script.

### Step 5: Test

1. Run evaluation pipeline
2. Verify metric appears in `unified_summary.json`
3. Run quality gate checker
4. Verify threshold is checked correctly

---

## Configuration Validation

### Validate Configuration Files

```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('ml_pipeline/configs/quality_gates.yml'))"

# Validate paths exist
python ml_pipeline/ci_cd/validate_environment.py
```

### Common Configuration Errors

1. **Invalid YAML Syntax:**
   - Missing colons
   - Incorrect indentation
   - **Fix:** Use YAML linter

2. **Path Not Found:**
   - Relative paths incorrect
   - Files don't exist
   - **Fix:** Verify paths relative to project root

3. **Environment Variable Not Set:**
   - Variable referenced but not set
   - **Fix:** Add to GitHub Secrets or environment

4. **Threshold Logic Error:**
   - min > max
   - Invalid comparison operators
   - **Fix:** Review threshold definitions

---

## Advanced Configuration

### Custom Quality Gate Logic

To add custom quality gate logic:

1. Modify `ml_pipeline/ci_cd/quality_gate_checker.py`
2. Add custom check function
3. Integrate into `check_quality_gates()` function

### Custom Notification Templates

1. Edit templates in `ml_pipeline/ci_cd/templates/`
2. Use Jinja2 syntax for variable substitution
3. Update `notification_config.yml` to reference new templates

### Multi-Environment Deployment

To deploy to different environments based on branch:

1. Update workflow to set environment based on branch
2. Configure environment-specific thresholds
3. Use environment-specific notification rules

---

## Troubleshooting Configuration

### Issue: Thresholds Not Applied

**Symptoms:** Quality gates always pass/fail regardless of thresholds

**Solutions:**
1. Verify metric mapping is correct
2. Check metric names in `unified_summary.json`
3. Verify threshold file is loaded correctly
4. Check quality gate checker logs

### Issue: Path Not Found

**Symptoms:** Scripts can't find files/directories

**Solutions:**
1. Verify paths are relative to project root
2. Check file/directory exists
3. Verify permissions
4. Test paths locally before pushing

### Issue: Environment Variables Not Set

**Symptoms:** Scripts fail with "variable not found"

**Solutions:**
1. Check GitHub Secrets are set
2. Verify variable names match config
3. Check workflow environment variable setup
4. Test locally with exported variables

---

## Configuration Examples

### Example 1: Stricter Production Thresholds

```yaml
production:
  critical:
    mean_semantic_sim:
      min: 0.50  # Increased from 0.45
    mean_precision_at_k:
      min: 0.85  # Increased from 0.80
```

### Example 2: Adding New Metric

```yaml
# In metric_mapping
metric_mapping:
  response_time: "performance.avg_response_time_ms"

# In thresholds
production:
  warning:
    response_time:
      max: 5000  # 5 seconds max
```

### Example 3: Enabling Slack Notifications

```yaml
slack:
  enabled: true
  webhook_url_env: "SLACK_WEBHOOK_URL"

rules:
  triggers:
    - event: "pipeline_success"
      channels: ["email", "slack"]
```

---

For workflow details, see [WORKFLOW_GUIDE.md](./WORKFLOW_GUIDE.md).

For troubleshooting, see [TROUBLESHOOTING.md](./TROUBLESHOOTING.md).

