PY ?= python

.PHONY: setup dev test lint migrate bootstrap-sources audit-sources extract-rules rule-worklist reconcile-source-reviews seed worker

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

bootstrap-sources:
	$(PY) scripts/bootstrap_source_library.py

audit-sources:
	$(PY) scripts/audit_source_library.py

extract-rules:
	$(PY) scripts/extract_source_rules.py --all --limit 10

rule-worklist:
	$(PY) scripts/rule_review_worklist.py --source-title-contains "Residential Design Codes" --limit 5

reconcile-source-reviews:
	$(PY) scripts/reconcile_source_review_queue.py --source-title-contains "Residential Design Codes"

seed:
	$(PY) scripts/seed_example.py

worker:
	$(PY) -m draftcheck_worker.main
