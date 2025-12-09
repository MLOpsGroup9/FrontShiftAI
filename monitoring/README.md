# Monitoring & Observability (The "Control Tower")

Just like an airport control tower needs to know if a plane is delayed or off-course, **FrontShiftAI** needs to know if the AI is hallucinating or if the server is slow.

We use two primary tools:

## 1. Google Cloud Monitoring (Infrastructure)
*   **What it tracks**: CPU usage, Memory, Latency (how fast the API responds).
*   **Alerts**: If the API takes > 3 seconds to answer, or if 500 errors spike, our team gets an email instantly.

## 2. Weights & Biases (AI Quality)
*   **What it tracks**: Every single conversation.
*   **Metrics**:
    *   **Groundedness**: Did the AI answer based on the handbook?
    *   **Answer Correctness**: Was the answer accurate?
    *   **User Feedback**: Did the user say "Thanks" or "This is wrong"?

## 🛠️ Setup

### Middleware
The backend includes a custom middleware (`monitoring/middleware.py`) that automatically logs every request to these services.

### Accessing Dashboards
*   **Infrastructure**: Go to [Google Cloud Console > Monitoring](https://console.cloud.google.com/monitoring)
*   **AI Traces**: Go to [WandB Project](https://wandb.ai/) and select the `FrontShiftAI` project.
