import pandas as pd
from great_expectations.dataset import PandasDataset

df = pd.read_csv("data_pipeline/data/cleaned/cleaned_chunks.csv")
gx_df = PandasDataset(df)

gx_df.expect_column_to_exist("filename")
gx_df.expect_column_values_to_not_be_null("text")
gx_df.expect_column_values_to_be_of_type("chunk_id", "int64")
gx_df.expect_column_values_to_be_between("chunk_id", min_value=1, max_value=10000)

results = gx_df.validate()
print(results)
