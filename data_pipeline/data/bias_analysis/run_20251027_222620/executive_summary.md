# Executive Summary: Data Bias Insights — All data

### 1. Key Representation Findings

- **Industry** → Low imbalance (Gini=0.20, Entropy=3.08, Ratio=3.5)
  - Top categories: Logistics (67), Finance (59), Construction (54)

- **Org** → Low imbalance (Gini=0.00, Entropy=-0.00, Ratio=1.0)
  - Top categories: General Business (390)

- **Doc_type** → Low imbalance (Gini=0.00, Entropy=-0.00, Ratio=1.0)
  - Top categories: handbook (390)

- **Company** → Low imbalance (Gini=0.25, Entropy=4.03, Ratio=5.9)
  - Top categories: Buchheit Logistics (47), Tnt Construction (35), Old National Bank (34)

- **Policy_tags** → Moderate imbalance (Gini=0.59, Entropy=5.60, Ratio=58.0)
  - Top categories:  (58), REST (47), HARASSMENT (27)

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
