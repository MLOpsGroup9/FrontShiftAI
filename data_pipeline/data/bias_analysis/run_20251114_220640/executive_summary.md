# Executive Summary: Data Bias Insights — All data

### 1. Key Representation Findings

- **Industry** → Low imbalance (Gini=0.07, Entropy=0.99, Ratio=1.3)
  - Top categories: Retail (98), Healthcare (75)

- **Org** → Low imbalance (Gini=0.00, Entropy=-0.00, Ratio=1.0)
  - Top categories: General Business (173)

- **Doc_type** → Low imbalance (Gini=0.00, Entropy=-0.00, Ratio=1.0)
  - Top categories: handbook (173)

- **Company** → Low imbalance (Gini=0.09, Entropy=1.98, Ratio=1.6)
  - Top categories: Lunds Byerlys (52), Holiday Market (46), Crouse Medical Practice (42)

- **Policy_tags** → Moderate imbalance (Gini=0.56, Entropy=4.69, Ratio=32.0)
  - Top categories:  (32), REST (29), HARASSMENT (9)

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
