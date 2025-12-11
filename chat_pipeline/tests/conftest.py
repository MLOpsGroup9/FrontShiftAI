"""Test configuration for chat_pipeline."""

import sys
from pathlib import Path

# Ensure the repository root is on sys.path so `import chat_pipeline` works no matter
# where pytest is invoked from.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
