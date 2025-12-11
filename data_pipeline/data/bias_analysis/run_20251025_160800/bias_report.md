# Advanced Bias Detection Report — All data

## Representation Metrics

**industry** — unique=9, gini=0.199, entropy=3.078, ratio_imbalance=3.70
Top-5: Logistics:74, Finance:61, Retail:49, Manufacturing:48, Construction:38

**org** — unique=1, gini=0.000, entropy=-0.000, ratio_imbalance=1.00
Top-5: General Business:391

**doc_type** — unique=1, gini=0.000, entropy=-0.000, ratio_imbalance=1.00
Top-5: handbook:391

**company** — unique=18, gini=0.247, entropy=4.024, ratio_imbalance=6.50
Top-5: Buchheit Logistics:52, Old National Bank:36, B G Foods:31, Lunds Byerlys:28, Jacob Heating And Cooling:25

**policy_tags** — unique=115, gini=0.607, entropy=5.434, ratio_imbalance=63.00
Top-5: :63, REST:57, HARASSMENT:28, HARASSMENT|REST:16, MEAL|REST:11

## Divergence from Uniform (KL)

- industry: KL=0.064
- org: KL=0.000
- doc_type: KL=0.000
- company: KL=0.101

## Sentiment Bias
- See `sentiment_by_industry.png` and `sentiment_by_doc.csv`.

## Topic Bias
- `top_terms_by_industry.json` and `pca_topics.png`.

## Coverage Bias
- `policy_tag_counts.csv`, `keyword_top100.csv`, and `policy_tags_top20.png`.
