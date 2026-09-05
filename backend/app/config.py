"""Settings loaded from the repo-root .env. TODO(backend): extend as needed."""

import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://recollect:recollect@localhost:5432/recollect")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
JUDGE0_URL = os.getenv("JUDGE0_URL", "https://ce.judge0.com")
JUDGE0_API_KEY = os.getenv("JUDGE0_API_KEY", "")
JUDGE0_API_HOST = os.getenv("JUDGE0_API_HOST", "")
USE_MOCK_AI = os.getenv("USE_MOCK_AI", "true").lower() == "true"
CORS_ORIGINS = [o.strip() for o in os.getenv(
    "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",") if o.strip()]
