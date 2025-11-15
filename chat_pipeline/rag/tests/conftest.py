"""Test configuration for RAG package."""

import sys
from pathlib import Path

# Ensure the repository root is on sys.path so `import rag` works no matter
# where pytest is invoked from (project root or `chat_pipeline/`).
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
