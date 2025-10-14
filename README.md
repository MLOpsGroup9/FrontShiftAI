# Project Scoping - FrontShiftAI: AI Copilot for Deskless Workers

**Team Members**  
- Harshitkumar Brahmbhatt  
- Krishna Venkatesh  
- Raghav Gali  
- Rishi Raj Kuleri  
- Sujitha Godishala  
- Swathi Baba Eswarappa  

---

## 1. Introduction
Deskless workers face limited access to HR systems due to **irregular schedules, lack of computer access, and fragmented communication**.  

These challenges lead to:  
- Lower benefits enrollment/utilization  
- Poor training adoption  
- High attrition and disengagement  

**Proposed Solution:**  
- **RAG core** → Retrieves grounded answers from HR docs and policies.  
- **Agentic layer** → Executes actions like scheduling, compliance checks, escalation.  
- **Voice interaction (planned)** → Enables hands-free access for frontline roles.  

---

## 2. Dataset Information

### 2.1 Dataset Card
| Attribute      | Description |
|----------------|-------------|
| **Name**       | Deskless Worker Handbook Q&A Dataset |
| **Size**       | 200–20,000 Q&A pairs |
| **Sources**    | Publicly available employee handbooks (healthcare, retail, logistics, hospitality, finance, construction, etc.) |
| **Formats**    | PDF (retrieval embedding) |
| **Data Types** | Natural language questions, concise answers, metadata (source, industry, section) |

### 2.2 Example Sources
- Healthcare: [Crouse Medical Handbook (2019)](https://crousemed.com/media/1449/cmp-employee-handbook.pdf)  
- Retail: [Lunds & Byerlys Handbook (2019)](https://corporate.lundsandbyerlys.com/wp-content/uploads/2024/05/EmployeeHandbook_20190926.pdf)  
- Manufacturing: [BG Foods Handbook (2022)](https://bgfood.com/wp-content/uploads/2022/01/BG-Employee-Handbook-2022.pdf)  
- Construction: [TNT Construction Handbook (2018)](https://www.tntconstructionmn.com/wp-content/uploads/2018/05/TNT-Construction-Inc-Handbook_Final-2018.pdf)  
- Hospitality: [Alta Peruvian Lodge Handbook (2016)](https://www.altaperuvian.com/wp-content/uploads/2017/01/APL-Empl-Manual-Revised-12-22-16-fixed.pdf)  
- Finance: [Old National Bank Handbook](https://www.oldnational.com/globalassets/onb-site/onb-documents/onb-about-us/onb-team-member-handbook/team-member-handbook.pdf)  

### 2.3 Rights & Privacy
- **Source Material**: All handbooks are public PDFs.  
- **Usage**: Research/educational only.  
- **Privacy**: No personal data; only policy text.  
- **Compliance**: GDPR/CCPA principles respected.  

---

## 3. Data Planning and Splits

### 3.1 Preprocessing Steps
- Extract text from PDFs (PyMuPDF, PDFMiner)  
- Clean headers/footers, remove duplicates  
- Chunk into policy sections  
- Generate Q&A pairs (manual + synthetic)  
- Normalize into JSONL schema  

### 3.2 Splitting Strategy
- **Train (70%)** → Q&A pairs for fine-tuning  
- **Validation (15%)** → Hyperparameter tuning  
- **Test (15%)** → Final evaluation  
- Stratified by industry, deduplicated  

---

## 4. Problems & Current Solutions
- **HCM Suites** (Workday, SAP) → Admin-focused, vendor-locked  
- **Enterprise Assistants** (Oracle DA) → Rigid, schema-bound  
- **LMS Microlearning** (Docebo, Cornerstone) → Static, non-queryable  
- **Generic Chatbots** (Leena AI, Talla) → FAQ-only, no grounding  
- **Self-Service Portals** → Desktop-centric, not conversational  
- **Slack/Teams** → Transient, non-retrievable  

---

## 5. Proposed Solution
- **RAG for grounded answers** (cited, accurate)  
- **Agentic orchestration** for HR workflows (scheduling, compliance, escalation)  
- **Personalization & memory** for context-aware Q&A  
- **System integration** with HRIS, LMS, calendars  
- **Safe fallback** when confidence is low  
- **Voice accessibility** for frontline workers  

---

## 6. Current Flow & Bottlenecks
Traditional HR flow → **HR overload, fragmented systems, limited access**.  
**AI Copilot improves** with:  
- Automated retrieval (RAG)  
- Unified query interface  
- Mobile/voice accessibility  
- 24/7 availability  
- Analytics feedback loop  

---

## 7. Metrics, Objectives, and Business Goals
- **Objectives:** Build RAG system, enable agentic actions, provide voice interface, ensure compliance.  
- **Business Alignment:** HR efficiency, training compliance, engagement, reduced risk, scalable support.  

---

## 8. Key Metrics
- **RAG** → Recall@5 > 90%, Factuality > 85%, F1 > 80%, Hallucination < 5%  
- **Agentic** → Tool accuracy > 90%, Task success > 85%, Fallback > 95%  
- **Voice** → WER < 10%, Latency < 3s, Voice success > 80%  

---

## 9. Failure Analysis
- **Data ingestion** → corrupted PDFs → multi-parser fallback  
- **Retrieval** → poor recall → hybrid retrieval, eval thresholds  
- **LLM gen** → hallucination → context-only guardrails  
- **Agents** → wrong tool → JSON schema validation, confirmations  
- **Infra** → latency spikes → autoscaling, caching, fallback modes  

---

## 10. Deployment Infrastructure
- **Backend**: FastAPI on GKE  
- **RAG**: Hugging Face embeddings + ChromaDB (GKE)  
- **LLM**: LLaMA-3 8B (Vertex AI endpoint)  
- **Agents**: LangChain/LangGraph on GKE  
- **Voice**: Google Cloud STT/TTS  
- **Data**: GCS (docs), Cloud SQL (metadata), JSONL/CSV  
- **Monitoring**: Cloud Monitoring, Prometheus/Grafana, Vertex AI drift detection  

---

## 11. Monitoring Plan
- Track retrieval recall, hallucination, tool accuracy, fallback rate, WER, latency  
- GCP Cloud Monitoring alerts + Grafana dashboards  
- Future: drift detection, detailed audit logs  

---

## 12. Success & Acceptance Criteria
- **RAG**: Recall@5 ≥ 90%, Hallucination ≤ 5%  
- **Agentic**: Task success ≥ 85%  
- **Voice**: WER ≤ 10%, latency ≤ 3s  
- **Pilot Study**: ≥ 80% accuracy, ≥ 4/5 satisfaction  

---

## 13. Timeline (10 weeks)
1. **Dataset & Retrieval MVP (Weeks 1–2)**  
2. **Agentic Layer MVP (Weeks 3–4)**  
3. **Voice Prototype (Weeks 5–6)**  
4. **Monitoring & Hardening (Weeks 7–8)**  
5. **Pilot & Acceptance (Weeks 9–10)**  

---

## 14. Additional Information
The stack may evolve (embedding models, vector DBs, orchestration libs), but changes will be **incremental and non-disruptive**.  
Core principles (RAG core, agentic orchestration, GCP deployment, voice accessibility) remain unchanged.  

---

## 15. Repository Structure
```bash
FrontShiftAI/
├── .dvc/
├── .pytest_cache/
│
├── data_pipeline/
│ ├── pycache/
│ ├── dags/
│ ├── data/
│ │ ├── raw/
│ │ ├── extracted/
│ │ ├── cleaned/
│ │ └── vector_db/
│ ├── logs/
│ ├── scripts/
│ │ ├── init.py
│ │ ├── data_extraction.py
│ │ ├── preprocess.py
│ │ ├── store_in_chromadb.py
│ │ ├── validate_data.py
│ │ └── test_rag_llama.py
│ ├── tests/
│ │ ├── init.py
│ │ ├── test_data_extraction.py
│ │ ├── test_preprocess.py
│ │ └── test_pipeline_integration.py
│ ├── utils/
│ │ └── logger.py
│ ├── init.py
│ └── README.md
│
├── docs/
├── logs/
│
├── models/
│ ├── .cache/
│ ├── Meta-Llama-3-8B-Instruct.Q4_K_M.gguf
│ └── README.md
│
├── src/
│ ├── agents/
│ ├── api/
│ ├── rag/
│ ├── utils/
│ └── voice/
│
├── .dvcignore
├── .gitignore
├── dvc.lock
├── dvc.yaml
├── environment.yml
├── License.md
├── README.md
└── requirements.txt
```

---

## 🔗 Repository
👉 [FrontShiftAI GitHub](https://github.com/MLOpsGroup9/FrontShiftAI)
