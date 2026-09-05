"""Memoize backend.

The backend imports the `ai` package, which lives at the repo root, while
uvicorn is normally started from `backend/`. Put the repo root on sys.path here
— before any submodule imports — so `import ai.*` resolves either way.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
