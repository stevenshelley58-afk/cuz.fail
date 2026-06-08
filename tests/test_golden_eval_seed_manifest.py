from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from draftcheck_core.database import Base
from draftcheck_core.bootstrap_sources import ensure_demo_source_library
from draftcheck_core.evals import GoldenEvalService
from draftcheck_core.json_utils import from_json, to_json
from draftcheck_core.models import GoldenEvalCase
from draftcheck_shared.schemas import GoldenEvalRunRequest
from scripts import run_golden_evals
from scripts.seed_golden_evals import load_case_payloads, seed_golden_eval_cases


def test_retrieval_golden_manifest_loads_and_upserts_idempotently():
    payloads = load_case_payloads(Path("tests/gold/retrieval_quality.json"))
    assert len(payloads) >= 3
    assert {payload.track for payload in payloads} == {"retrieval"}
    assert {
        "Allowed two storey house question needs property context",
        "Second storey addition question needs property context",
    }.issubset({payload.name for payload in payloads})

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        first = seed_golden_eval_cases(db, payloads)
        second = seed_golden_eval_cases(db, payloads)
        db.commit()

        cases = db.scalars(select(GoldenEvalCase)).all()

    assert first == {"created": len(payloads), "updated": 0, "total": len(payloads)}
    assert second == {"created": 0, "updated": len(payloads), "total": len(payloads)}
    assert len(cases) == len(payloads)
    assert all(from_json(case.expected_json, {}).get("status") for case in cases)


def test_golden_manifest_seed_updates_existing_case_with_same_input_when_name_changes():
    payload = load_case_payloads(Path("tests/gold/retrieval_quality.json"))[0]
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        db.add(
            GoldenEvalCase(
                track=payload.track,
                name="Old retrieval case name",
                input_json=to_json(payload.input),
                expected_json=to_json({"status": "unsupported"}),
                source_version_ids_json=to_json([]),
                is_active=True,
            )
        )
        db.flush()

        result = seed_golden_eval_cases(db, [payload])
        db.commit()

        cases = db.scalars(select(GoldenEvalCase)).all()

    assert result == {"created": 0, "updated": 1, "total": 1}
    assert len(cases) == 1
    assert cases[0].name == payload.name
    assert from_json(cases[0].expected_json, {}) == payload.expected


def test_retrieval_golden_manifest_passes_against_bootstrap_source_library():
    payloads = load_case_payloads(Path("tests/gold/retrieval_quality.json"))
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        ensure_demo_source_library(db)
        seed_golden_eval_cases(db, payloads)
        run = GoldenEvalService(db).run(GoldenEvalRunRequest(track="retrieval", run_by="test"))

    assert run.status == "passed"
    assert run.passed is True
    assert run.failed_count == 0
    assert run.metrics["release_gate_satisfied"] is True


def test_golden_eval_cli_exits_nonzero_when_release_gate_not_satisfied(monkeypatch, capsys):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    monkeypatch.setattr(run_golden_evals, "init_database", lambda: None)
    monkeypatch.setattr(run_golden_evals, "SessionLocal", session_factory)

    exit_code = run_golden_evals.main(["--track", "retrieval", "--run-by", "test", "--skip-seed-manifest"])

    assert exit_code == 1
    payload = from_json(capsys.readouterr().out, {})
    assert payload["status"] == "no_cases"
    assert payload["passed"] is False
    assert payload["metrics"]["release_gate_satisfied"] is False


def test_golden_eval_cli_seeds_manifest_before_running(monkeypatch, capsys):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    monkeypatch.setattr(run_golden_evals, "init_database", lambda: None)
    monkeypatch.setattr(run_golden_evals, "SessionLocal", session_factory)

    with Session(engine) as db:
        ensure_demo_source_library(db)
        db.commit()

    exit_code = run_golden_evals.main(
        [
            "--track",
            "retrieval",
            "--run-by",
            "test",
            "--seed-manifest",
            "tests/gold/retrieval_quality.json",
        ]
    )

    assert exit_code == 0
    payload = from_json(capsys.readouterr().out, {})
    assert payload["status"] == "passed"
    assert payload["case_count"] == len(load_case_payloads(Path("tests/gold/retrieval_quality.json")))
    assert payload["metrics"]["release_gate_satisfied"] is True
