# WTF Does This Repo Do?

An AI-powered codebase intelligence tool for understanding unfamiliar repositories and reviewing changes. It currently supports secure repository ingestion, Tree-sitter source parsing, dependency graph construction, code chunking, an ephemeral local vector index, and an interactive repository dashboard. AI features are not implemented yet.

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

## Parse an imported repository

Parse the supported source files in an active workspace:

```bash
curl -X POST http://localhost:8000/api/v1/repositories/WORKSPACE_ID/parse
```

The response contains normalized file metadata and discovered functions, methods, classes, interfaces, and type aliases with source locations. Python, JavaScript, TypeScript, and TSX are currently supported.

## Index a parsed repository

Build or replace the in-memory index for an active workspace:

```bash
curl -X POST http://localhost:8000/api/v1/repositories/WORKSPACE_ID/index
```

Retrieve the current index without rebuilding it:

```bash
curl http://localhost:8000/api/v1/repositories/WORKSPACE_ID/index
```

The index contains normalized metadata, resolved local imports, external-module references, conservative internal call edges, graph nodes and edges, symbol-aware code chunks, and deterministic local embeddings. Indexes expire and are deleted with their repository workspace. The feature-hashing embedding adapter provides local vector indexing without sending code to an external service; AI-backed retrieval remains a later phase.

The web app provides a form for the same public GitHub ingestion flow. Interactive API documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs).

## Run the web app

In a second terminal:

```bash
cd apps/web
npm install
cp ../../.env.example .env.local
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

Submit a public GitHub URL to import and index the repository. When indexing completes, the dashboard displays a hierarchical source tree, a structural repository overview, an architecture-level import graph, and a detailed symbol relationship graph. The overview is derived from static metadata; it is not AI-generated.

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
