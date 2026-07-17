# WTF Does This Repo Do?

An AI-powered codebase intelligence tool for understanding unfamiliar repositories and reviewing changes. The project is currently in Phase 1: the frontend and backend application foundations are runnable, but repository analysis is not implemented yet.

## Prerequisites

- Node.js 20 or newer
- Python 3.11 or newer
- npm

## Environment

Copy the shared example environment file:

```bash
cp .env.example .env
```

The checked-in defaults expect the frontend at `http://localhost:3000` and the API at `http://localhost:8000`.

## Run the API

```bash
cd services/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Verify [http://localhost:8000/health](http://localhost:8000/health). It should return `{"status":"ok"}`.

## Run the web app

In a second terminal:

```bash
cd apps/web
npm install
cp ../../.env.example .env.local
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Test and build

After installing both applications' dependencies:

```bash
make test
make build
```

## Current structure

```text
apps/web/          Next.js frontend
services/api/      FastAPI backend
```

