# FrontShiftAI: AI Concierge for Deskless Workers

![Python](https://img.shields.io/badge/Python-3.12+-blue) ![React](https://img.shields.io/badge/React-18.2-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green) ![Docker](https://img.shields.io/badge/Docker-Enabled-blue) ![Status](https://img.shields.io/badge/Status-Active-brightgreen)

**Team Members**: Harshitkumar Brahmbhatt, Krishna Venkatesh, Raghav Gali, Rishi Raj Kuleri, Sujitha Godishala, Swathi Baba Eswarappa

---

## 📖 About The Project

**FrontShiftAI** is an intelligent, multi-agent AI assistant designed specifically for the "deskless" workforce—nurses, construction foremen, retail managers, and field technicians. These workers don't have easy access to HR portals or complex documentation systems while on the job.

FrontShiftAI bridges this gap by acting as a **24/7 HR & Operations Concierge**. It ingests thousands of pages of PDF handbooks, understands company policies, and provides instant, accurate answers via a chat interface. Beyond just answering questions, it can actively perform tasks like checking PTO balances, filing leave requests, and opening HR support tickets.

### 🌐 Live Demo & Deployment
- **Frontend Application (Vercel)**: [Access App Here](https://frontshift-ai.vercel.app/) *(URL inferred from context, please verifying if different)*
- **Backend API (Google Cloud Run)**: `https://frontshiftai-backend-vvukpmzsxa-uc.a.run.app`
- **Voice Agent API**: `https://ragavgsm21--frontshiftai-voice-agent-web-api.modal.run`

---

## 🚀 Key Features

### 🧠 1. Multi-Agent Intelligence
The system isn't just a chatbot; it's a squad of specialized agents coordinated by a central brain:
*   **Unified Router**: Automatically understands if a user is asking a policy question, requesting time off, or reporting a grievance and routes it to the right expert.
*   **RAG Agent (The Librarian)**: Uses advanced Retrieval-Augmented Generation to search company PDFs. It cites its sources (page numbers and links) so users can trust the answer.
*   **PTO Agent (The HR Assistant)**: A transactional agent that can:
    *   Check live leave balances.
    *   Understand natural language requests ("I need next Friday off").
    *   Validate requests against holidays and blackout dates.
    *   Book the time off in the database.
*   **HR Ticket Agent (The Support Rep)**: Handles complex inquiries that require human intervention. It categorizes issues (Payroll, Benefits, etc.), assigns priority, and schedules meetings.
*   **Website Extraction Agent (The Researcher)**: If the handbook doesn't have the answer (e.g., "What are the office hours?"), it automatically searches the company's public website for real-time info.

#### 🧠 1.1 LLM Architecture & Resiliency
To ensure 99.9% uptime and low latency, we employ a robust fallback strategy across different model providers:

| Component | Main LLM | Backup Chain (in order) |
| :--- | :--- | :--- |
| **LLM Decider** (Routing) | **Groq** <br>*(Llama 3.1 8B Instant)* | 1. **Mercury** <br>2. **OpenAI** *(GPT-4o-mini)* <br>3. **Local** *(Ollama/Llama 3)* |
| **Agentic Flow** (PTO/HR) | **Groq** <br>*(Llama 3.1 8B Instant)* | 1. **Mercury** <br>2. **OpenAI** *(GPT-4o-mini)* <br>3. **Local** *(Ollama/Llama 3)* |
| **RAG Model** (Generator) | **Mercury** <br>*(Custom Model)* | 1. **Groq** <br>2. **OpenAI** *(GPT-4o-mini)* <br>3. **Local** *(Llama 3.2 3B GGUF)* |

### 🏢 2. Multi-Tenant Architecture
*   **One System, Many Companies**: A single deployment serves multiple organizations (Crouse Medical, TechCorp, RetailCo).
*   **Data Isolation**: Each company's data (documents, users, tickets) is strictly segregated.
*   **Dynamic Branding**: The UI adapts to the user's company context.

### 🛠️ 3. Super Admin & Company Management
*   **Self-Service Onboarding**: Super Admins can add new companies instantly.
    *   *Input*: Company Name, Domain, Handbook PDF URL.
    *   *Automation*: The system automatically downloads the PDF, runs OCR, chunks the text, generates embeddings, and rebuilds the vector index—all in the background.
    *   *Consistency*: The new index is synced to Google Cloud Storage (GCS) so all API instances update automatically.
*   **Bulk Management**: Tools to bulk-delete users or remove entire companies cleanly.

### 📊 4. Enterprise-Grade Operations
*   **Model Registry**: We version-control our AI "brains". We can rollout v2 and rollback to v1 instantly if issues arise.
*   **Monitoring**: Real-time dashboards (Weights & Biases) track token usage, latency, and user feedback (thumbs up/down).
*   **CI/CD**: Automated GitHub Actions for testing backend/frontend and retraining RAG models.

---

## 📂 Repository Structure

The codebase is organized into modular microservices for scalability and maintainability.

```text
FrontShiftAI/
├── backend/                  # FastAPI Application (The "Brain")
│   ├── agents/               # LangGraph workflow definitions for PTO, HR, RAG
│   ├── api/                  # REST API endpoints (Auth, Chat, Admin)
│   ├── db/                   # Database models and connection logic
│   ├── jobs/                 # Celery background tasks (Ingestion, Rebuilds)
│   ├── services/             # Core logic (Auth Service, RAG Service)
│   ├── main.py               # Application entry point
│   └── requirements.txt      # Python dependencies
│
├── frontend/                 # React Application (The "Face")
│   ├── src/
│   │   ├── components/       # Reusable UI components (ChatArea, Sidebar)
│   │   ├── services/         # API client integration
│   │   └── App.jsx           # Main routing logic
│   ├── package.json          # Node dependencies and scripts
│   └── vite.config.js        # Build configuration
│
├── data_pipeline/            # Data Engineering (The "Factory")
│   ├── scripts/              # Python scripts for PDF ingestion and embedding
│   ├── data/                 # Local storage for vector DB (synced to GCS)
│   └── Dockerfile            # Container for running data jobs
│
├── chat_pipeline/            # AI Research & Eval (The "Lab")
│   ├── rag/                  # RAG logic (retriever, reranker, generator)
│   ├── evaluation/           # Scripts to test answer quality (DeepEval)
│   └── configs/              # YAML configs for experiments
│
├── .github/workflows/        # CI/CD Automation
│   ├── deploy-vercel.yml     # Frontend deployment
│   ├── retrain_rag.yml       # Manual trigger to rebuild RAG index
│   └── backend.yml           # Backend testing
│
└── docker-compose.yml        # Local development orchestration
```

---

## 🛠️ Getting Started

### Prerequisites
*   Python 3.10+
*   Node.js 18+
*   Docker (optional, for Redis/Celery)

### 1. Backend Setup
The backend powers the API and AI agents.

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# (Populate .env with your OpenAI/Groq/DB credentials)

# Run the server
python main.py
```
*API will be available at `http://localhost:8000`*

### 2. Frontend Setup
The modern React UI.

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```
*App will be available at `http://localhost:5173`*

### 3. Data Pipeline (RAG Ingestion)
To ingest a new company handbook locally:

```bash
# Ensure you are provided the OpenAI/Embedding keys
cd data_pipeline

# Run the ingestion script
python scripts/pipeline_runner.py
```

### 4. Running Tests
We maintain high code quality with comprehensive test suites.

```bash
# Backend Tests
pytest backend/tests

# Agent Logic Tests
pytest backend/agents/test_agents
```

---

## 💻 Tech Stack

| Component | Technologies |
| :--- | :--- |
| **Backend** | Python, FastAPI, SQLAlchemy, Pydantic, Celery, Redis |
| **Frontend** | React, Vite, TailwindCSS, Framer Motion, Axios |
| **AI/ML** | LangChain, LangGraph, ChromaDB, HuggingFace, OpenAI, Groq, Llama |
| **DevOps** | Docker, Google Cloud Run, Google Cloud Storage, GitHub Actions, Vercel |
| **Monitoring** | Weights & Biases (W&B), DeepEval |

---

## 📜 License
MIT License. Created by MLOpsGroup9 (Northeastern University).
