# WTF Does This Repo Do?

An AI-powered codebase intelligence tool for understanding unfamiliar repositories and reviewing changes. The project currently supports secure repository ingestion and temporary workspace management. Source-code parsing is not implemented yet.

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

## Ingest a repository

Clone a public GitHub repository into temporary storage:

```bash
curl -X POST http://localhost:8000/api/v1/repositories/github \
  -H 'Content-Type: application/json' \
  -d '{"repository_url":"https://github.com/owner/repository"}'
```

Or upload a ZIP archive:

```bash
curl -X POST http://localhost:8000/api/v1/repositories/uploads \
  -F 'repository=@repository.zip;type=application/zip'
```

Both endpoints return an opaque workspace `id`, file count, byte count, and expiration time. Inspect or delete the workspace with:

```bash
curl http://localhost:8000/api/v1/repositories/WORKSPACE_ID
curl -X DELETE http://localhost:8000/api/v1/repositories/WORKSPACE_ID
```

Repository workspaces expire after one hour by default and are deleted when the API shuts down. Git metadata is removed after cloning, unsafe archive paths and symbolic links are rejected, and configurable file/size limits protect temporary storage. Repository code is never executed.

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
