# Advanced Bias Detection Report — All data

## Representation Metrics

**industry** — unique=2, gini=0.066, entropy=0.987, ratio_imbalance=1.31
Top-5: Retail:98, Healthcare:75

**org** — unique=1, gini=0.000, entropy=-0.000, ratio_imbalance=1.00
Top-5: General Business:173

**doc_type** — unique=1, gini=0.000, entropy=-0.000, ratio_imbalance=1.00
Top-5: handbook:173

**company** — unique=4, gini=0.088, entropy=1.981, ratio_imbalance=1.58
Top-5: Lunds Byerlys:52, Holiday Market:46, Crouse Medical Practice:42, Healthcare Services Group:33

**policy_tags** — unique=53, gini=0.563, entropy=4.688, ratio_imbalance=32.00
Top-5: :32, REST:29, HARASSMENT:9, PTO:8, FMLA:7

## Divergence from Uniform (KL)

- industry: KL=0.009
- org: KL=0.000
- doc_type: KL=0.000
- company: KL=0.013

## Sentiment Bias
- See `sentiment_by_industry.png` and `sentiment_by_doc.csv`.

## Topic Bias
- `top_terms_by_industry.json` and `pca_topics.png`.

## Coverage Bias
- `policy_tag_counts.csv`, `keyword_top100.csv`, and `policy_tags_top20.png`.
