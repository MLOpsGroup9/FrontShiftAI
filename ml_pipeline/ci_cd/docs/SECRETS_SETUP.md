# GitHub Secrets Setup Guide

## Required Secrets Configuration

Before the CI/CD workflows can run, configure these secrets in your GitHub repository:

**Path:** Repository Settings → Secrets and variables → Actions → New repository secret

---

## Required Secrets

### 1. WANDB_API_KEY

**Description:** Weights & Biases API key for experiment tracking

**How to get:**

1. Login to https://wandb.ai
2. Go to Settings → API Keys
3. Copy your API key
4. Add as secret: `WANDB_API_KEY`

**Placeholder (for testing):** `PLACEHOLDER_WANDB_KEY`

---

### 2. EMAIL_SENDER

**Description:** Gmail address to send notifications from

**Format:** `your-email@gmail.com`

**Placeholder (for testing):** `placeholder@gmail.com`

---

### 3. EMAIL_PASSWORD

**Description:** Gmail App Password (NOT your regular Gmail password)

**How to get:**

1. Go to Google Account → Security
2. Enable 2-Step Verification (required)
3. Go to Security → 2-Step Verification → App Passwords
4. Generate new app password for "Mail"
5. Copy the 16-character password
6. Add as secret: `EMAIL_PASSWORD`

**Important:** 
- Must use App Password, not regular password
- Requires 2FA enabled on Gmail account
- Keep this secret secure

**Placeholder (for testing):** `PLACEHOLDER_APP_PASSWORD`

---

### 4. EMAIL_RECEIVER

**Description:** Email address to receive CI/CD notifications

**Format:** `recipient@email.com`

**Placeholder (for testing):** `placeholder-receiver@gmail.com`

---

## Optional Secrets

### SLACK_WEBHOOK_URL

**Description:** Slack webhook URL for notifications (if using Slack)

**How to get:**

1. Go to your Slack workspace
2. Create Incoming Webhook app
3. Copy webhook URL
4. Add as secret: `SLACK_WEBHOOK_URL`

**Status:** Currently disabled in `ml_pipeline/configs/notification_config.yml`

---

## Verification

After adding secrets, verify they are set:

1. Go to Repository Settings → Secrets and variables → Actions
2. You should see:
   - WANDB_API_KEY
   - EMAIL_SENDER
   - EMAIL_PASSWORD
   - EMAIL_RECEIVER

## Testing Secrets Locally

**DO NOT** put real secrets in config files or code. Always use environment variables:

```bash
export WANDB_API_KEY="your-key"
export EMAIL_SENDER="your-email@gmail.com"
export EMAIL_PASSWORD="your-app-password"
export EMAIL_RECEIVER="recipient@email.com"

# Test validation
python ml_pipeline/ci_cd/validate_environment.py --verbose
```

---

## Security Notes

- Never commit secrets to git
- Never share secrets in chat or documentation
- Rotate secrets if compromised
- Use GitHub Secrets for CI/CD (never hardcode)
- Consider using GitHub Environments for production secrets

---

## When to Configure

**Configure these secrets when:**

- Ready to test CI/CD workflows on main branch
- Before merging feature branch to main
- Before enabling automatic workflow triggers

**Until then:**

- Workflows are disabled on feature branches
- Placeholders in documentation only
- Manual testing can use local environment variables

