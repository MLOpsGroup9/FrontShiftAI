# Advanced Bias Detection Report — All data

## Representation Metrics

**industry** — unique=9, gini=0.197, entropy=3.079, ratio_imbalance=3.53
Top-5: Logistics:67, Finance:59, Construction:54, Retail:49, Manufacturing:47

**org** — unique=1, gini=0.000, entropy=-0.000, ratio_imbalance=1.00
Top-5: General Business:390

**doc_type** — unique=1, gini=0.000, entropy=-0.000, ratio_imbalance=1.00
Top-5: handbook:390

**company** — unique=18, gini=0.249, entropy=4.027, ratio_imbalance=5.87
Top-5: Buchheit Logistics:47, Tnt Construction:35, Old National Bank:34, B G Foods:29, Lunds Byerlys:27

**policy_tags** — unique=117, gini=0.592, entropy=5.596, ratio_imbalance=58.00
Top-5: :58, REST:47, HARASSMENT:27, HARASSMENT|REST:18, FMLA:12

## Divergence from Uniform (KL)

- industry: KL=0.063
- org: KL=0.000
- doc_type: KL=0.000
- company: KL=0.099

## Sentiment Bias
- See `sentiment_by_industry.png` and `sentiment_by_doc.csv`.

## Topic Bias
- `top_terms_by_industry.json` and `pca_topics.png`.

## Coverage Bias
- `policy_tag_counts.csv`, `keyword_top100.csv`, and `policy_tags_top20.png`.
