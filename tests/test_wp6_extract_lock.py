from scripts.wp6_extract import advisory_lock_key, build_endpoints, write_report


def test_advisory_lock_key_is_stable_signed_63_bit() -> None:
    key = advisory_lock_key("1a3a1c37-879c-499f-821e-a1c3f02c7bc9")

    assert key == advisory_lock_key("1a3a1c37-879c-499f-821e-a1c3f02c7bc9")
    assert 0 <= key < 2**63


def test_build_endpoints_can_force_openai_fallback(monkeypatch) -> None:
    monkeypatch.setenv("WP6_FORCE_OPENAI_ENSEMBLE", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    endpoints, escalations = build_endpoints()

    assert [endpoint.name for endpoint in endpoints] == ["openai_mini", "openai_mini", "openai_frontier"]
    assert endpoints[0].model == "gpt-4o-mini"
    assert endpoints[2].model == "gpt-4o"
    assert escalations


def test_write_report_creates_parent_directory(tmp_path) -> None:
    report_path = tmp_path / "reports" / "wp6.json"

    write_report(str(report_path), '{"ok": true}')

    assert report_path.read_text(encoding="utf-8") == '{"ok": true}'
