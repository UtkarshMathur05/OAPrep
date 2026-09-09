# One image, one origin: the frontend is built here and served by the same
# FastAPI process that answers the API. That is a cookie decision rather than a
# packaging one — see FRONTEND_DIST in backend/app/config.py.
#
# Docker rather than a platform's native Python runtime because the build needs
# both Node and Python, and this way that is stated instead of assumed.

# ---------------------------------------------------------------- frontend
FROM node:22-slim AS frontend

WORKDIR /build
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci || npm install

COPY frontend/ ./
# Empty base URL: the app calls the origin it was served from. Mock mode is off
# because a deployed build that quietly serves canned data is worse than one
# that visibly fails.
ENV VITE_API_BASE_URL="/api"
ENV VITE_USE_MOCK=false
RUN npm run build


# ----------------------------------------------------------------- runtime
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv

COPY backend/requirements.txt backend/requirements.txt
COPY ai/requirements.txt ai/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt -r ai/requirements.txt

# `backend/app/__init__.py` puts the repo root on sys.path so `ai.*` imports
# resolve, so these two have to stay siblings.
COPY backend/ backend/
COPY ai/ ai/
COPY --from=frontend /build/dist frontend/dist

EXPOSE 8000
WORKDIR /srv/backend
# $PORT is what Render (and most PaaS) binds; 8000 keeps `docker run` simple.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
