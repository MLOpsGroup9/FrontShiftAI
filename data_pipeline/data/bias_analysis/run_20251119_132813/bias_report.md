# Advanced Bias Detection Report — All data

## Representation Metrics

**industry** — unique=9, gini=0.238, entropy=3.041, ratio_imbalance=3.72
Top-5: Logistics:134, Finance:115, Retail:98, Manufacturing:92, Healthcare:75

**org** — unique=1, gini=0.000, entropy=-0.000, ratio_imbalance=1.00
Top-5: General Business:700

**doc_type** — unique=1, gini=0.000, entropy=-0.000, ratio_imbalance=1.00
Top-5: handbook:700

**company** — unique=17, gini=0.250, entropy=3.939, ratio_imbalance=6.27
Top-5: Buchheit Logistics:94, Old National Bank:66, B G Foods:56, Lunds Byerlys:52, Home Bank:49

**policy_tags** — unique=132, gini=0.692, entropy=5.200, ratio_imbalance=151.00
Top-5: :151, REST:101, HARASSMENT:48, HARASSMENT|REST:28, FMLA:20

## Divergence from Uniform (KL)

- industry: KL=0.090
- org: KL=0.000
- doc_type: KL=0.000
- company: KL=0.103

## Sentiment Bias
- See `sentiment_by_industry.png` and `sentiment_by_doc.csv`.

## Topic Bias
- `top_terms_by_industry.json` and `pca_topics.png`.

## Coverage Bias
- `policy_tag_counts.csv`, `keyword_top100.csv`, and `policy_tags_top20.png`.
