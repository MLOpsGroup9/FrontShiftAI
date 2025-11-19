# Inception Labs Mercury Model Setup Guide

This guide explains how to set up and configure the Inception Labs Mercury model for the FrontShiftAI backend API.

## Overview

The backend API uses the Inception Labs Mercury model via their API, which is compatible with OpenAI's API interface. This provides:
- Fast inference times
- High-quality responses
- No local model files required
- Scalable API-based deployment
- Pay-as-you-go pricing

## Setup Steps

### 1. Create Inception Labs Account

1. Visit [Inception Platform](https://platform.inceptionlabs.ai/)
2. Sign up for an account
3. Complete the registration process

### 2. Subscribe to a Plan

1. Navigate to the billing section
2. Choose a plan that suits your needs
3. Complete the subscription process

### 3. Generate API Key

1. Go to the API section in the dashboard
2. Click "Generate API Key"
3. Copy the API key (you won't be able to see it again)
4. Store it securely

### 4. Configure Environment Variables

**Linux/Mac:**
```bash
export INCEPTION_API_KEY=your_api_key_here
export MERCURY_MODEL=mercury-v1  # Optional
```

**Windows:**
```cmd
set INCEPTION_API_KEY=your_api_key_here
set MERCURY_MODEL=mercury-v1
```

**Or use a .env file:**
```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your API key
INCEPTION_API_KEY=your_api_key_here
MERCURY_MODEL=mercury-v1
```

### 5. Install Dependencies

```bash
cd frontend/backend_api
pip install -r requirements.txt
```

### 6. Start the API Server

```bash
python rag_api.py
```

Or use the startup script:
```bash
# Linux/Mac
./start_backend.sh

# Windows
start_backend.bat
```

## Available Models

- `mercury-v1` - Standard Mercury model (default)
- `mercury-coder-small` - Smaller coding-focused model
- Check the [Inception Platform](https://platform.inceptionlabs.ai/) for the latest available models

## Testing

### Test Health Endpoint

```bash
curl http://localhost:8001/health
```

Expected response:
```json
{
  "status": "ok",
  "model_type": "Inception Labs Mercury",
  "model": "mercury-v1",
  "api_base": "https://api.inceptionlabs.ai/v1",
  "api_key_configured": true,
  "api_key_set": true
}
```

### Test RAG Query

```bash
curl -X POST http://localhost:8001/api/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is my leave policy?",
    "company_name": "Company Name",
    "top_k": 4
  }'
```

## Troubleshooting

### API Key Issues

**"API key not configured" error:**
- Verify `INCEPTION_API_KEY` is set: `echo $INCEPTION_API_KEY`
- Check for typos in the API key
- Ensure the API key is from a valid account

**"Authentication failed" error:**
- Verify the API key is correct
- Check that your account has an active subscription
- Ensure the API key hasn't been revoked

### Connection Issues

**"Connection failed" error:**
- Check your internet connection
- Verify the API URL is accessible: `curl https://api.inceptionlabs.ai/v1/chat/completions`
- Check for firewall restrictions

**"Rate limit exceeded" error:**
- Check your subscription plan limits
- Implement rate limiting in your application
- Consider upgrading your plan

### Model Issues

**"Model not found" error:**
- Verify the model name is correct
- Check available models in the dashboard
- Ensure the model is available for your plan

### Response Format Issues

The API uses OpenAI's chat completions format. If you encounter issues:

1. Check the response structure:
   ```python
   print(json.dumps(response.json(), indent=2))
   ```

2. Verify the response contains `choices[0].message.content`

3. Check the API documentation for any format changes

## API Usage

The Inception Labs API is compatible with OpenAI's API, so you can use it similarly:

```python
import requests

response = requests.post(
    "https://api.inceptionlabs.ai/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {INCEPTION_API_KEY}",
        "Content-Type": "application/json",
    },
    json={
        "model": "mercury-v1",
        "messages": [
            {"role": "user", "content": "Hello!"}
        ],
        "max_tokens": 1000,
    }
)

result = response.json()
print(result["choices"][0]["message"]["content"])
```

## Cost Management

- Monitor your API usage in the dashboard
- Set up usage alerts if available
- Review your billing regularly
- Optimize prompts to reduce token usage

## Security Best Practices

1. **Never commit API keys to version control**
   - Use `.env` files and add them to `.gitignore`
   - Use environment variables in production
   - Use secrets management services

2. **Rotate API keys regularly**
   - Generate new keys periodically
   - Revoke old keys when not needed

3. **Restrict API key permissions**
   - Use the minimum required permissions
   - Monitor API key usage

4. **Use HTTPS**
   - Always use HTTPS for API calls
   - Never send API keys over unencrypted connections

## Support

For issues or questions:
1. Check the [Inception Labs documentation](https://platform.inceptionlabs.ai/)
2. Review the [backend API README](./README.md)
3. Contact Inception Labs support through the platform
4. Check the API status page if available

## Migration Notes

### From Llama.cpp

- **No local model files:** Everything runs via API
- **Faster startup:** No model loading required
- **Always updated:** Uses the latest model version
- **Scalable:** Handles traffic automatically
- **Cost effective:** Pay only for what you use

### API Compatibility

The Inception Labs API is compatible with OpenAI's API, so:
- You can use OpenAI client libraries
- The request/response format is the same
- Migration from OpenAI is straightforward

## Next Steps

1. Test the API with sample queries
2. Monitor API usage and costs
3. Optimize prompts for better results
4. Set up error handling and retries
5. Implement rate limiting if needed

