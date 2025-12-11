# Modal Deployment Guide - FrontShiftAI Voice Agent

Deploy the voice agent on Modal with **on-demand workers** - no manual startup needed!

## Architecture

```
┌─────────────────┐     ┌────────────────────────────────────────────────────┐
│                 │     │                      Modal                          │
│    Frontend     │     │  ┌─────────────────┐    ┌──────────────────────┐   │
│   (Vercel)      │────▶│  │   Web API       │───▶│   Voice Worker       │   │
│                 │     │  │  POST /session  │    │   (spawned on-demand)│   │
│  Click Voice 🎙️ │     │  └─────────────────┘    └──────────┬───────────┘   │
└────────┬────────┘     └────────────────────────────────────────────────────┘
         │                                                   │
         │              ┌─────────────────┐                  │
         └─────────────▶│   LiveKit       │◀─────────────────┘
                        │   Cloud         │
                        └─────────────────┘
                                 │
                        ┌────────▼────────┐
                        │   Backend API   │
                        │  (Cloud Run)    │
                        └─────────────────┘
```

**Key Feature**: When user clicks the voice button, the `/session` endpoint automatically spawns a worker. No need to run `modal run` before demos!

## Quick Start

### 1. Create Modal Secrets

Go to https://modal.com/secrets and create:

**`livekit-credentials`**
```
LIVEKIT_URL=wss://your-livekit.livekit.cloud
LIVEKIT_API_KEY=<your-api-key>
LIVEKIT_API_SECRET=<your-api-secret>
```

**`voice-agent-providers`**
```
OPENAI_API_KEY=<your-openai-key>
DEEPGRAM_API_KEY=<your-deepgram-key>
ASSEMBLYAI_API_KEY=<your-assemblyai-key>
CARTESIA_API_KEY=<your-cartesia-key>
```

**`voice-agent-backend`**
```
VOICE_AGENT_BACKEND_URL=https://your-backend.run.app
VOICE_AGENT_JWT=<fallback-service-account-jwt>
```

### 2. Deploy

```bash
modal deploy voice_pipeline/modal_deploy.py
```

Copy the URL it gives you (e.g., `https://your-org--frontshiftai-voice-agent-web-api.modal.run`)

### 3. Update Frontend

Edit `frontend/.env`:
```bash
VITE_VOICE_API_URL=https://your-org--frontshiftai-voice-agent-web-api.modal.run
```

### 4. Done! 🎉

Click the voice button in your app - it just works!

## How It Works

1. **User clicks voice button** → Frontend calls `POST /session` with user's JWT
2. **Modal API** creates LiveKit room + embeds JWT in metadata
3. **Modal API** calls `voice_worker_for_room.spawn(room_name, session_id)`
4. **Worker spins up** (~5-10 seconds cold start, faster when warm)
5. **Worker joins room** and starts listening
6. **User speaks** → Voice agent responds using their JWT for backend calls
7. **User disconnects** → Worker terminates

## API Endpoints

### `POST /session`
Create session and spawn worker.

**Request:**
```json
{
  "user_email": "user@company.com",
  "company": "Acme Corp",
  "user_token": "eyJhbG..."
}
```

**Response:**
```json
{
  "session_id": "abc123",
  "room_name": "voice-abc123",
  "token": "eyJhbG...",
  "livekit_url": "wss://...",
  "worker_status": "spawning"
}
```

### `GET /health`
Check service health and provider configuration.

### `GET /health/deep`
Test connectivity to LiveKit and backend.

## Cold Start Optimization

First request after deploy may take 10-15 seconds (cold start). To warm up:

```bash
# Hit the health endpoint to warm the container
curl https://your-modal-url/health
```

Or use Modal's keep-warm feature for production.

## Backup: Manual Worker

If on-demand spawning has issues, run a persistent worker:

```bash
modal run voice_pipeline/modal_deploy.py::start_worker_manual
```

This worker listens for ALL rooms and handles them. Keep it running in a terminal during your demo.

## Local Development

Test locally without Modal:

**Terminal 1 - Backend:**
```bash
cd backend && uvicorn main:app --reload
```

**Terminal 2 - Session Server:**
```bash
cd voice_pipeline && python local_session_server.py
```

**Terminal 3 - Voice Agent:**
```bash
cd voice_pipeline/scripts && python main.py dev
```

**Terminal 4 - Frontend:**
```bash
cd frontend && npm run dev
```

## Troubleshooting

### "Worker not joining room"
- Check Modal logs: `modal app logs frontshiftai-voice-agent`
- Verify LiveKit credentials in Modal secrets
- Try manual worker mode as backup

### "User token required" error
- Frontend must pass JWT from localStorage
- Check user is logged in

### "Cold start too slow"
- Hit `/health` endpoint to warm up before demo
- Consider Modal's keep-warm for production

### "Backend calls failing"
- Check `VOICE_AGENT_BACKEND_URL` in Modal secrets
- Verify backend is accessible from Modal (public URL)

## Monitoring

```bash
# View logs
modal app logs frontshiftai-voice-agent

# Follow logs in real-time
modal app logs frontshiftai-voice-agent --follow

# List running functions
modal app list
```

## Cost

- **CPU**: 2 vCPUs per worker
- **Memory**: 4GB per worker
- **Billing**: Only when workers are running
- **On-demand**: Workers terminate after session ends

For PoC/demos, costs are minimal since workers only run during active sessions.
