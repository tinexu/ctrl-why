# WTF Does This Repo Do?

An AI-powered codebase advisor for understanding unfamiliar repositories, reviewing proposed changes, and debugging CI failures. Import a public GitHub repository, explore its structure, ask grounded questions, analyze a pasted Git diff, and connect failed pipeline logs to relevant source code.

**Live demo:** [https://ctrl-why.vercel.app](https://ctrl-why.vercel.app)

## What it does

- Imports public GitHub repositories into isolated temporary workspaces.
- Parses Python, JavaScript, TypeScript, and TSX with Tree-sitter.
- Discovers files, symbols, imports, calls, code chunks, and dependency relationships.
- Displays structural, file-level, and call-level graphs.
- Answers repository questions using retrieved code with file-and-line citations.
- Shows ranked source excerpts beneath each AI answer.
- Analyzes pasted unified Git diffs for impact, risk, affected dependents, security concerns, and suggested tests.
- Explains pasted CI/CD logs using failure classification, log evidence, and retrieved repository evidence.

## Architecture

```text
Public GitHub repository
          │
          ▼
 Temporary ingestion workspace
          │
          ▼
 Tree-sitter parsing and discovery
          │
          ├── File and symbol metadata
          ├── Import and call relationships
          ├── Symbol-aware code chunks
          └── Ephemeral local vector index
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
 Grounded chat     Diff analysis     CI analysis
          │              │              │
          └──── Explanations and bounded evidence ────┘
```

The backend is a FastAPI service. The frontend is a Next.js application using React Flow for graph visualization. Repository workspaces and indexes are stored locally in memory and expire automatically.

## Project structure

```text
apps/web/          Next.js frontend
services/api/      FastAPI backend
```

## Built with Codex and GPT-5.6

Codex was used as an engineering collaborator throughout the project rather than only as a code generator. We used it to inspect the evolving repository, translate the product proposal into an implementation plan, implement and test backend and frontend features, diagnose integration failures, review security boundaries, resolve Git collaboration issues, and keep the documentation aligned with the working product.

Codex accelerated:

- Temporary repository ingestion and workspace lifecycle design.
- Tree-sitter parsing across Python, JavaScript, TypeScript, and TSX.
- Symbol-aware chunking, dependency extraction, local retrieval, and graph data.
- GitHub ingestion and Next.js/FastAPI integration.
- Retrieval-grounded repository chat with file-and-line citations.
- Safe symbolic-link handling discovered while testing a real public repository.
- Pull-request diff analysis and CI/CD failure analysis workflows.
- Backend tests, frontend validation, debugging, and submission-readiness review.

The team made the key product and design decisions. These included focusing on the difficulty of navigating unfamiliar code, combining the original Feature Finder and AI Advisor into one clearer chat experience, keeping source evidence visible beneath generated answers, separating the dashboard into Explore, Ask, Review change, and Debug CI workflows, and prioritizing interactive architectural orientation.

GPT-5.6 powers the AI-enhanced portions through the OpenAI Responses API. The backend retrieves or constructs bounded evidence, sends it with the user’s request, and instructs the model to stay grounded in that evidence. Repository chat pairs generated explanations with exact retrieved paths, line ranges, and excerpts. Diff and CI analysis retain deterministic fallbacks and use AI to improve explanations when an API key is configured.

The collaboration was iterative: the team tested real repositories, identified confusing or incomplete experiences, made product decisions, and used Codex to implement and verify targeted improvements while preserving human control over scope and final decisions.

## Prerequisites

- Node.js 20 or newer
- Python 3.11 or newer
- npm
- Git
- An OpenAI API key with available API credits for AI-enhanced output

## Environment setup

From the repository root:

```bash
cp .env.example .env
```

Add your OpenAI API key to `.env`:

```env
OPENAI_API_KEY=your_api_key_here
```

The defaults expect the frontend at `http://localhost:3000` and API at `http://localhost:8000`. Never commit `.env`; it is ignored by Git.

## Run locally

### 1. Start the API

```bash
cd services/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Verify [http://localhost:8000/health](http://localhost:8000/health) returns:

```json
{"status":"ok"}
```

### 2. Start the web app

In a second terminal, from the repository root:

```bash
cd apps/web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Deploy for judging

The recommended demo deployment uses Vercel for the Next.js frontend and a
single Render web service for the FastAPI backend. Keep the API at one instance:
repository workspaces and indexes are temporary and stored in that process.

### 1. Deploy the API on Render

1. In Render, create a new **Blueprint** and connect this repository.
2. Render will read `render.yaml` and create `ctrl-why-api`.
3. Enter these secret environment variables when prompted:

   ```env
   OPENAI_API_KEY=your_api_key_here
   APP_CORS_ORIGINS=https://your-project.vercel.app
   ```

   You can initially use the expected Vercel URL and update it after the
   frontend has its final domain. Multiple allowed origins can be separated by
   commas.

4. Deploy and verify `https://your-api.onrender.com/health` returns
   `{"status":"ok"}`.

### 2. Deploy the frontend on Vercel

1. Import this repository as a new Vercel project.
2. Set **Root Directory** to `apps/web`. Vercel will detect Next.js.
3. Add the production environment variable:

   ```env
   NEXT_PUBLIC_API_URL=https://your-api.onrender.com
   ```

4. Deploy, then copy the final Vercel URL into the Render
   `APP_CORS_ORIGINS` value and redeploy the API if it changed.

### 3. Verify the public demo

From a private browser window, import a small public Python repository, open
the generated workspace, ask a repository question, and confirm the evidence
links expand.

## Using the product

1. Import a public GitHub repository.
2. Wait for ingestion, parsing, dependency extraction, and indexing.
3. Use **Explore** to inspect the overview and dependency graphs.
4. Use **Ask** for grounded repository questions and expand **Relevant code**.
5. Use **Review change** to paste a unified Git diff and inspect impact and risk.
6. Use **Debug CI** to paste failed pipeline output and connect it to likely source files.

The four views remain mounted while switching, so chat history and pasted analyses are preserved. Repository indexes are ephemeral; restart the import after restarting the API.

## Pull-request diff analysis

The MVP accepts pasted unified Git diffs. It maps changed lines to indexed symbols, finds dependent files, assigns a risk score, checks selected suspicious added-line patterns, and suggests tests. With `OPENAI_API_KEY`, the explanation is AI-enhanced from structured analysis and redacted added-line evidence.

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

Direct GitHub pull-request fetching is not implemented yet.

## CI/CD failure analysis

The CI Copilot classifies common test, type-check, lint, build, dependency, and configuration failures. It extracts relevant log lines, matches mentioned paths against the index, retrieves related code, and returns a likely cause, recommendations, and validation steps. Credential-shaped values are redacted before AI enhancement.

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

Direct GitHub Actions integration and automatic patch generation are not implemented yet.

## API endpoints

Interactive documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs) outside production.

```text
POST   /api/v1/repositories/github
POST   /api/v1/repositories/uploads
POST   /api/v1/repositories/{workspace_id}/parse
POST   /api/v1/repositories/{workspace_id}/index
GET    /api/v1/repositories/{workspace_id}/index
POST   /api/v1/repositories/{workspace_id}/search
POST   /api/v1/repositories/{workspace_id}/chat
POST   /api/v1/repositories/{workspace_id}/pull-request-analysis
POST   /api/v1/repositories/{workspace_id}/ci-analysis
GET    /api/v1/repositories/{workspace_id}
DELETE /api/v1/repositories/{workspace_id}
```

## Test and build

After installing both applications’ dependencies:

```bash
make test
make build
```

This runs the backend test suite, frontend TypeScript checks, and optimized Next.js production build.

## Security and privacy

- Only HTTPS GitHub URLs in the form `https://github.com/owner/repository` are accepted.
- Cloning is non-interactive, shallow, single-branch, and timeout-limited.
- Git metadata is removed after cloning.
- Symbolic links are removed from cloned repositories without following their targets.
- ZIP uploads reject unsafe paths and symbolic links.
- File-count, expanded-size, upload-size, and source-file-size limits protect temporary storage.
- Repository code is parsed as data and is never executed.
- Workspaces expire after one hour by default and are removed at API shutdown.
- Repository chat sends only retrieved source excerpts to OpenAI.
- CI evidence and added diff lines are redacted for common credential patterns before AI enhancement.

Use public repositories that you are comfortable sending to the configured AI provider. Private repository authentication is not supported.

## Current limitations

- The web interface imports public GitHub repositories only.
- Supported languages are Python, JavaScript, TypeScript, and TSX.
- Workspaces and indexes are in-memory and are not shared across API processes.
- Retrieval uses deterministic local feature hashing rather than hosted semantic embeddings.
- Static dependency analysis may miss dynamic dispatch, runtime imports, generated code, or framework-specific behavior.
- Citations display source paths and line ranges, but an integrated clickable code viewer is not implemented.
- Pull requests and CI logs must be pasted rather than fetched directly from GitHub.
- Automatic patches and merges are not implemented.

## Judge testing

The project is designed for current desktop browsers. Local development has been tested on macOS; the Node.js and Python services are also suitable for Linux environments with the listed prerequisites.

Judges can follow **Environment setup** and **Run locally**, or use the
[hosted demo](https://ctrl-why.vercel.app) without rebuilding the project.

No test account is required because the current product accepts public GitHub repositories. The hosted backend runs on Render's free tier, so the first request after a period of inactivity can take up to approximately one minute while the service wakes.

## Recommended demo flow

1. Import a small public Python or TypeScript repository and show the progress timeline.
2. In **Explore**, select a meaningful relationship in the graph.
3. In **Ask**, ask a repository-specific question and expand **Relevant code**.
4. In **Review change**, paste a real diff and show dependents, risk, tests, and evidence.
5. In **Debug CI**, paste a failed test log and compare log evidence with repository evidence.

Keep the required demonstration video under three minutes and include audio explaining both the product and how Codex and GPT-5.6 contributed.
