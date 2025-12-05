# Executive Summary: Data Bias Insights — All data

### 1. Key Representation Findings

- **Industry** → Low imbalance (Gini=0.24, Entropy=3.04, Ratio=3.7)
  - Top categories: Logistics (134), Finance (115), Retail (98)

- **Org** → Low imbalance (Gini=0.00, Entropy=-0.00, Ratio=1.0)
  - Top categories: General Business (700)

- **Doc_type** → Low imbalance (Gini=0.00, Entropy=-0.00, Ratio=1.0)
  - Top categories: handbook (700)

- **Company** → Low imbalance (Gini=0.25, Entropy=3.94, Ratio=6.3)
  - Top categories: Buchheit Logistics (94), Old National Bank (66), B G Foods (56)

- **Policy_tags** → High imbalance (Gini=0.69, Entropy=5.20, Ratio=151.0)
  - Top categories:  (151), REST (101), HARASSMENT (48)

### 2. Overall Bias Interpretation
- Uneven representation across categories may require rebalancing.

### 3. Sentiment & Topic Overview
- Inspect sentiment and topic plots to understand tonal or topical skew.

### 4. Recommended Actions
1) Collect samples for underrepresented categories.
2) Diversify document types where imbalance is high.
3) Expand metadata coverage (policy tags, keywords).
4) Verify tone bias with complementary NLP tooling.

### 5. Confidence Summary
- Representation: High
- Topic: Moderate
- Sentiment: Low–Moderate
