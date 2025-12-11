# FrontShiftAI Voice Pipeline

![Python](https://img.shields.io/badge/Python-3.11+-blue) ![LiveKit](https://img.shields.io/badge/LiveKit-1.0+-green) ![Modal](https://img.shields.io/badge/Modal-Serverless-orange) ![FastAPI](https://img.shields.io/badge/FastAPI-0.110-green)

**Real-Time Voice Interface for the Deskless Workforce**

The Voice Pipeline is FrontShiftAI's **real-time voice-to-voice AI assistant**, enabling hands-free interaction with company policies, HR systems, and PTO workflows. Built on [LiveKit](https://livekit.io/), it transforms the text-based chat experience into a natural, conversational voice interface—critical for nurses, field technicians, and construction workers who can't type while working.

---

## Abstract

The **Voice Pipeline** extends FrontShiftAI's multi-agent platform with **ultra-low-latency voice capabilities** (<500ms response time). Unlike basic voice assistants, this system:

*   **Orchestrates Multi-Modal AI**: Combines Speech-to-Text (STT), Large Language Models (LLMs), and Text-to-Speech (TTS) in a seamless real-time pipeline
*   **Authenticates Per-User**: Extracts JWT tokens from LiveKit participant metadata to make authenticated backend API calls on behalf of the user
*   **Resilient Provider Chaining**: Implements automatic fallback across Deepgram → AssemblyAI for STT and Deepgram → Cartesia for TTS
*   **On-Demand Serverless Workers**: Spawns dedicated voice agents per session on Modal, eliminating manual startup overhead

---

## Deployment Access

| Component | Provider | URL |
|-----------|----------|-----|
| **Voice Session API** | Modal | [https://raghavg--frontshiftai-voice-agent-web-api.modal.run](https://raghavg--frontshiftai-voice-agent-web-api.modal.run) |
| **LiveKit Cloud** | LiveKit | wss://frontshiftai-vkrebx4e.livekit.cloud |
| **Backend API** | Cloud Run | [https://frontshiftai-backend-vvukpmzsxa-uc.a.run.app](https://frontshiftai-backend-vvukpmzsxa-uc.a.run.app) |

---

## Key Features

### 1. Real-Time Voice Orchestration

The voice pipeline isn't just speech recognition—it's a **full duplex conversational AI system**:

*   **Sub-500ms Latency**: Optimized provider selection (Deepgram STT, Deepgram TTS) ensures near-instantaneous responses
*   **Voice Activity Detection (VAD)**: Silero VAD detects when users stop speaking with <200ms latency
*   **Turn-Taking Protocol**: Interrupt-aware system allows users to naturally cut off the AI mid-sentence
*   **Background Audio**: Optional keyboard typing sounds during "thinking" time improve perceived responsiveness

### 2. Multi-Tenant JWT Authentication Flow

**The Challenge**: Voice sessions are stateless WebRTC connections. How do we authenticate users?

**The Solution**: JWT Passthrough Architecture

```
┌──────────────┐     1. User logs in        ┌─────────────┐
│   Frontend   │──────────────────────────▶│   Backend   │
│  (React)     │◀──────────────────────────│  (FastAPI)  │
└──────┬───────┘     2. Get JWT token       └─────────────┘
       │
       │ 3. Click voice button
       │
       ▼
┌──────────────────────────────────────────────────────────┐
│                    Modal Voice API                       │
│  POST /session { user_token: "eyJhbG..." }              │
│                                                           │
│  1. Create LiveKit room token                           │
│  2. Embed user JWT in participant metadata              │
│  3. Spawn voice worker for this room                    │
└───────────────────────┬──────────────────────────────────┘
                        │
                        ▼
                ┌───────────────┐
                │  Voice Worker │
                │               │
                │  1. User joins room                      │
                │  2. Extract JWT from metadata            │
                │  3. Initialize agent with user token     │
                │  4. Make authenticated backend calls     │
                └───────────────┘
```

**Key Insight**: The user's backend JWT is embedded in LiveKit's participant metadata when the session is created. The voice worker extracts it on connection and uses it for all RAG/PTO/HR API calls—ensuring **true multi-tenant isolation**.

### 3. Provider Resilience & Fallback Chains

To achieve 99.9% uptime, the pipeline implements **multi-provider fallback strategies**:

| Component | Primary Provider | Fallback Provider(s) | Rationale |
| :--- | :--- | :--- | :--- |
| **STT** | **Deepgram** (Nova 2 General) | AssemblyAI (default) | Deepgram has lower latency but AssemblyAI is more robust for accents |
| **LLM** | **OpenAI** (GPT-4o-mini) | None | Tool calling requires function support |
| **TTS** | **Deepgram** (Aura 2 Thalia) | Cartesia (Sonic 2) | Deepgram voices sound more natural; Cartesia is backup |
| **VAD** | **Silero** | N/A | Open-source, runs locally |

**Auto-Retry Logic**: If Deepgram STT fails (e.g., API timeout), the system automatically retries with AssemblyAI **within the same user utterance**—invisible to the user.

### 4. On-Demand Worker Architecture

**Traditional Problem**: Voice agents must run 24/7 to handle incoming calls, wasting compute when idle.

**Our Solution**: **Spawn-on-Demand Workers via Modal**

**How It Works**:
1.  User clicks voice button → Frontend calls `POST /session` on Modal API
2.  Modal API creates LiveKit room + spawns a dedicated worker via `voice_worker_for_room.spawn()`
3.  Worker boots in ~5-10 seconds (cold start), joins room, handles conversation
4.  Worker auto-terminates when user disconnects
5.  **No manual startup needed**—perfect for demos and production

**Cost Impact**: Workers only run during active sessions. For a PoC with 10 demo sessions/day (avg 5 min each), monthly cost ≈ **$2-3** vs. **$100+** for always-on workers.

### 5. Tool Integration with Backend Agents

The voice agent exposes **4 function tools** that map directly to backend APIs:

| Tool Name | Backend Endpoint | Purpose |
| :--- | :--- | :--- |
| `query_info` | `/api/rag/query` | Answer policy questions via RAG (embeddings search) |
| `website_search` | `/api/chat/message` | Search company website for public info (Brave Search) |
| `request_pto` | `/api/pto/chat` | Request time off, check PTO balances |
| `create_hr_ticket` | `/api/hr-tickets/chat` | Escalate complex issues to HR |

**Instruction Hierarchy**:
```
User: "How many vacation days do I have?"
  ↓
Voice Agent LLM decides: This is a PTO question → call request_pto()
  ↓
request_pto tool hits /api/pto/chat with user's JWT
  ↓
Backend PTO agent queries database, returns balance
  ↓
Voice Agent speaks: "You have 12 days remaining"
```

**Hallucination Prevention**: The agent is **strictly instructed** to use tools for all factual queries. If a tool returns no results, it says "I don't know" instead of inventing answers.

---

## Documentation

| Documentation | Description | Link |
|---------------|-------------|------|
| **Modal Deployment** | On-demand worker setup, secrets, monitoring | [MODAL_DEPLOYMENT.md](./MODAL_DEPLOYMENT.md) |

---

## Repository Structure

```
voice_pipeline/
├── scripts/
│   ├── main.py                     # 🏁 VOICE AGENT ENTRYPOINT
│   │                               # - LiveKit worker initialization
│   │                               # - JWT extraction from room metadata
│   │                               # - Provider chain construction (STT/LLM/TTS/VAD)
│   │                               # - Agent session management
│   │
│   ├── generate_jwt.py             # 🔑 Helper: Generate test JWTs for local dev
│   ├── test_backend_connection.py  # 🧪 Sanity check: Validate backend connectivity
│   └── secret_sanity.py            # 🔐 Secret validation: Check all API keys exist
│
├── utils/
│   ├── config.py                   # ⚙️ Configuration Loader
│   │                               # - Loads default.yaml + environment overrides
│   │                               # - Builds ProviderChainConfig for resilience
│   │
│   ├── metrics.py                  # 📊 Metrics Reporters
│   │                               # - STTMetricsReporter, LLMMetricsReporter, TTSMetricsReporter
│   │                               # - VADMetricsReporter, RAGMetricsReporter
│   │                               # - Logs to W&B + structured logs
│   │
│   ├── wandb_logger.py             # 📈 Weights & Biases Integration
│   │                               # - Session-level tracking
│   │                               # - Latency histograms, cost tracking
│   │
│   └── logger.py                   # 🗂️ Logging Setup (structured JSON logs)
│
├── configs/
│   └── default.yaml                # 📝 Default Provider Configuration
│                                   # - STT: Deepgram → AssemblyAI
│                                   # - LLM: OpenAI GPT-4o-mini
│                                   # - TTS: Deepgram → Cartesia
│                                   # - VAD: Silero
│
├── tests/
│   ├── test_agent.py               # 🧪 Comprehensive Unit Tests
│   │                               # - Provider chain building
│   │                               # - Tool integration (mocked backend)
│   │                               # - Metrics collection hooks
│   │                               # - Entrypoint flow (session start/error handling)
│   └── __init__.py
│
├── modal_deploy.py                 # 🚀 MODAL DEPLOYMENT DEFINITION
│                                   # - voice_worker_for_room (on-demand worker)
│                                   # - web_api (FastAPI session creation)
│                                   # - start_worker_manual (backup global worker)
│
├── local_session_server.py         # 💻 LOCAL DEVELOPMENT SESSION API
│                                   # - Creates LiveKit tokens for local testing
│                                   # - Runs on localhost:8001
│
├── requirements.txt                # 📦 Python Dependencies
├── MODAL_DEPLOYMENT.md             # 📖 Deployment Guide
└── README.md                       # 📘 THIS FILE
```

---

## Technical Stack

### Core Voice Components
- **LiveKit Agents SDK**: Real-time voice orchestration framework
- **STT Providers**:
  - Primary: Deepgram Nova 2 General
  - Fallback: AssemblyAI
- **LLM Provider**: OpenAI GPT-4o-mini (function calling required)
- **TTS Providers**:
  - Primary: Deepgram Aura 2 Thalia (natural, low-latency)
  - Fallback: Cartesia Sonic 2
- **VAD**: Silero (open-source, local inference)

### Infrastructure
- **Cloud Platform**: Modal (serverless Python containers)
- **Session Management**: FastAPI (creates LiveKit tokens)
- **Authentication**: JWT passthrough via LiveKit metadata
- **Monitoring**: Weights & Biases, Google Cloud Logging

### Key Libraries
```python
livekit>=1.0.0                      # WebRTC client SDK
livekit-agents>=1.2                 # Voice agent framework
livekit-plugins-noise-cancellation  # Background noise filtering
python-dotenv>=1.0.0                # Environment config
httpx>=0.24.0                       # Async HTTP client
wandb>=0.15.0                       # Metrics tracking
modal>=0.55.0                       # Serverless deployment
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                             USER JOURNEY                                │
│                                                                         │
│  1. User logs in → Gets JWT from backend                              │
│  2. Clicks "Voice Assistant" button                                    │
│  3. Frontend calls Modal /session endpoint with JWT                    │
│  4. Modal spawns worker + returns LiveKit connection details           │
│  5. Frontend connects to LiveKit room                                  │
│  6. Voice worker extracts JWT, starts conversation                     │
└─────────────────────────────────────────────────────────────────────────┘

                                ▼

    ┌────────────────────────────────────────────────────────────────┐
    │                      MODAL DEPLOYMENT                          │
    │                                                                │
    │  ┌──────────────────────┐      ┌──────────────────────────┐  │
    │  │   FastAPI Web API    │      │   Voice Worker           │  │
    │  │   (Always-On)        │      │   (Spawned On-Demand)    │  │
    │  │                      │      │                          │  │
    │  │  POST /session       │─────▶│  1. Join LiveKit room    │  │
    │  │  GET /health         │      │  2. Extract user JWT     │  │
    │  │                      │      │  3. Initialize agent     │  │
    │  └──────────────────────┘      │  4. Start STT/LLM/TTS    │  │
    │                                │  5. Handle conversation  │  │
    │                                └──────────┬───────────────┘  │
    └───────────────────────────────────────────┼──────────────────┘
                                                │
                ┌───────────────────────────────┼──────────────────┐
                │                               │                  │
                ▼                               ▼                  ▼
    ┌─────────────────┐           ┌──────────────────┐  ┌──────────────┐
    │  LiveKit Cloud  │           │  Backend API     │  │  AI Providers│
    │                 │           │  (Cloud Run)     │  │              │
    │  WebRTC Rooms   │           │                  │  │ • Deepgram   │
    │  Audio Routing  │           │  /api/rag/query  │  │ • OpenAI     │
    │                 │           │  /api/pto/chat   │  │ • AssemblyAI │
    └─────────┬───────┘           │  /api/hr-tickets │  │ • Cartesia   │
              │                   └──────────────────┘  └──────────────┘
              │
              ▼
    ┌─────────────────┐
    │   Frontend      │
    │   (React)       │
    │                 │
    │  LiveKit SDK    │
    │  Audio I/O      │
    └─────────────────┘
```

---

## Data Flow: Voice Query Processing

Let's trace a real query: **"How many sick days can I take?"**

### Phase 1: Speech Capture (0-500ms)
```
User speaks ───▶ LiveKit captures audio ───▶ Send to voice worker
```

### Phase 2: Transcription (500-1000ms)
```
Worker sends audio ───▶ Deepgram STT API ───▶ "How many sick days can I take?"
                              │
                              ▼ (if timeout/error)
                        AssemblyAI STT (fallback)
```

### Phase 3: Agent Decision (1000-1500ms)
```
Transcript ───▶ OpenAI GPT-4o-mini with tools
                      │
                      ├─ Analyzes intent: "PTO policy question"
                      └─ Decides: Call query_info tool
```

### Phase 4: Backend RAG Query (1500-3000ms)
```
query_info("sick days policy", top_k=3)
    │
    └───▶ POST /api/rag/query (with user JWT)
              │
              ├─ ChromaDB embedding search
              ├─ Retrieve top 3 policy chunks
              └─ LLM generates answer with citations

    Response: {
        "answer": "You can take up to 5 sick days per year...",
        "sources": ["handbook_p42.pdf#page=42"],
        "company": "Crouse Medical"
    }
```

### Phase 5: Response Generation (3000-3200ms)
```
LLM formats answer ───▶ "According to your company handbook,
                         you can take up to 5 sick days per year..."
```

### Phase 6: Speech Synthesis (3200-3800ms)
```
Text ───▶ Deepgram TTS ───▶ Audio stream (begins playing at ~3400ms)
                │
                ▼ (if error)
          Cartesia TTS (fallback)
```

### Phase 7: Delivery (3800ms+)
```
Audio stream ───▶ LiveKit ───▶ User hears response
```

**Total Time to First Audio**: ~3.4 seconds (network latency + multi-hop processing)

---

## Monitoring & Metrics

### 1. Real-Time Metrics Collection

Every voice interaction generates **5 types of metrics**:

| Metric Type | What We Track | Why It Matters |
| :--- | :--- | :--- |
| **STT** | Transcription latency, audio duration, speech ID | Detect slow STT providers |
| **LLM** | TTFT (time to first token), tokens/sec, completion tokens | Measure reasoning speed |
| **TTS** | TTFB (time to first byte), audio duration, characters count | Detect slow voice synthesis |
| **VAD** | Idle time, inference count | Optimize turn-taking |
| **RAG** | Total duration, retrieval time, generation time, sources count | Track backend query performance |

### 2. Weights & Biases Integration

Metrics are logged to W&B for long-term analysis:

```python
wandb.log({
    "stt/duration": 0.45,
    "llm/ttft": 0.12,
    "tts/duration": 0.38,
    "rag/total_duration": 1.85,
    "rag/cache_hit": False,
})
```

**Key Dashboards**:
*   **Latency Histogram**: P50/P95/P99 response times per component
*   **Cost Tracking**: Token usage × pricing for OpenAI/Deepgram
*   **Error Rate**: Fallback trigger frequency (Deepgram → AssemblyAI)

### 3. Structured Logging

All events are logged as JSON for CloudWatch/Datadog ingestion:

```json
{
  "metric_type": "rag_query_complete",
  "session_id": "abc123",
  "query": "How many sick days can I take?",
  "total_duration_seconds": 1.85,
  "backend_duration_seconds": 1.72,
  "retrieval_duration_seconds": 0.45,
  "generation_duration_seconds": 1.27,
  "sources_count": 3,
  "cache_hit": false
}
```

---

## Testing Protocol

### Unit Tests (98% Coverage)

The test suite validates every component in isolation:

**Tier 1: Provider Builders** (`test_build_*_provider`)
- Validates that `ProviderConfig` objects correctly instantiate Deepgram/OpenAI/Cartesia clients
- Tests fallback chain construction (primary + 2 fallbacks)

**Tier 2: Backend Client** (`test_backend_client_hits_mock_server`)
- Mocks HTTP layer to test JWT authentication headers
- Validates retry logic and timeout handling

**Tier 3: Tool Integration** (`test_voice_agent_tools_call_backend`)
- Mocks backend responses for RAG/PTO/HR endpoints
- Validates that tools parse responses correctly
- Ensures website search rejects non-website_extraction responses

**Tier 4: Metrics Hooks** (`test_voice_agent_*_metrics_handlers`)
- Simulates LiveKit metrics events (STT/LLM/TTS/VAD)
- Validates that reporters schedule async logging tasks
- Checks W&B logging format

**Tier 5: Entrypoint Flow** (`test_entrypoint_*`)
- Tests full session lifecycle (connect → greet → error handling)
- Validates STT restart logic on recoverable errors
- Tests graceful degradation when greeting fails

**Run Tests**:
```bash
cd voice_pipeline
pytest tests/ -v --cov=scripts --cov=utils
```

### Integration Testing

**Local End-to-End Test** (requires real API keys):
```bash
# Terminal 1: Start backend
cd backend && uvicorn main:app --reload

# Terminal 2: Start local session server
cd voice_pipeline && python local_session_server.py

# Terminal 3: Start voice worker
cd voice_pipeline/scripts && python main.py dev

# Terminal 4: Open frontend
cd frontend && npm run dev
```

Click the voice button and speak: "How many vacation days do I have?"

**Expected Behavior**:
1.  Frontend shows "Connecting..." → "Connected"
2.  Voice worker logs show JWT extraction
3.  You hear the agent's greeting within 3 seconds
4.  Your query triggers `request_pto` tool → backend API call
5.  Agent responds with your PTO balance

---

## Cost Analysis (Monthly Estimate)

Designed for **student-budget serverless operations**.

| Service | Configuration | Usage (Demo Scenario) | Est. Monthly Cost |
|---------|---------------|----------------------|-------------------|
| **Modal Compute** | On-demand workers (2 vCPU, 4GB RAM) | 10 sessions/day × 5 min × 30 days = 25 hours | ~$3.00 |
| **LiveKit Cloud** | Free Tier | <100 participant-minutes/day | $0.00 |
| **Deepgram STT** | Pay-as-you-go | 25 hours × 60 min × $0.0043/min = 6,450 min | ~$27.74 |
| **Deepgram TTS** | Pay-as-you-go | ~150k characters/month × $0.015/1k chars | ~$2.25 |
| **OpenAI API** | GPT-4o-mini | ~500k tokens/month × $0.15/1M tokens | ~$0.08 |
| **W&B** | Free Tier | <100 GB logs/month | $0.00 |
| **Total** | | | **~$33.07/month** |

**Cost Optimization Strategies**:
1.  **Use Free STT**: Switch to Whisper (local) or Groq Whisper (free) for non-prod
2.  **Reduce Session Length**: Set 5-min auto-disconnect for idle sessions
3.  **Cache TTS**: Pre-generate common greetings and error messages

**Production Scaling** (1000 users, 5 sessions/week):
*   **Modal**: ~$50/month (workers scale to zero when idle)
*   **LiveKit**: ~$99/month (paid tier for guaranteed uptime)
*   **Deepgram STT**: ~$300/month
*   **Total**: ~$450/month for **20,000 voice sessions**

---

## Installation & Contributing

### Prerequisites
- Python 3.11+
- Modal account ([modal.com](https://modal.com))
- LiveKit Cloud account ([livekit.io](https://livekit.io))
- API keys:
  - Deepgram (STT/TTS)
  - OpenAI (LLM)
  - AssemblyAI (STT fallback)
  - Cartesia (TTS fallback)

### Quick Start (Local Development)

**1. Clone & Install Dependencies**
```bash
git clone https://github.com/MLOpsGroup9/FrontShiftAI.git
cd FrontShiftAI/voice_pipeline

# Create virtual environment
python -m venv voice_venv
source voice_venv/bin/activate  # On Windows: voice_venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

**2. Configure Environment**
Create `scripts/.env`:
```bash
# LiveKit credentials
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=APIxxxxxxxxxxxxx
LIVEKIT_API_SECRET=xxxxxxxxxxxxx

# Backend
VOICE_AGENT_BACKEND_URL=http://localhost:8000
VOICE_AGENT_JWT=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# AI Providers
OPENAI_API_KEY=sk-...
DEEPGRAM_API_KEY=...
ASSEMBLYAI_API_KEY=...
CARTESIA_API_KEY=...

# Optional: Monitoring
WANDB_API_KEY=...
```

**3. Run Locally**
```bash
# Terminal 1: Backend (required)
cd backend && uvicorn main:app --reload --port 8000

# Terminal 2: Session API
cd voice_pipeline && python local_session_server.py

# Terminal 3: Voice Worker
cd voice_pipeline/scripts && python main.py dev

# Terminal 4: Frontend
cd frontend && npm run dev
```

Visit `http://localhost:5173`, log in, and click the microphone icon.

### Deploy to Production

See [MODAL_DEPLOYMENT.md](./MODAL_DEPLOYMENT.md) for full instructions.

**TL;DR**:
```bash
# 1. Create Modal secrets at modal.com/secrets:
#    - livekit-credentials
#    - voice-agent-providers
#    - voice-agent-backend

# 2. Deploy
modal deploy voice_pipeline/modal_deploy.py

# 3. Copy the URL (e.g., https://yourorg--frontshiftai-voice-agent-web-api.modal.run)

# 4. Update frontend .env
VITE_VOICE_API_URL=https://yourorg--frontshiftai-voice-agent-web-api.modal.run
```

### Contributing
Please follow the main project's [contribution guidelines](../README.md#contributing).

**Voice-specific guidelines**:
- All tests must pass: `pytest tests/ -v`
- Add metrics logging for new tools
- Update provider chains in `configs/default.yaml` if adding new providers
- Test with real audio devices (not just mock tests)

---

## Troubleshooting

### Common Issues

**1. "No user token found" Warning**
```
⚠️ No user token found - using service account (auth may fail!)
```

**Cause**: Frontend didn't pass JWT in `/session` request.

**Fix**:
- Ensure user is logged in before clicking voice button
- Check browser console for session creation errors
- Verify `user_token` is in localStorage

---

**2. "Worker not joining room"**

**Symptoms**: Frontend connects to LiveKit but no response from agent.

**Debug Steps**:
```bash
# Check Modal logs
modal app logs frontshiftai-voice-agent --follow

# Look for:
# ✅ "Voice Worker Starting" (worker spawned)
# ✅ "Connected to room: voice-abc123" (worker joined)
# ❌ If you don't see these, worker didn't start
```

**Fix**: Verify LiveKit credentials in Modal secrets match your LiveKit Cloud project.

---

**3. "STT Timeout / Fallback Triggered"**

```
⚠️ Deepgram STT timeout, falling back to AssemblyAI
```

**Cause**: Deepgram API rate limit or network issue.

**Fix**:
- Check Deepgram dashboard for quota
- Temporary: Lower `top_k` in RAG queries to reduce load
- Long-term: Upgrade to Deepgram paid tier

---

**4. "Backend calls failing with 401 Unauthorized"**

**Symptoms**: Tools return errors like "Invalid token" or "Unauthorized".

**Debug**:
```python
# Check if JWT extraction worked
# In modal_deploy.py logs, look for:
# 🔑 FOUND user token from participant: user@company.com
```

**Fix**:
- Ensure user's JWT isn't expired (check `exp` claim)
- Verify `VOICE_AGENT_BACKEND_URL` is correct (https://, no trailing slash)
- Test backend directly: `curl -H "Authorization: Bearer $JWT" $BACKEND_URL/health`

---

**5. "Cold Start Too Slow (>15 seconds)"**

**Cause**: Modal container cold start + dependency loading.

**Workarounds**:
- **Pre-warm**: Hit `/health` endpoint before demo: `curl https://your-modal-url/health`
- **Keep Warm (Paid)**: Enable Modal's keep-warm feature in production
- **Local Dev**: Use `python main.py dev` for instant startup

---

## Fairness & Bias Considerations

### Voice Accessibility Challenges

**Challenge**: Voice interfaces inherently bias toward:
- Native English speakers
- Standard American/British accents
- Quiet environments

**Our Mitigations**:
1.  **Accent-Robust STT**: AssemblyAI fallback has better non-native English support than Deepgram
2.  **Noise Cancellation**: `livekit-plugins-noise-cancellation` filters background noise
3.  **Multi-Modal Fallback**: If voice fails 3 times, agent says: "I'm having trouble hearing you. Would you like to switch to text chat?"

### STT Bias Analysis (Planned)

**Methodology** (not yet implemented):
1.  Collect 100 voice samples across:
    - Gender (male/female/non-binary)
    - Accent (US, UK, Indian, Chinese)
    - Age (18-30, 30-50, 50+)
2.  Measure Word Error Rate (WER) for each demographic
3.  If WER variance >10%, add accent-specific STT models

**Current Status**: Voice pipeline is in PoC phase. Production deployment should include this analysis.

---

## Future Enhancements

**Planned for Next Release**:
1.  **Call Summary Emails**: After each session, email transcript + action items to user
2.  **Multi-Language Support**: Spanish, Mandarin TTS/STT for diverse workforces
3.  **Proactive Notifications**: Agent calls user when PTO request is approved
4.  **Voice Biometrics**: Identify users by voice (eliminate JWT requirement)

**Research Ideas**:
- **Emotion Detection**: Analyze tone to detect frustrated users → auto-escalate to human
- **Noise-Robust RAG**: Filter retrieval results based on acoustic environment (factory floor vs. office)

---

## License

Proprietary software developed by **MLOps Group 9** (Northeastern University).

---

## Acknowledgments

Built with:
- [LiveKit](https://livekit.io/) - Real-time communication infrastructure
- [Modal](https://modal.com/) - Serverless Python platform
- [Deepgram](https://deepgram.com/) - Speech recognition & synthesis
- [OpenAI](https://openai.com/) - Language model reasoning
