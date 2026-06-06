# SnapPlate - dev shortcuts.
#
# Architecture: the DATA LAYER (Postgres + MinIO) runs in Docker; the BACKEND
# (FastAPI) runs on the host; the FRONTEND (Next.js) runs on the host.
#
# QUICK START:
#   1)  make up            # start Postgres + MinIO (Docker), wait for healthy
#   2)  make db-migrate    # apply migrations (first run / after model changes)
#   3a) make run-backend   # FastAPI on http://localhost:8000
#   3b) make run-frontend  # Next.js on http://localhost:3000

BACKEND_DIR = backend
ALGORITHM_DIR = algorithm
FRONTEND_DIR = frontend
# Sibling algorithm project on PYTHONPATH so backend imports algorithm.*.
BACKEND_ALGORITHM_PATH = ../$(ALGORITHM_DIR)
PY = PYTHONPATH=$(BACKEND_ALGORITHM_PATH) .venv/bin/python
ALEMBIC = PYTHONPATH=$(BACKEND_ALGORITHM_PATH) .venv/bin/alembic

.DEFAULT_GOAL := help

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  %-22s %s\n", $$1, $$2}'

# Data layer (Docker: Postgres + MinIO)
up:  ## Start Postgres + MinIO in Docker (detached) and wait until healthy
	cd $(BACKEND_DIR) && docker compose up -d
	@echo "waiting for Postgres to be healthy..."
	@until [ "$$(docker inspect --format '{{.State.Health.Status}}' snapplate-pg 2>/dev/null)" = "healthy" ]; do sleep 1; done
	@echo "data layer up - Postgres :5432, MinIO :9000 (console :9001)"

down:  ## Stop the data-layer containers (keeps volumes)
	cd $(BACKEND_DIR) && docker compose down

reset-db:  ## Drop the data-layer volumes (wipes all local data) and restart fresh
	cd $(BACKEND_DIR) && docker compose down -v && rm -rf pg-volume minio-volume
	$(MAKE) up

# Backend (FastAPI on the host)
install:  ## Install algorithm + backend deps into backend/.venv
	cd $(BACKEND_DIR) && .venv/bin/python -m pip install -e ../$(ALGORITHM_DIR)
	cd $(BACKEND_DIR) && .venv/bin/python -m pip install -e .

run-backend:  ## Run FastAPI (host) with reload on http://localhost:8000
	cd $(BACKEND_DIR) && $(PY) -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend (Next.js on the host)
frontend-install:  ## Install frontend deps (npm)
	cd $(FRONTEND_DIR) && npm install

run-frontend:  ## Run Next.js dev server on http://localhost:3000
	cd $(FRONTEND_DIR) && npm run dev

# Full stack (one shot)
dev:  ## Bring up the data layer + migrate, then print how to start the apps
	$(MAKE) up
	$(MAKE) db-migrate
	@echo ""
	@echo "Data layer ready + migrated. Now in two terminals:"
	@echo "  make run-backend    # http://localhost:8000"
	@echo "  make run-frontend   # http://localhost:3000"

# Database migrations (Alembic)
db-migrate:  ## Apply all migrations (alembic upgrade head)
	cd $(BACKEND_DIR) && $(ALEMBIC) upgrade head

db-rollback:  ## Roll back the last migration
	cd $(BACKEND_DIR) && $(ALEMBIC) downgrade -1

# Quality + tests
lint:  ## ruff check + format check
	cd $(BACKEND_DIR) && ruff check app && ruff format --check app

format:  ## ruff format + autofix
	cd $(BACKEND_DIR) && ruff format app && ruff check --fix app

typecheck:  ## pyright
	cd $(BACKEND_DIR) && pyright app

test-algorithm:  ## Run the algorithm pytest suite
	cd $(ALGORITHM_DIR) && uv run pytest tests/ -q

test:  ## Run the backend pytest suite (needs `make up` first)
	cd $(BACKEND_DIR) && $(PY) -m pytest tests/ -q

test-all: test-algorithm test  ## Run algorithm + backend pytest suites

.PHONY: help up down reset-db install run-backend frontend-install run-frontend \
	dev db-migrate db-rollback lint format typecheck test-algorithm test test-all
