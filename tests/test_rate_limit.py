from __future__ import annotations


def test_chat_endpoint_rate_limit_returns_429(client, monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")
    monkeypatch.setenv("RATE_LIMIT_CHAT_REQUESTS", "1")

    first = client.post(
        "/v1/chat",
        json={"message": "Front setback rules?"},
        headers={"x-forwarded-for": "203.0.113.10"},
    )
    second = client.post(
        "/v1/chat",
        json={"message": "Front setback rules?"},
        headers={"x-forwarded-for": "203.0.113.10"},
    )

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["code"] == "rate_limited"
    assert second.headers["retry-after"]


def test_rate_limit_can_be_disabled(client, monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
    monkeypatch.setenv("RATE_LIMIT_CHAT_REQUESTS", "1")

    first = client.post(
        "/v1/chat",
        json={"message": "Front setback rules?"},
        headers={"x-forwarded-for": "203.0.113.11"},
    )
    second = client.post(
        "/v1/chat",
        json={"message": "Front setback rules?"},
        headers={"x-forwarded-for": "203.0.113.11"},
    )

    assert first.status_code == 200
    assert second.status_code == 200


def test_rate_limit_uses_valid_api_key_tenant_bucket_before_proxy_ip(client, monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")
    monkeypatch.setenv("RATE_LIMIT_CHAT_REQUESTS", "1")
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv(
        "API_AUTH_KEYS",
        ",".join(
            [
                "tenant-a:abcdefghijklmnopqrstuvwxyz123456",
                "tenant-b:abcdefghijklmnopqrstuvwxyz654321",
            ]
        ),
    )

    tenant_a_first = client.post(
        "/v1/chat",
        json={"message": "Front setback rules?"},
        headers={
            "authorization": "Bearer abcdefghijklmnopqrstuvwxyz123456",
            "x-forwarded-for": "203.0.113.12",
        },
    )
    tenant_b_first = client.post(
        "/v1/chat",
        json={"message": "Front setback rules?"},
        headers={
            "authorization": "Bearer abcdefghijklmnopqrstuvwxyz654321",
            "x-forwarded-for": "203.0.113.12",
        },
    )
    tenant_a_second = client.post(
        "/v1/chat",
        json={"message": "Front setback rules?"},
        headers={
            "authorization": "Bearer abcdefghijklmnopqrstuvwxyz123456",
            "x-forwarded-for": "203.0.113.12",
        },
    )

    assert tenant_a_first.status_code == 200
    assert tenant_b_first.status_code == 200
    assert tenant_a_second.status_code == 429
    assert tenant_a_second.json()["code"] == "rate_limited"


def test_rate_limit_invalid_api_keys_share_client_ip_bucket(client, monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")
    monkeypatch.setenv("RATE_LIMIT_CHAT_REQUESTS", "1")
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("API_AUTH_KEYS", "tenant-a:abcdefghijklmnopqrstuvwxyz123456")

    first = client.post(
        "/v1/chat",
        json={"message": "Front setback rules?"},
        headers={
            "authorization": "Bearer invalid-key-one",
            "x-forwarded-for": "203.0.113.13",
        },
    )
    second = client.post(
        "/v1/chat",
        json={"message": "Front setback rules?"},
        headers={
            "authorization": "Bearer invalid-key-two",
            "x-forwarded-for": "203.0.113.13",
        },
    )

    assert first.status_code == 401
    assert second.status_code == 429
    assert second.json()["code"] == "rate_limited"
