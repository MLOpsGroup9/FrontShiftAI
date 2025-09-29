# MDesklessAI - AI Copilot for Deskless Workers


# AI Copilot for Deskless Workers 

**Team Members**  
- Harshitkumar Brahmbhatt  
- Krishna Venkatesh  
- Raghav Gali  
- Rishi Raj Kuleri  
- Sujitha Godishala  
- Swathi Baba Eswarappa  

---

## 1. Introduction

Despite making up **70–80% of the workforce**, deskless workers remain underserved by traditional HR and knowledge systems due to structural and communication barriers:

- Limited computer access during work hours (62%)  
- Irregular schedules (56%)  
- Lack of face-to-face communication (55%)  

These gaps result in **low benefits enrollment**, **weak training adoption**, **reduced engagement**, and **higher attrition**.  

### Proposed Solution  
We propose an **AI Copilot** powered by **Retrieval-Augmented Generation (RAG)** with an **agentic orchestration layer**:

- **RAG foundation** → Retrieves policy/training content from handbooks, LMS, HR portals.  
- **Agentic layer** → Executes follow-up tasks (schedule training, check compliance, escalate to HR).  
- **Voice interaction (future work)** → Accessibility in hands-busy, on-the-move environments.  

---

## 2. Dataset Information

### Dataset Introduction
A **Deskless Worker Handbook Q&A Dataset** generated from diverse employee handbooks across industries.

- Purpose: Make HR/policy content accessible via natural queries.  
- Scope: 200–20,000 Q&A pairs (manual + synthetic).  

### Data Card

| Attribute      | Description |
|----------------|-------------|
| **Name**       | Deskless Worker Handbook Q&A Dataset |
| **Sources**    | Employee handbooks (healthcare, retail, logistics, hospitality, finance, etc.) |
| **Formats**    | CSV (exploration), JSONL (fine-tuning), PDF/TXT (retrieval) |
| **Types**      | Q&A pairs, metadata (industry, policy type, source) |

### Example Sources
- Healthcare: *Crouse Medical Handbook (2019)*  
- Cleaning & Maintenance: *CleanSpace Handbook (2024)*  
- Retail: *Lunds & Byerlys Handbook (2019)*  
- Hospitality: *Alta Peruvian Lodge Handbook (2016)*  
- Finance: *Old National Bank Handbook*  
- Automobile: *Lowe Auto Handbook (2023)*  

### Rights & Privacy
- All handbooks are **publicly available PDFs**.  
- **No personal/employee-identifiable data**.  
- Dataset used **strictly for research/educational purposes**.  

---

## 3. Data Planning and Splits

### Preprocessing
1. **Extract text** from PDFs (PyMuPDF, PDFMiner).  
2. **Clean/normalize** (remove headers, footers, duplicates).  
3. **Chunk** into policy sections.  
4. **Generate Q&A pairs** (manual + synthetic).  
5. **Normalize format** (JSONL schema).  

### Splitting Strategy
- **Train (70%)**: Main Q&A set.  
- **Validation (15%)**: Hyperparameter tuning.  
- **Test (15%)**: Final evaluation.  
- Stratified by industry.  
- Deduplication to avoid leakage.  

---

## 4. Problems & Limitations of Current Solutions

- **HCM Suites (Workday, SAP)** → Vendor-locked, admin-focused.  
- **Digital Assistants (Oracle DA)** → Rigid, schema-bound.  
- **LMS (Docebo, Cornerstone)** → Static, no real-time retrieval.  
- **Generic Chatbots (Leena AI, Talla)** → FAQ-only, no policy grounding.  
- **Self-Service Portals** → Desktop-centric, no natural query support.  
- **Internal Comms (Slack, Teams)** → Transient, not retrievable.  

---

## 5. Proposed Solution

### Core Features
1. **RAG: Grounded Q&A** → Accurate answers with citations.  
2. **Agentic Layer** → Orchestrates actions (schedule training, escalate to HR).  
3. **Personalization & Memory** → Contextual follow-ups, history-aware.  
4. **System Integration** → Connect to LMS, HRIS, calendars, docs.  
5. **Voice Interaction** → STT/TTS for hands-free environments.  
6. **Safe Fallbacks** → Escalate to HR if confidence is low.  

---

## 6. Current Flow & Bottlenecks

Traditional HR workflow →  

- **HR Overload** (all queries bottlenecked).  
- **Fragmented Systems** (LMS, HRIS, docs are siloed).  
- **Limited Worker Access** (no real-time retrieval).  

Results: delays, policy confusion, missed deadlines, disengagement.  

---

## 7. Metrics, Objectives, and Business Goals

### Objectives
- Build **RAG-based copilot** for grounded policy Q&A.  
- Enable **agentic action execution**.  
- Provide **voice-enabled conversational access**.  
- Ensure **compliance, auditability, and safe fallback**.  

### Business Alignment
| Goal | Support |
|------|----------|
| HR efficiency | Automates queries, reduces HR workload. |
| Training compliance | Timely scheduling/reminders. |
| Employee engagement | Conversational, mobile-first interface. |
| Risk reduction | Grounded answers, audit logs. |
| Scalability | AI handles query growth without HR scaling. |

---

## 8. Key Metrics

### RAG
- Recall@5 > 90%  
- Factuality/Citation Match > 85%  
- EM > 70%  
- F1 > 80%  
- ROUGE-L > 0.6  
- Hallucination Rate < 5%  
- User Helpfulness Rating > 4/5  

### Agentic Layer
- Tool Accuracy > 90%  
- Task Success > 85%  
- Safe Fallback > 95%  
- Completion Time < 5s  
- 100% logging & user confirmations  

### Voice Interaction
- WER < 10%  
- Latency < 3s  
- TTS Clarity > 4/5  
- Voice Task Success > 80%  

---

## 9. Failure Analysis (Planned)

- **RAG Failure**: Missing policy chunk → mitigation: improve chunking + hybrid search.  
- **Agent Misuse**: Wrong tool/action → mitigation: confirmation prompts + strict guardrails.  
- **Voice Errors**: Noisy environment → mitigation: fallback to text + retry logic.  
- **Data Drift**: Outdated handbook policies → mitigation: scheduled re-indexing.  

---

## 10. Deployment Infrastructure (Planned)

- **Backend**: Python, FastAPI, LangChain, ChromaDB/Pinecone.  
- **LLMs**: LLaMA-3, SciBERT (fine-tuned).  
- **Cloud**: Azure ML / GCP AI Platform.  
- **Integrations**: LMS, HRIS APIs, calendars.  
- **Frontend**: Streamlit / React (mobile-first).  
- **Voice**: Coqui TTS, Whisper STT.  

(Diagram to be added in repo)

---

## 11. Monitoring Plan (Planned)

- **LLM Metrics**: retrieval recall, factuality, hallucination.  
- **Agent Metrics**: tool accuracy, task success, escalation rate.  
- **Voice Metrics**: WER, latency, fallback rate.  
- **Usage Logs**: all queries + actions auditable.  
- **User Feedback**: rating after each session.  

---

## 12. Success & Acceptance Criteria

- RAG accuracy (Recall@5 > 90%, Hallucination < 5%).  
- Agentic tasks > 85% success rate.  
- Voice interaction end-to-end success > 80%.  
- HR workload reduction > 30%.  
- Positive user satisfaction (avg > 4/5).  

---

## 13. Timeline (Preliminary)

| Phase | Duration | Milestones |
|-------|----------|------------|
| Data Collection & Preprocessing | 2 weeks | Build Q&A dataset |
| Prototype RAG System | 3 weeks | Basic handbook Q&A |
| Agentic Layer Dev | 3 weeks | Tool integrations |
| Voice Interaction | 2 weeks | STT/TTS integration |
| Deployment Infra Setup | 2 weeks | Cloud, APIs, monitoring |
| Testing & Validation | 2 weeks | Metrics evaluation |
| Final Demo & Report | 1 week | End-to-end system |

---

## 14. Additional Information

- Strictly **research/educational use only**.  
- Potential for **enterprise adoption** via APIs + HRIS integration.  
- Long-term: **multi-lingual support**, **offline mobile app**, **real-time compliance monitoring**.  

---

## 📂 Repository Structure (planned)

├── data/ # Raw and processed handbook data
├── notebooks/ # Exploration & preprocessing
├── src/ # RAG + agentic pipeline
├── infra/ # Deployment configs (GCP/Azure/Docker)
├── docs/ # Diagrams, reports, presentations
├── README.md # Project overview



---

## 🔑 License & Usage

This project is intended for **academic and research use only**.  
All employee handbook content is sourced from **publicly available PDFs**. Redistribution of proprietary content is not permitted.  

---
