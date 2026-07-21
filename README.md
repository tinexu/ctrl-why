# WTF Does This Repo Do?

An AI-powered codebase intelligence tool for understanding unfamiliar repositories and reviewing changes. It currently supports secure repository ingestion, Tree-sitter source parsing, dependency graph construction, code chunking, an ephemeral local vector index, grounded repository chat, and pasted Git diff impact analysis.

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

The index contains normalized metadata, resolved local imports, external-module references, conservative internal call edges, graph nodes and edges, symbol-aware code chunks, and deterministic local embeddings. Indexes expire and are deleted with their repository workspace. The feature-hashing embedding adapter provides local vector indexing without sending the full repository to an external service. Chat retrieves a small set of relevant chunks before asking the configured OpenAI model to answer.

## Find where a feature is implemented

Search an indexed repository with a natural-language description:

```bash
curl -X POST http://localhost:8000/api/v1/repositories/WORKSPACE_ID/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"Where is authentication handled?","limit":5}'
```

Results include ranked file paths, symbols, line ranges, relevance scores, match reasons, and bounded source excerpts. The dashboard exposes the same workflow through its **Feature finder** panel.

The web app provides a form for the same public GitHub ingestion flow. Interactive API documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs).

## Analyze a pull request diff

After indexing a repository, paste a unified Git diff into the dashboard's **Pull request impact** panel. The analyzer maps changed lines to indexed symbols, finds files that import or call changed code, scores risk, flags a small set of suspicious added-line patterns, and suggests tests. If `OPENAI_API_KEY` is configured, the summary and additional test suggestions are AI-enhanced using only the structured analysis and redacted added-line evidence. Without a key, the complete deterministic analysis still works.

You can test the endpoint directly:

```bash
curl -X POST http://localhost:8000/api/v1/repositories/WORKSPACE_ID/pull-request-analysis \
  -H 'Content-Type: application/json' \
  --data-binary @- <<'JSON'
{
  "title": "Change authentication behavior",
  "diff": "diff --git a/pkg/auth.py b/pkg/auth.py\n--- a/pkg/auth.py\n+++ b/pkg/auth.py\n@@ -1,2 +1,2 @@\n-old behavior\n+new behavior"
}
JSON
```

The MVP accepts pasted diffs; it does not fetch pull requests from GitHub yet.

## Explain a CI/CD failure

Paste the failed workflow step output into the dashboard's **CI/CD Copilot** panel. The analyzer classifies common test, type-check, lint, build, dependency, and configuration failures; extracts the most relevant log lines; matches mentioned paths against the repository index; and retrieves related code. It returns a likely cause, affected files, recommendations, validation steps, and separate log/source evidence.

If `OPENAI_API_KEY` is configured, the explanation is AI-enhanced from only that bounded evidence. Common credential-shaped values are redacted before evidence is sent to OpenAI. Without a key, deterministic classification and repository retrieval still run.

Test the endpoint directly:

```bash
curl -X POST http://localhost:8000/api/v1/repositories/WORKSPACE_ID/ci-analysis \
  -H 'Content-Type: application/json' \
  --data-binary @- <<'JSON'
{
  "workflow_name": "Tests",
  "logs": "Run pytest\nFAILED tests/test_users.py::test_create_user\nAssertionError: expected 201, received 422\nProcess completed with exit code 1"
}
JSON
```

This phase accepts pasted logs. Direct GitHub Actions integration and automatic patch generation are not implemented.

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
