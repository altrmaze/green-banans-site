# Greens ACC Platform

Greens ACC is a fresh multi-agent corporate trading and accounting scaffold with a React frontend, a FastAPI backend, and Supabase migration assets.

## Structure

- `greens-acc-platform/frontend` — Vite + React corporate interface with Tailwind styling
- `greens-acc-platform/backend` — FastAPI service and agent orchestration placeholders
- `greens-acc-platform/supabase/migrations` — initial database migration assets

## Frontend

```bash
cd greens-acc-platform/frontend
npm install
npm run dev
```

## Backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r greens-acc-platform/backend/requirements.txt
uvicorn app.main:app --app-dir greens-acc-platform/backend --reload
```

## Root compatibility

A root `requirements.txt` is provided to install the backend dependencies from the repository root.
