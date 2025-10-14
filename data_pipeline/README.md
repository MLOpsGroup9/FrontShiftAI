```bash

FrontShiftAI/
 ├── data_pipeline/
 │   ├── data/
 │   │   ├── raw/            ← versioned by DVC
 │   │   ├── extracted/      ← versioned by DVC
 │   │   ├── cleaned/        ← versioned by DVC
 │   │   └── vector_db/      ← versioned by DVC
 │   └── scripts/
 │       ├── data_extraction.py
 │       ├── preprocess.py
 │       └── store_in_chromadb.py
 ├── dvc.yaml                 ← pipeline definition
 ├── dvc.lock                 ← data version snapshot
 ├── .dvc/config              ← DVC remote setup
 ├── .gitignore               ← excludes data folders
 └── ../dvc_storage/          ← actual data storage (remote)

```