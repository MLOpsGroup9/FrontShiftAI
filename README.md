![Python](https://img.shields.io/badge/Python-3.12+-blue)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)
![Documentation](https://img.shields.io/badge/Docs-Comprehensive-blueviolet)

# FrontShiftAI: The AI Copilot for Deskless Workers

**Team Members**: Harshitkumar Brahmbhatt, Krishna Venkatesh, Raghav Gali, Rishi Raj Kuleri, Sujitha Godishala, Swathi Baba Eswarappa

---

## 📖 What is FrontShiftAI?
**(In Simple Terms)**

Imagine a **"Deskless" Worker**—a nurse, a construction foreman, or a retail store manager. They don't sit at a computer all day. When they have a question like *"How do I request time off?"* or *"What is the safety protocol for this machine?"*, they can't easily search through a 50-page PDF handbook on a slow HR portal.

**FrontShiftAI** is an intelligent assistant that lives on their phone or tablet. It acts like a **24/7 HR & Operations Concierge**:
1.  **It Reads Everything**: We feed it all the company's PDF handbooks and policies.
2.  **It Understands Questions**: Additionaly, it speaks plain English (e.g., "I need a sick day tomorrow").
3.  **It Takes Action**: It doesn't just answer; it can actually *log* the request or *file* a ticket for them.

---

## 🏗️ How It Works (The "Secret Sauce")

We built a system that combines **Brain Power (LLMs)** with **Reliable Data (RAG)**.

### 1. The "Librarian" (Data Pipeline)
*   **What it does**: Reads thousands of PDF pages, organizes them, and indexes them so they are searchable.
*   **Tech**: Python, OCR (for reading scanned docs), ChromaDB (Vector Database).

### 2. The "Brain" (Chat Pipeline)
*   **What it does**: When a user asks a question, this part searches the "Library", finds the exact page, and then uses an advanced AI (like GPT-4 or Llama) to write a polite, accurate answer.
*   **Safety**: It never guesses. If the answer isn't in the handbook, it says "I don't know" or looks up the company website for public info (like office hours).
*   **Tech**: OpenAI / Llama Models, RAG (Retrieval-Augmented Generation), Mercury API.

### 3. The "Concierge" (Backend & Agents)
*   **What it does**: Handling complex tasks.
    *   *User*: "I want vacation next week."
    *   *Concierge*: "Checking your balance... You have 5 days left. Shall I book it?"
*   **Tech**: FastAPI, LangGraph (for multi-step reasoning), SQL Database.

---

## 📂 Project Structure
(Where to find things in this repo)

| Folder | Purpose |
| :--- | :--- |
| **`backend/`** | **The Core Service**. Runs the API, manages the database, and hosts the "Agents" (PTO, HR Ticket). |
| **`chat_pipeline/`** | **The AI Logic**. Handles the "thinking"—retrieving documents, evaluating answers, and tracking model quality. |
| **`data_pipeline/`** | **The Data Factory**. Downloads PDFs, cleans extracting text, and saves them into the efficient Vector Database. |
| **`frontend/`** | **The User Interface**. The React website where users actually chat with the bot. |
| **`.github/workflows/`** | **Automation**. Scripts that automatically test the code and deploy it to the cloud whenever we make changes. |

---

## 🚀 Key Features

### ✅ 1. Retrieval-Augmented Generation (RAG)
We don't just "ask ChatGPT". We explicitly provide the company's *own* handbook as context. This makes the answers **100% grounded in company policy**, reducing wrong answers ("hallucinations").

### ✅ 2. Intelligent Fallback
If the handbook doesn't have the answer, our **Unified Agent** is smart enough to:
*   **Search the Web**: If you ask "What are the office hours?", it checks the company's public website.
*   **Open a Ticket**: If you ask for help, it offers to connect you with a human HR rep.

### ✅ 3. Smart Actions (Agents)
*   **PTO Agent**: Can check balances and book time off.
*   **Ticket Agent**: Can categorize and file support requests.

### ✅ 4. Enterprise-Grade Ops
*   **Model Registry**: We track every version of our AI. If "v2" acts weird, we can instantly "Rollback" to "v1".
*   **Monitoring**: We use dashboards (Weights & Biases, Google Cloud) to watch for errors or slow responses in real-time.

---

## 🛠️ Getting Started (For Developers)

Want to run this locally?

### Prerequisites
*   Python 3.12+
*   Docker (recommended for Data Pipeline)

### Quick Start
1.  **Clone the Repo**:
    ```bash
    git clone https://github.com/MLOpsGroup9/FrontShiftAI.git
    cd FrontShiftAI
    ```

2.  **Run the Backend**:
    ```bash
    cd backend
    pip install -r requirements.txt
    python main.py
    ```
    *API will run at `http://localhost:8000`*

3.  **Run the Data Pipeline**:
    *See `data_pipeline/README.md` for the full Docker setup.*

4.  **Run the Chat Evaluation**:
    *See `chat_pipeline/README.md` to run the "Quality Gate" tests.*

---

## 📜 License
MIT License. Created by the MLOpsGroup9 Team at Northeastern University.
