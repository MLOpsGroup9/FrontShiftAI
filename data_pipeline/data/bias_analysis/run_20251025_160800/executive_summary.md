# Executive Summary: Data Bias Insights — All data

### 1. Key Representation Findings

- **Industry** → Low imbalance (Gini=0.20, Entropy=3.08, Ratio=3.7)
  - Top categories: Logistics (74), Finance (61), Retail (49)

- **Org** → Low imbalance (Gini=0.00, Entropy=-0.00, Ratio=1.0)
  - Top categories: General Business (391)

- **Doc_type** → Low imbalance (Gini=0.00, Entropy=-0.00, Ratio=1.0)
  - Top categories: handbook (391)

- **Company** → Low imbalance (Gini=0.25, Entropy=4.02, Ratio=6.5)
  - Top categories: Buchheit Logistics (52), Old National Bank (36), B G Foods (31)

- **Policy_tags** → High imbalance (Gini=0.61, Entropy=5.43, Ratio=63.0)
  - Top categories:  (63), REST (57), HARASSMENT (28)

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
