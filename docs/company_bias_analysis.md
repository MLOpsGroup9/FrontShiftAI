# Company Bias Analysis Report

**Date:** December 7, 2025
**Scope:** Handbook Data Representation & Model Performance Proxies

## 1. Executive Summary

This analysis evaluates potential bias in the FrontShiftAI system across the 17 supported companies. The primary focus is on **Representation Bias** (uneven data coverage) which serves as a leading indicator for potential **Performance Bias**.

> [!WARNING]
> **Performance Bias Limitation**: Direct model performance metrics (accuracy, RAG relevance) are currently generated using a standardized "Test Company" in the CI/CD pipeline. Therefore, true *performance* differences between companies cannot be measured until multi-tenant evaluation suites are implemented. Current analysis relies on data distribution metrics as a proxy.

## 2. Representation Metrics (Data Bias)

Uneven distribution of knowledge base content (handbooks) can lead to poorer RAG performance for underrepresented companies.

### Company Distribution
*   **Total Companies:** 17
*   **Gini Coefficient:** 0.250 (Low to Moderate Imbalance)
*   **Imbalance Ratio:** 6.27 (The larger companies have ~6x more data than smaller ones)

### Top 5 Companies by Content Volume
| Rank | Company | Chunks | Share of Data |
| :--- | :--- | :--- | :--- |
| 1 | Buchheit Logistics | 94 | ~13% |
| 2 | Old National Bank | 66 | ~9% |
| 3 | B G Foods | 56 | ~8% |
| 4 | Lunds Byerlys | 52 | ~7% |
| 5 | Home Bank | 49 | ~7% |

*Data Source: Advanced Bias Detection Report (2025-11-19)*

### Analysis
The relatively low Gini coefficient (0.250) indicates a **healthy distribution** of data. While *Buchheit Logistics* has more content, this is likely due to a more comprehensive handbook rather than systemic sampling bias. The system does not show severe "data poverty" for any specific company, defined as having <10 chunks.

## 3. Disparities & Explanations

| Disparity Type | Magnitude | Improvement Required? | Explanation |
| :--- | :--- | :--- | :--- |
| **Content Volume** | 6.27x (High vs Low) | 🟡 Monitor | Larger companies have longer, more detailed handbooks (e.g., Logistics vs small Retail). This is organic, not systemic. |
| **Industry Representation** | Gini: 0.238 | 🟢 Satisfactory | diverse mix across Logistics, Finance, Retail, Manufacturing, Healthcare. |
| **Policy Tagging** | Ratio: 151.0 | 🔴 Action needed | "REST" and "HARASSMENT" tags dominate. Niche policies are sparse, possibly affecting RAG retrieval for obscure queries. |

## 4. Performance Bias Hypotheses

Based on the data analysis, we can hypothesize where model performance might degrade:

1.  **Buchheit Logistics (High Volume)**: Risk of **retrieval confusion**. With 94 chunks, the RAG system has more "distractors" to filter through.
    *   *Mitigation*: Ensure `top_k` remains sufficient (e.g., 4-6) to capture relevant context.
2.  **Smaller Handbooks (<20 chunks)**: Risk of **hallucination**. If the handbook is sparse, the RAG agent may be forced to rely on general LLM knowledge or return "I don't know" more often.
    *   *Mitigation*: Strict confidence thresholds to prefer "I don't know" over hallucination.

## 5. Recommendations

1.  **Expand Evaluation Suite**: Create a `multi_tenant_eval.json` test set containing at least 5 test cases per company to measure actual RAG accuracy variances.
2.  **Enrich Policy Tags**: The imbalance in policy tags (151x ratio) suggests automated tagging is over-indexing on common terms. Fine-tune the extraction agent to recognize broader policy categories.
3.  **Context-Aware Chunking**: For smaller handbooks, consider larger chunk sizes to ensure sufficiency of context.
