# Troubleshooting Guide - FrontShiftAI CI/CD Pipeline

This guide helps you diagnose and resolve common issues with the CI/CD pipeline.

---

## Table of Contents

1. [Common Failure Scenarios](#common-failure-scenarios)
2. [Accessing Logs](#accessing-logs)
3. [Debugging Steps](#debugging-steps)
4. [Manual Rollback](#manual-rollback)
5. [FAQ](#faq)
6. [Getting Help](#getting-help)

---

## Common Failure Scenarios

### 1. Environment Validation Failed

**Symptoms:**
- Job: `setup-and-validation` fails
- Error: "Environment validation failed"

**Common Causes:**
- Missing Python packages
- ChromaDB not accessible
- Model file not found
- Environment variables not set

**Solutions:**

1. **Check Missing Packages:**
   ```bash
   # Locally, verify all packages are installed
   pip install -r requirements.txt
   pip install pyyaml  # For config parsing
   ```

2. **Verify ChromaDB:**
   ```bash
   # Check if ChromaDB exists
   ls -la data_pipeline/data/vector_db/
   
   # Test connection locally
   python -c "import chromadb; client = chromadb.PersistentClient(path='data_pipeline/data/vector_db'); print(client.list_collections())"
   ```

3. **Check Model File:**
   ```bash
   # Verify model file exists
   ls -lh models/Llama-3.2-3B-Instruct-Q4_K_S.gguf
   ```

4. **Verify Environment Variables:**
   - Check GitHub Secrets are set
   - Verify variable names match config
   - Test locally: `export WANDB_API_KEY=your_key`

---

### 2. Evaluation Pipeline Failed

**Symptoms:**
- Job: `run-evaluation` fails
- Error: Script execution error
- Missing `unified_summary.json`

**Common Causes:**
- Error in evaluation script
- W&B connection issue
- ChromaDB query failure
- Out of memory

**Solutions:**

1. **Check Evaluation Scripts:**
   ```bash
   # Run evaluation locally
   python ml_pipeline/eval_pipeline_runner.py
   ```

2. **Verify W&B Connection:**
   ```bash
   # Test W&B locally
   wandb login
   python -c "import wandb; wandb.init(project='FrontShiftAI', entity='group9mlops-northeastern-university')"
   ```

3. **Check ChromaDB Data:**
   ```bash
   # Verify data exists
   python -c "from ml_pipeline.rag.rag_query_utils import retrieve_context; docs, _ = retrieve_context('test', None, 5); print(f'Retrieved {len(docs)} docs')"
   ```

4. **Review Logs:**
   - Check `ml_pipeline/logs/` for detailed error messages
   - Review GitHub Actions logs for specific step failures

---

### 3. Quality Gates Failed

**Symptoms:**
- Job: `quality-gate-check` fails
- Error: "Quality gates failed"
- Deployment blocked

**Common Causes:**
- Metrics below thresholds
- Missing metric in unified_summary.json
- Incorrect threshold configuration

**Solutions:**

1. **Check Metrics:**
   ```bash
   # View evaluation results
   cat ml_pipeline/evaluation/eval_results/unified_summary.json
   ```

2. **Review Thresholds:**
   ```bash
   # Check current thresholds
   cat ml_pipeline/configs/quality_gates.yml
   ```

3. **Run Quality Gate Checker Locally:**
   ```bash
   python ml_pipeline/ci_cd/quality_gate_checker.py --environment production --verbose
   ```

4. **Adjust Thresholds (if appropriate):**
   - Edit `ml_pipeline/configs/quality_gates.yml`
   - Lower thresholds for development
   - Document why thresholds changed

5. **Fix Model/Evaluation:**
   - If metrics are legitimately low, fix the model or evaluation
   - Review W&B dashboard for insights

---

### 4. Deployment Failed

**Symptoms:**
- Job: `deploy-model` fails
- Error: "Deployment failed"
- Model not in registry

**Common Causes:**
- Model file not found
- Registry path issues
- Permission errors
- Metadata creation failed

**Solutions:**

1. **Verify Model File:**
   ```bash
   # Check model exists in artifacts
   ls -lh models/Llama-3.2-3B-Instruct-Q4_K_S.gguf
   ```

2. **Check Registry Path:**
   ```bash
   # Verify registry directory
   ls -la models_registry/
   ```

3. **Test Deployment Locally:**
   ```bash
   python ml_pipeline/ci_cd/deploy_model.py --dry-run
   ```

4. **Check Permissions:**
   - Ensure GitHub Actions has write permissions
   - Verify registry directory is writable

---

### 5. Email Notification Failed

**Symptoms:**
- Job: `notify` fails or skips
- No email received
- Warning in logs

**Common Causes:**
- Email credentials not set
- SMTP connection issue
- Invalid email addresses

**Solutions:**

1. **Verify Email Secrets:**
   - Check GitHub Secrets: `EMAIL_SENDER`, `EMAIL_PASSWORD`, `EMAIL_RECEIVER`
   - Verify secrets are set correctly

2. **Test Email Locally:**
   ```bash
   # Create email_config.json
   echo '{"sender": "your@email.com", "password": "app_password", "receiver": "recipient@email.com"}' > ml_pipeline/utils/email_config.json
   
   # Test email
   python ml_pipeline/utils/email_notifier.py
   ```

3. **Check SMTP Settings:**
   - For Gmail: Use App Password (not regular password)
   - Verify SMTP server and port in config

4. **Note:** Email failure is non-blocking, pipeline continues

---

### 6. ChromaDB Not Found in CI

**Symptoms:**
- ChromaDB validation fails in CI
- "Collection not found" error

**Common Causes:**
- ChromaDB not committed to repo
- Data pipeline hasn't run
- Path mismatch

**Solutions:**

1. **Run Data Pipeline First:**
   - Ensure data pipeline has run and created ChromaDB
   - Commit ChromaDB to repository (if small) or use DVC

2. **Check Paths:**
   - Verify `data_pipeline/data/vector_db/` exists
   - Check path in `pipeline_config.yml`

3. **Use DVC for Large Data:**
   ```bash
   # If using DVC
   dvc pull
   ```

---

## Accessing Logs

### GitHub Actions Logs

1. **Navigate to Actions:**
   - Go to repository → Actions tab
   - Select failed workflow run
   - Click on failed job
   - Expand failed step
   - View detailed logs

2. **Download Artifacts:**
   - Scroll to bottom of workflow run
   - Download `eval-results` artifact
   - Extract and review files

### Local Logs

```bash
# View pipeline logs
ls -la ml_pipeline/logs/

# View specific log file
tail -f ml_pipeline/logs/eval_pipeline_runner_2025-01-15.log
```

### W&B Dashboard

1. **Access Dashboard:**
   - Link provided in email notification
   - Or visit: https://wandb.ai/group9mlops-northeastern-university/FrontShiftAI

2. **View Runs:**
   - Select run from list
   - View metrics, artifacts, logs

---

## Debugging Steps

### Step 1: Reproduce Locally

```bash
# 1. Validate environment
python ml_pipeline/ci_cd/validate_environment.py --verbose

# 2. Run evaluation
python ml_pipeline/eval_pipeline_runner.py

# 3. Check quality gates
python ml_pipeline/ci_cd/quality_gate_checker.py --environment production --verbose

# 4. Test deployment (dry run)
python ml_pipeline/ci_cd/deploy_model.py --dry-run
```

### Step 2: Check Configuration

```bash
# Verify config files are valid YAML
python -c "import yaml; yaml.safe_load(open('ml_pipeline/configs/quality_gates.yml'))"
python -c "import yaml; yaml.safe_load(open('ml_pipeline/configs/pipeline_config.yml'))"
```

### Step 3: Review Evaluation Results

```bash
# Check all evaluation outputs
ls -la ml_pipeline/evaluation/eval_results/

# View unified summary
cat ml_pipeline/evaluation/eval_results/unified_summary.json | jq .

# View quality gate results
cat quality_gate_result.json | jq .
```

### Step 4: Test Individual Components

```bash
# Test RAG retrieval
python -c "from ml_pipeline.rag.rag_query_utils import retrieve_context; docs, _ = retrieve_context('test', None, 5); print(len(docs))"

# Test W&B connection
python -c "import wandb; wandb.init(project='FrontShiftAI', entity='group9mlops-northeastern-university'); wandb.finish()"
```

---

## Manual Rollback

### When to Rollback

- Model performance degraded
- Critical bugs discovered
- Need to revert to known-good version

### Rollback Steps

1. **List Available Versions:**
   ```bash
   python ml_pipeline/ci_cd/rollback_model.py --list-versions
   ```

2. **Review Target Version:**
   ```bash
   # Check target version metadata
   cat models_registry/llama_3b_instruct_v5/metadata.json | jq .
   ```

3. **Execute Rollback:**
   ```bash
   # Via GitHub Actions (recommended)
   # Go to Actions → Rollback workflow → Run workflow
   # Enter target version and reason
   
   # Or locally (if needed)
   python ml_pipeline/ci_cd/rollback_model.py \
     --target-version v5 \
     --reason "Performance degradation in production"
   ```

4. **Verify Rollback:**
   ```bash
   # Check latest symlink
   ls -la models_registry/latest
   
   # Verify metadata
   cat models_registry/latest/metadata.json | jq .
   ```

### Rollback via GitHub Actions

1. Go to Actions → Rollback workflow
2. Click "Run workflow"
3. Select branch (usually `main`)
4. Enter:
   - Target version (e.g., "v5") or check "use_previous"
   - Reason (required)
5. For production: Approve manual approval step
6. Monitor workflow execution

---

## FAQ

### Q: Why did my deployment get blocked?

**A:** Quality gates failed. Check:
1. View quality gate results in workflow logs
2. Review metrics in `unified_summary.json`
3. Compare against thresholds in `quality_gates.yml`
4. Fix model or adjust thresholds

### Q: How do I skip quality gates for testing?

**A:** Not recommended, but you can:
1. Temporarily lower thresholds in `quality_gates.yml`
2. Use development environment (lower thresholds)
3. Deploy manually using `model_deploy.yml` workflow

### Q: Why is ChromaDB not found in CI?

**A:** ChromaDB needs to be:
1. Committed to repository (if small)
2. Or pulled via DVC: `dvc pull`
3. Or created by running data pipeline first

### Q: How do I change email notification recipients?

**A:** Update GitHub Secret:
1. Go to Settings → Secrets → Actions
2. Update `EMAIL_RECEIVER` secret
3. Or modify `notification_config.yml` if using different variable

### Q: Can I run the pipeline locally?

**A:** Yes:
```bash
# Full pipeline
python ml_pipeline/eval_pipeline_runner.py

# Individual components
python ml_pipeline/evaluation/rag_eval_metrics.py
python ml_pipeline/ci_cd/quality_gate_checker.py --environment production
```

### Q: How do I add a new quality gate metric?

**A:** See [CONFIGURATION_GUIDE.md](./CONFIGURATION_GUIDE.md#adding-new-metrics):
1. Add metric to evaluation output
2. Add metric mapping in `quality_gates.yml`
3. Add thresholds for each environment
4. Test quality gate checker

### Q: Why is the workflow taking so long?

**A:** Check:
1. Evaluation pipeline: ~10-20 minutes (normal)
2. Quality gates: ~2-5 minutes (normal)
3. If longer: Check for timeouts, resource constraints
4. Review workflow logs for bottlenecks

### Q: How do I disable email notifications?

**A:** In `notification_config.yml`:
```yaml
email:
  enabled: false
```

Or remove email secrets from GitHub (workflow will skip email step).

---

## Getting Help

### Internal Resources

1. **Documentation:**
   - [WORKFLOW_GUIDE.md](./WORKFLOW_GUIDE.md) - Workflow details
   - [CONFIGURATION_GUIDE.md](./CONFIGURATION_GUIDE.md) - Configuration details

2. **Code:**
   - Review scripts in `ml_pipeline/ci_cd/`
   - Check evaluation scripts in `ml_pipeline/evaluation/`

3. **Logs:**
   - GitHub Actions logs
   - Local logs in `ml_pipeline/logs/`
   - W&B dashboard

### External Resources

1. **GitHub Issues:**
   - Create issue in repository
   - Include: error logs, steps to reproduce, environment details

2. **W&B Support:**
   - W&B documentation: https://docs.wandb.ai
   - W&B community: https://wandb.ai/community

3. **GitHub Actions:**
   - GitHub Actions documentation: https://docs.github.com/en/actions

### Reporting Issues

When reporting issues, include:

1. **Error Message:** Full error from logs
2. **Workflow Run:** Link to GitHub Actions run
3. **Steps to Reproduce:** What triggered the failure
4. **Environment:** Branch, commit hash, environment
5. **Configuration:** Relevant config file snippets
6. **Logs:** Relevant log excerpts

### Example Issue Report

```
**Issue:** Quality gates failing incorrectly

**Error:** Quality gate check failed with "mean_semantic_sim below threshold"

**Workflow:** https://github.com/.../actions/runs/12345

**Steps:**
1. Pushed to main branch
2. Evaluation completed successfully
3. Quality gate check failed

**Metrics:**
- mean_semantic_sim: 0.48
- Threshold: 0.45 (should pass)

**Environment:** Production, main branch

**Config:** quality_gates.yml (production section)
```

---

## Prevention Tips

1. **Test Locally First:** Always test changes locally before pushing
2. **Use Feature Branches:** Leverage component tests for fast feedback
3. **Monitor Metrics:** Regularly review W&B dashboard for trends
4. **Review Thresholds:** Periodically review and adjust quality gate thresholds
5. **Keep Dependencies Updated:** Regularly update requirements.txt
6. **Document Changes:** Document configuration and threshold changes
7. **Backup Before Rollback:** Always backup current version before rollback

---

For workflow details, see [WORKFLOW_GUIDE.md](./WORKFLOW_GUIDE.md).

For configuration details, see [CONFIGURATION_GUIDE.md](./CONFIGURATION_GUIDE.md).

