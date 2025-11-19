# Executive Summary: Data Bias Insights — All data

### 1. Key Representation Findings

- **Industry** → Low imbalance (Gini=0.20, Entropy=3.08, Ratio=3.7)
  - Top categories: Logistics (134), Finance (115), Construction (104)

- **Org** → Low imbalance (Gini=0.00, Entropy=-0.00, Ratio=1.0)
  - Top categories: General Business (768)

- **Doc_type** → Low imbalance (Gini=0.00, Entropy=-0.00, Ratio=1.0)
  - Top categories: handbook (768)

- **Company** → Low imbalance (Gini=0.25, Entropy=4.02, Ratio=6.3)
  - Top categories: Buchheit Logistics (94), Tnt Construction (68), Old National Bank (66)

- **Policy_tags** → High imbalance (Gini=0.70, Entropy=5.21, Ratio=165.0)
  - Top categories:  (165), REST (107), HARASSMENT (52)

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
