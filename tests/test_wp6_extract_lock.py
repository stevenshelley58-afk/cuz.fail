from scripts.wp6_extract import advisory_lock_key, build_endpoints, llm_retry_delays, write_report


def clear_endpoint_env(monkeypatch) -> None:
    for name in (
        "WP6_KIMI_API_KEY",
        "MOONSHOT_API_KEY",
        "KIMI_API_KEY",
        "WP6_KIMI_MODEL",
        "WP6_KIMI_BASE_URL",
        "WP6_KIMI_THINKING",
        "ANTHROPIC_API_KEY",
        "WP6_ANTHROPIC_MODEL",
        "OPENAI_API_KEY",
        "OPENROUTER_API_KEY",
        "MINIMAX_API_KEY",
        "WP6_ENABLE_CLAUDE_CLI",
        "WP6_FORCE_OPENAI_ENSEMBLE",
        "WP6_ALLOW_OPENAI",
    ):
        monkeypatch.delenv(name, raising=False)


def test_advisory_lock_key_is_stable_signed_63_bit() -> None:
    key = advisory_lock_key("1a3a1c37-879c-499f-821e-a1c3f02c7bc9")

    assert key == advisory_lock_key("1a3a1c37-879c-499f-821e-a1c3f02c7bc9")
    assert 0 <= key < 2**63


def test_build_endpoints_can_force_openai_fallback(monkeypatch) -> None:
    clear_endpoint_env(monkeypatch)
    monkeypatch.setenv("WP6_FORCE_OPENAI_ENSEMBLE", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    endpoints, escalations = build_endpoints()

    assert [endpoint.name for endpoint in endpoints] == ["openai", "openai", "openai"]
    assert endpoints[0].model == "gpt-4o-mini"
    assert endpoints[2].model == "gpt-4o"
    assert escalations


def test_build_endpoints_can_opt_into_claude_cli_fallback(monkeypatch) -> None:
    clear_endpoint_env(monkeypatch)
    monkeypatch.setenv("WP6_ENABLE_CLAUDE_CLI", "1")
    monkeypatch.setenv("WP6_CLAUDE_CLI_MODEL", "sonnet")

    endpoints, escalations = build_endpoints()

    assert [endpoint.name for endpoint in endpoints] == ["claude_cli", "claude_cli", "claude_cli"]
    assert endpoints[0].model == "sonnet"
    assert escalations


def test_build_endpoints_prefers_kimi_with_independent_anthropic(monkeypatch) -> None:
    clear_endpoint_env(monkeypatch)
    monkeypatch.setenv("WP6_KIMI_API_KEY", "kimi-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-key")
    monkeypatch.setenv("WP6_ANTHROPIC_MODEL", "claude-test")

    endpoints, escalations = build_endpoints()

    assert [endpoint.name for endpoint in endpoints] == ["kimi", "kimi", "anthropic"]
    assert endpoints[0].model == "kimi-k2.6"
    assert endpoints[0].temperature is None
    assert endpoints[0].extra_body == {"thinking": {"type": "disabled"}}
    assert endpoints[2].model == "claude-test"
    assert escalations


def test_build_endpoints_keeps_kimi_only_single_family(monkeypatch) -> None:
    clear_endpoint_env(monkeypatch)
    monkeypatch.setenv("MOONSHOT_API_KEY", "kimi-key")
    monkeypatch.setenv("WP6_KIMI_MODEL", "kimi-k2.7-code")

    endpoints, escalations = build_endpoints()

    assert [endpoint.name for endpoint in endpoints] == ["kimi", "kimi", "kimi"]
    assert endpoints[0].model == "kimi-k2.7-code"
    assert endpoints[0].temperature is None
    assert endpoints[0].extra_body == {}
    assert "without a second model family" in " ".join(escalations)


def test_build_endpoints_can_use_anthropic_only_as_candidate_fallback(monkeypatch) -> None:
    clear_endpoint_env(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-key")
    monkeypatch.setenv("WP6_ANTHROPIC_MODEL", "claude-test")

    endpoints, escalations = build_endpoints()

    assert [endpoint.name for endpoint in endpoints] == ["anthropic", "anthropic", "anthropic"]
    assert endpoints[0].model == "claude-test"
    assert "fallback only" in " ".join(escalations)


def test_write_report_creates_parent_directory(tmp_path) -> None:
    report_path = tmp_path / "reports" / "wp6.json"

    write_report(str(report_path), '{"ok": true}')

    assert report_path.read_text(encoding="utf-8") == '{"ok": true}'


def test_llm_retry_delays_ignores_invalid_values(monkeypatch) -> None:
    monkeypatch.setenv("WP6_LLM_RETRY_DELAYS", "0, nope, 2.5, -1")

    assert llm_retry_delays() == (0.0, 2.5)
