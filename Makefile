PY ?= python

.PHONY: setup dev test lint migrate seed worker

setup:
	$(PY) -m pip install -e ".[dev]"

dev:
	$(PY) -m uvicorn draftcheck_api.main:app --reload --host 127.0.0.1 --port 8000

test:
	$(PY) -m pytest

lint:
	$(PY) -m ruff check .

typecheck:
	$(PY) -m mypy apps packages

migrate:
	$(PY) -c "from draftcheck_core.database import init_database; init_database()"

seed:
	$(PY) scripts/seed_example.py

worker:
	$(PY) -m draftcheck_worker.main
