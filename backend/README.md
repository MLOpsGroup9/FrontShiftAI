# FrontShiftAI Backend API - Inception Labs Mercury Model Integration

This backend API service provides RAG (Retrieval-Augmented Generation) queries using the Inception Labs Mercury model instead of Llama.cpp.

The Inception Labs API is compatible with OpenAI's API interface, making it easy to integrate.

## Configuration

### Setup Inception Labs API

1. **Create an Account:**
   - Visit [Inception Platform](https://platform.inceptionlabs.ai/)
   - Create an account and subscribe to a billing plan

2. **Get API Key:**
   - Generate an API key from the dashboard
   - Copy your API key

3. **Set Environment Variables:**
   ```bash
   export INCEPTION_API_KEY=your_api_key_here
   export MERCURY_MODEL=mercury-v1  # Optional: defaults to mercury-v1
   export INCEPTION_API_BASE=https://api.inceptionlabs.ai/v1  # Optional: defaults to this
   ```

### Available Models

- `mercury-v1` - Standard Mercury model (default)
- `mercury-coder-small` - Smaller coding-focused model
- Other models as available on the platform

## Installation

```bash
cd frontend/backend_api
pip install -r requirements.txt
```

## Running the API

### Basic usage:
```bash
python rag_api.py
```

### With environment variables:
```bash
# For Bedrock
USE_BEDROCK=true AWS_REGION=us-east-1 python rag_api.py

# For Direct API
MERCURY_API_ENDPOINT=https://api.example.com/mercury/v1/completions MERCURY_API_KEY=your_key python rag_api.py
```

### Using startup script:
```bash
# Linux/Mac
./start_backend.sh

# Windows
start_backend.bat
```

## Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `INCEPTION_API_KEY` | Inception Labs API key | `None` | **Yes** |
| `MERCURY_MODEL` | Mercury model name | `mercury-v1` | No |
| `INCEPTION_API_BASE` | API base URL | `https://api.inceptionlabs.ai/v1` | No |
| `PORT` | API server port | `8001` | No |

## API Endpoints

### Health Check
```
GET /health
```

Response:
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

### RAG Query
```
POST /api/rag/query
```

Request:
```json
{
  "query": "What is my leave policy?",
  "company_name": "Company Name",
  "top_k": 4
}
```

Response:
```json
{
  "answer": "Your leave policy...",
  "sources": [
    {
      "company": "Company Name",
      "filename": "handbook.pdf",
      "chunk_id": "1"
    }
  ],
  "query": "What is my leave policy?",
  "company_name": "Company Name"
}
```

## Getting Your API Key

1. **Visit Inception Platform:**
   - Go to [https://platform.inceptionlabs.ai/](https://platform.inceptionlabs.ai/)
   - Sign up for an account

2. **Subscribe to a Plan:**
   - Choose a billing plan that suits your needs
   - Complete the subscription process

3. **Generate API Key:**
   - Navigate to the API section in the dashboard
   - Generate a new API key
   - Copy the API key (you won't be able to see it again)

4. **Set Environment Variable:**
   ```bash
   export INCEPTION_API_KEY=your_api_key_here
   ```
   
   Or create a `.env` file:
   ```bash
   INCEPTION_API_KEY=your_api_key_here
   ```

## Troubleshooting

### API Key Issues

**API key not set:**
- Verify `INCEPTION_API_KEY` environment variable is set
- Check that the API key is copied correctly (no extra spaces)
- Ensure the API key is from a valid Inception Labs account

**Authentication failed:**
- Verify API key is correct and not expired
- Check that your account has an active subscription
- Ensure the API key has the required permissions

### API Connection Issues

**Connection failed:**
- Check network connectivity
- Verify the API base URL is correct: `https://api.inceptionlabs.ai/v1`
- Check if there are any firewall restrictions

**Rate limiting:**
- Check your subscription plan limits
- Implement retry logic with exponential backoff
- Monitor your API usage in the dashboard

**Model not found:**
- Verify the model name is correct (e.g., `mercury-v1`, `mercury-coder-small`)
- Check available models in the Inception Labs dashboard
- Ensure the model is available for your subscription plan

### General Issues

**ChromaDB not found:**
- Verify ChromaDB is initialized in `data_pipeline/data/vector_db/`
- Check collection name: `frontshift_handbooks`
- Ensure embeddings are generated

**Import errors:**
- Verify Python path includes project root
- Check that `ml_pipeline` is in Python path
- Ensure all dependencies are installed

## Testing

### Test Health Endpoint:
```bash
curl http://localhost:8001/health
```

### Test RAG Query:
```bash
curl -X POST http://localhost:8001/api/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is my leave policy?",
    "company_name": "Company Name",
    "top_k": 4
  }'
```

## Migration from Llama.cpp

The backend has been updated to use Inception Labs Mercury model instead of Llama.cpp:

1. **Removed:** Llama.cpp dependencies and local model files
2. **Added:** Requests library for API calls
3. **Updated:** Model inference to use Inception Labs API (OpenAI-compatible)
4. **Simplified:** No local model loading required

The RAG pipeline (ChromaDB retrieval) remains unchanged. Only the text generation component has been updated to use Mercury via API.

### Benefits

- **No Local Model Files:** No need to download or store large model files
- **Faster Startup:** API-based inference starts immediately
- **Scalable:** Handles traffic spikes automatically
- **Always Updated:** Uses the latest model version from Inception Labs
- **Cost Effective:** Pay only for what you use

## Notes

- Inception Labs Mercury model provides fast inference and high-quality responses
- API is compatible with OpenAI's interface, making it easy to integrate
- No local model files required - everything runs via API
- Response format follows OpenAI's chat completions format
- Check the [Inception Labs documentation](https://platform.inceptionlabs.ai/) for the latest model options and features

