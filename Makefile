.PHONY: install run tui api web web-build test lint

install:
	uv sync

run:
	uv run python -m headofsocial.tui.app

tui:
	uv run python -m headofsocial.tui.app

api:
	uv run uvicorn headofsocial.api.app:app --reload --port 8080

# Web dashboard: FastAPI on :8080 + Vite dev server on :5173 (proxies /api).
web:
	uv run uvicorn headofsocial.api.app:app --reload --port 8080 & \
	cd web && npm run dev

# Build the SPA; FastAPI serves it at /app (see api/app.py static mount).
web-build:
	cd web && npm install && npm run build

test:
	uv run pytest

lint:
	uv run ruff check .
