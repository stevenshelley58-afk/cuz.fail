from __future__ import annotations


TENANT_A = {"authorization": "Bearer key-a"}
TENANT_B = {"authorization": "Bearer key-b"}


def test_api_key_tenants_scope_project_access(client, monkeypatch):
    _enable_tenant_auth(monkeypatch)

    created = client.post(
        "/v1/projects",
        headers=TENANT_A,
        json={
            "project_name": "Tenant A project",
            "address": "1 Tenant Street, Perth WA",
            "local_government": "Perth",
            "project_type": "single_house",
            "stage": "design",
            "created_by": "spoofed-user",
        },
    )

    assert created.status_code == 200, created.text
    project = created.json()
    assert project["created_by"] == "tenant-a"

    tenant_a_projects = client.get("/v1/projects", headers=TENANT_A)
    assert tenant_a_projects.status_code == 200
    assert [row["id"] for row in tenant_a_projects.json()] == [project["id"]]

    tenant_b_projects = client.get("/v1/projects", headers=TENANT_B)
    assert tenant_b_projects.status_code == 200
    assert tenant_b_projects.json() == []

    tenant_b_project = client.get(f"/v1/projects/{project['id']}", headers=TENANT_B)
    assert tenant_b_project.status_code == 404
    assert tenant_b_project.json()["code"] == "not_found"


def test_api_key_tenants_scope_nested_project_routes(client, monkeypatch):
    _enable_tenant_auth(monkeypatch)
    project = _create_project(client, TENANT_A)

    tenant_a_chat = client.post(
        f"/v1/projects/{project['id']}/chat",
        headers=TENANT_A,
        json={"message": "What is the site cover requirement for R30?"},
    )
    assert tenant_a_chat.status_code == 200, tenant_a_chat.text

    tenant_b_chat = client.post(
        f"/v1/projects/{project['id']}/chat",
        headers=TENANT_B,
        json={"message": "What is the site cover requirement for R30?"},
    )
    assert tenant_b_chat.status_code == 404

    tenant_b_export = client.get(
        f"/v1/projects/{project['id']}/exports/not-real",
        headers=TENANT_B,
    )
    assert tenant_b_export.status_code == 404

    tenant_b_signoffs = client.get(f"/v1/projects/{project['id']}/signoffs", headers=TENANT_B)
    assert tenant_b_signoffs.status_code == 404


def test_api_key_tenants_scope_review_queues_and_audit(client, monkeypatch):
    _enable_tenant_auth(monkeypatch)
    project = _create_project(client, TENANT_A)

    queue_item = client.post(
        "/v1/review-queues",
        headers=TENANT_A,
        json={
            "queue": "source_review",
            "project_id": project["id"],
            "target_type": "project",
            "target_id": project["id"],
            "reason": "Tenant scoped review item",
            "suggested_action": "Review tenant-specific project evidence.",
        },
    )
    assert queue_item.status_code == 200, queue_item.text

    tenant_a_queue = client.get("/v1/review-queues", headers=TENANT_A)
    assert tenant_a_queue.status_code == 200
    assert [item["id"] for item in tenant_a_queue.json()] == [queue_item.json()["id"]]

    tenant_b_queue = client.get("/v1/review-queues", headers=TENANT_B)
    assert tenant_b_queue.status_code == 200
    assert tenant_b_queue.json() == []

    tenant_b_update = client.patch(
        f"/v1/review-queues/{queue_item.json()['id']}",
        headers=TENANT_B,
        json={"status": "resolved", "reviewed_by": "tenant-b"},
    )
    assert tenant_b_update.status_code == 404

    tenant_a_audit = client.get("/v1/audit", headers=TENANT_A)
    assert tenant_a_audit.status_code == 200
    assert {event["project_id"] for event in tenant_a_audit.json()} == {project["id"]}

    tenant_b_audit = client.get("/v1/audit", headers=TENANT_B)
    assert tenant_b_audit.status_code == 200
    assert tenant_b_audit.json() == []


def _enable_tenant_auth(monkeypatch) -> None:
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("API_AUTH_KEYS", "tenant-a:key-a,tenant-b:key-b")


def _create_project(client, headers: dict[str, str]) -> dict:
    response = client.post(
        "/v1/projects",
        headers=headers,
        json={
            "project_name": "Tenant scoped project",
            "address": "1 Tenant Street, Perth WA",
            "local_government": "Perth",
            "project_type": "single_house",
            "stage": "design",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()
