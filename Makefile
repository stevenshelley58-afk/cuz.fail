PY ?= python

.PHONY: setup dev test lint typecheck migrate worker

setup:
	$(PY) -m pip install -e ".[dev]"

dev:
	$(PY) -m uvicorn draftcheck.api.main:app --reload --host 127.0.0.1 --port 8000

test:
	$(PY) -m pytest

lint:
	$(PY) -m ruff check .

typecheck:
	$(PY) -m mypy src tests/test_v3_api_shell.py

migrate:
	$(PY) -m alembic upgrade head

worker:
	$(PY) -m procrastinate --app draftcheck.jobs.procrastinate_app worker --queues default,source_ingestion,council_pack,rfi_analysis,source_freshness_audit
