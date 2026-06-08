from __future__ import annotations

import importlib


def test_v3_hermes_and_cockburn_monitor_tasks_are_governed(
    monkeypatch,
) -> None:
    monkeypatch.setenv("PROCRASTINATE_DB_URI", "postgresql://fixture:fixture@localhost/fixture")
    jobs = importlib.import_module("draftcheck.jobs")

    hermes = jobs.hermes_governance_canary()
    monitor = jobs.cockburn_source_monitor()

    assert hermes["status"] == "ok"
    assert hermes["trace_required"] is True
    assert hermes["skill_version_required"] is True
    assert hermes["spend_capped"] is True
    assert "compliance verdicts" in hermes["forbidden_outputs"]
    assert monitor["status"] == "monitoring"
    assert monitor["local_government"] == "City of Cockburn"
    assert monitor["canary_address"] == "3 Black Swan Rise, Beeliar WA 6164"
    assert monitor["policy"] == "cite_or_refuse"
