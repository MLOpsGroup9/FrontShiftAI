# Data Pipeline Structure

## Data Directories
```
data/
├── raw/           # Original PDF/DOCX files
├── pages/         # Extracted text pages
├── chunks/        # Semantic text chunks
├── qna/          # Generated Q&A pairs
└── chroma_db/    # Vector embeddings
```

## File Formats

1. `raw/*.pdf` - Source documents
2. `pages/*.txt` - Extracted text, one file per document
3. `chunks/*.jsonl` - Text chunks with metadata:
```json
{
    "chunk_id": "chunk_0",
    "text": "...",
    "start_char": 0,
    "length": 1000,
    "metadata": {
        "source": "handbook.pdf",
        "date": "2024-03-21"
    }
}
```

4. `qna/*.jsonl` - Q&A pairs:
```json
{
    "instruction": "What is the policy on X?",
    "output": "The policy states...",
    "context": "Original chunk text...",
    "metadata": {
        "chunk_id": "chunk_0",
        "source": "handbook.pdf"
    }
}
```

## Processing Flow
1. PDF → raw/
2. raw/ → pages/ (text extraction)
3. pages/ → chunks/ (semantic splitting)
4. chunks/ → qna/ (Q&A generation)
5. qna/ → chroma_db/ (embedding)