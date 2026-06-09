PY ?= python

.PHONY: setup dev test lint typecheck migrate backup seed-eval \
        bootstrap-sources audit-sources extract-rules rule-worklist \
        reconcile-source-reviews seed worker

setup:
	$(PY) -m pip install -e ".[dev]"

dev:
	uvicorn draftcheck.api.main:app --reload --port 8000

test:
	pytest tests/ -x -q

lint:
	ruff check src/ tests/

typecheck:
	mypy src/draftcheck/ --ignore-missing-imports

migrate:
	alembic upgrade head

backup:
	bash scripts/backup_db.sh

seed-eval:
	$(PY) -c "from draftcheck.eval.seeds import seed_eval_cases; import asyncio; asyncio.run(seed_eval_cases())"

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
