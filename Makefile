.PHONY: api web test build

api:
	cd services/api && .venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

web:
	cd apps/web && npm run dev

test:
	cd services/api && .venv/bin/python -m pytest
	cd apps/web && npm run typecheck

build:
	cd apps/web && npm run build

