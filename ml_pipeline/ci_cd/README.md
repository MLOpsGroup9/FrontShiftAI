# CI/CD Module

## Current Status

The CI/CD system is implemented and ready for review. It's not active yet - workflows are configured to only run on the main branch.

### What's Done

- Quality gates with environment-specific thresholds
- Automated deployment with model registry versioning
- Rollback mechanism with audit trail
- Email notification templates
- Documentation

### What Still Needs Setup

- GitHub Secrets need to be configured (see docs/SECRETS_SETUP.md)
- Workflows are disabled on feature branches
- Email sending will be skipped until real secrets are configured

### For Reviewers

**What to check:**

1. **Configuration files** (`ml_pipeline/configs/`)
   - Thresholds make sense
   - Paths are correct
   - Nothing missing

2. **Scripts** (`ml_pipeline/ci_cd/*.py`)
   - Code looks good
   - Error handling is solid
   - Works with existing components

3. **Workflows** (`.github/workflows/`)
   - Job structure makes sense
   - Artifacts are handled properly
   - Triggers are set up correctly

4. **Documentation** (`ml_pipeline/ci_cd/docs/`)
   - Clear and complete
   - Easy to follow
   - Good examples

5. **Templates** (`ml_pipeline/ci_cd/templates/`)
   - Email templates look professional
   - Variables are correct
   - Content is helpful

**Testing locally (optional):**

```bash
# Set placeholder environment variables
export WANDB_API_KEY="PLACEHOLDER_WANDB_KEY"
export EMAIL_SENDER="placeholder@gmail.com"
export EMAIL_PASSWORD="PLACEHOLDER_APP_PASSWORD"
export EMAIL_RECEIVER="placeholder-receiver@gmail.com"
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Test validation (will warn about placeholders)
python ml_pipeline/ci_cd/validate_environment.py --verbose

# Test quality gate (after running evaluation)
python ml_pipeline/eval_pipeline_runner.py
python ml_pipeline/ci_cd/quality_gate_checker.py --environment development

# Test deploy (dry run)
python ml_pipeline/ci_cd/deploy_model.py --dry-run
```

Scripts will detect placeholder values and warn, but won't fail.

---

## Before Merging to Main

**Checklist:**

- [ ] Code reviewed and approved
- [ ] Documentation reviewed
- [ ] GitHub Secrets configured (see `docs/SECRETS_SETUP.md`)
- [ ] Workflow triggers confirmed (only on main branch)
- [ ] Local testing completed
- [ ] Email templates approved
- [ ] Quality gate thresholds agreed upon

**After merge:**

- Workflows will auto-trigger on pushes to main
- Email notifications will be sent
- Models will be deployed to registry
- Rollback available if needed

---

## Documentation

- [Workflow Guide](docs/WORKFLOW_GUIDE.md) - How workflows work
- [Configuration Guide](docs/CONFIGURATION_GUIDE.md) - Modifying configs
- [Secrets Setup](docs/SECRETS_SETUP.md) - GitHub Secrets configuration
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions
- [Review Checklist](REVIEW_CHECKLIST.md) - For code reviewers

---

## Integration Points

**Uses existing components:**

- `ml_pipeline/eval_pipeline_runner.py` - Main orchestrator
- `ml_pipeline/tracking/exp_tracking.py` - W&B logging
- `ml_pipeline/tracking/push_to_registry.py` - Model versioning
- `ml_pipeline/utils/email_notifier.py` - Email sending
- `ml_pipeline/utils/logger.py` - Logging

**Does not modify:**

- `data_pipeline/` - Remains untouched
- Existing evaluation scripts
- Existing tracking logic

---

## Activation Plan

**Phase 1: Review (Current)**

- Code pushed to feature branch for review
- Workflows disabled on feature branches
- Placeholder secrets in documentation

**Phase 2: Configuration (Before main merge)**

- Configure real GitHub Secrets
- Test workflows manually (workflow_dispatch)
- Verify email notifications work

**Phase 3: Activation (After main merge)**

- Workflows auto-trigger on main branch
- Full CI/CD pipeline active
- Monitor first few runs

---

## Contact

Questions or issues? Contact the ML team or check documentation in `docs/`.
