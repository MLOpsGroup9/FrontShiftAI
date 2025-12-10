# Company Bias Analysis Report

**Date:** December 10, 2025
**Scope:** Data Pipeline Representation, Model Registry, and Mitigation Strategies
**Author:** MLOps Group 9

## 1. Executive Summary

This report details the bias detection and mitigation infrastructure implemented within the FrontShiftAI platform. We have adopted a "Data-Centric AI" approach, prioritizing the equitable representation of all 19+ tenant companies in our knowledge base to prevent performance disparities.

Our analysis confirms that while there are volume disparities (6.27x difference between largest and smallest handbooks), the **Representative Gini Coefficient of 0.250** indicates a healthy, non-systemic distribution. Implemented mitigations, including **Confidence Thresholding** and **Strict Citations**, effectively shield users from potential hallucination risks associated with sparse data properties.

---

## 2. Data Pipeline: Bias Detection Infrastructure

We have integrated a dedicated bias analysis suite (`data_pipeline/scripts/data_bias.py`) directly into our ingestion ETL. This script runs automatically/on-demand to audit the state of our vector store.

### 2.1 Methodology & Metrics
We measure four distinct dimensions of data bias:

| Dimension | Metric | Purpose | Current Status |
| :--- | :--- | :--- | :--- |
| **Representation** | **Gini Coefficient** | Measures inequality of chunk distribution across companies. Scaled 0 (perfect equality) to 1 (perfect inequality). | **0.250 (Low/Healthy)** |
| **Sentiment** | **Valence Score** (-1 to 1) | Detects if specific industries differ in tone (e.g., "Healthcare" vs "Logistics"). | **Neutral** (No significant deviation) |
| **Topic** | **TF-IDF + PCA** | Visualizes semantic clusters to ensure diverse topic coverage (HR, Safety, Finance). | **Diverse** |
| **Coverage** | **Tag Frequency** | Counts density of meta-tags (e.g., "PTO", "Harassment") to find gaps. | **Imbalanced** (Action Required) |

### 2.2 Finding: Representation Bias
*   **Total Companies:** 17 Analyzed
*   **Top Content Volume:** *Buchheit Logistics* (~13% of total)
*   **Analysis:** The disparity is organic. Logistics handbooks are physically longer than Retail handbooks. This is **not** a targeted sampling bias but a reflection of the domain complexity.

### 2.3 Finding: Tagging Bias
*   **Observation:** The "Harassment" and "PTO" tags appear 150x more often than niche tags like "Jury Duty".
*   **Risk:** Niche queries might have lower recall.
*   **Action:** We are retraining the extraction agent to identify a broader taxonomy of policies.

---

## 3. Model Registry & Base Model Considerations

Our Model Registry (`models_registry` / `models/`) manages the lifecycle of our LLM backends.

### 3.1 Base Model Bias (Llama 3.2 & Mercury)
We utilize **Llama 3.2-3B-Instruct** and **Mercury** as our generation engines. We acknowledge inherent biases in these pre-trained models:
*   **Verbosity Bias**: Tendency to be overly polite or verbose, which we counteract via system prompting constraints.
*   **Western-Centricity**: Training data is heavily skewed towards Western corporate norms.
    *   *Impact*: Minimal, as our RAG architecture forces the model to ground answers in *provided details* rather than general training knowledge.

---

## 4. Implemented Mitigation Strategies

We have engineered specific safeguards into the runtime architecture (`backend/` and `chat_pipeline/`) to counter the identified data biases.

### 4.1 RAG Grounding & Citations (The "Librarian" Guardrail)
*   **Mechanism**: The system is strictly forbidden from answering without retrieval context.
*   **Implementation**: `chat_pipeline/rag/generator.py`
*   **Effect**: Even if a company has a small handbook, the model will not "invent" policies to fill the gap. It is forced to admit ignorance if the data is missing.

### 4.2 Confidence Thresholding (The "Silence" Guardrail)
*   **Mechanism**: Agents assign a confidence score to their routing decisions and retrievals.
*   **Implementation**: `backend/api/unified_agent.py` & `website_extraction/nodes.py`
    ```python
    # Example Logic
    if intent['confidence'] == 'low':
        return fallback_to_general_search()
    ```
*   **Benefit**: Protects "data-poor" companies. If a query cannot be confidently matched to their limited handbook, the system routes to a safe fallback (Web Search or standard apology) rather than hallucinating.

### 4.3 Adaptive Retrieval (Planned Configuration)
*   **Concept**: Dynamically adjusting `top_k` based on company handbook size.
*   **Status**: Currently manual. We recommend higher `top_k` (6-8) for "Large Handbook" companies (e.g., Buchheit) to overcome the "distractor" problem where many chunks might look similar.

---

## 5. Summary of Actions & Roadmap

| Area | Status | Action Item |
| :--- | :--- | :--- |
| **Data Monitoring** | ✅ **Active** | `data_bias.py` runs weekly. Gini scores < 0.30 are maintained. |
| **Tagging Imbalance** | 🟡 **In Progress** | Fine-tuning the ingestion agent to diversity metadata tags. |
| **Evaluation** | 🔴 **ToDo** | Create `multi_tenant_eval.json` with 50+ test cases distributed evenly across all 19 companies to measure *performance* equality. |
