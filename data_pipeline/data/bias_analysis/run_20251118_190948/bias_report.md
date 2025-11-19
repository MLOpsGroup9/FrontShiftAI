# Advanced Bias Detection Report — All data

## Representation Metrics

**industry** — unique=9, gini=0.199, entropy=3.077, ratio_imbalance=3.72
Top-5: Logistics:134, Finance:115, Construction:104, Retail:98, Manufacturing:92

**org** — unique=1, gini=0.000, entropy=-0.000, ratio_imbalance=1.00
Top-5: General Business:768

**doc_type** — unique=1, gini=0.000, entropy=-0.000, ratio_imbalance=1.00
Top-5: handbook:768

**company** — unique=18, gini=0.252, entropy=4.022, ratio_imbalance=6.27
Top-5: Buchheit Logistics:94, Tnt Construction:68, Old National Bank:66, B G Foods:56, Lunds Byerlys:52

**policy_tags** — unique=134, gini=0.702, entropy=5.211, ratio_imbalance=165.00
Top-5: :165, REST:107, HARASSMENT:52, HARASSMENT|REST:31, FMLA:23

## Divergence from Uniform (KL)

- industry: KL=0.064
- org: KL=0.000
- doc_type: KL=0.000
- company: KL=0.103

## Sentiment Bias
- See `sentiment_by_industry.png` and `sentiment_by_doc.csv`.

## Topic Bias
- `top_terms_by_industry.json` and `pca_topics.png`.

## Coverage Bias
- `policy_tag_counts.csv`, `keyword_top100.csv`, and `policy_tags_top20.png`.
