from __future__ import annotations

from io import BytesIO

from docx import Document

from tests.test_sources_retrieval import seed_source


def create_project(client):
    response = client.post(
        "/v1/projects",
        json={
            "project_name": "Example RFI job",
            "address": "1 Example Street, Spearwood WA",
            "local_government": "Cockburn",
            "lot_plan": "Lot 1 on P12345",
            "project_type": "single_house_addition",
            "stage": "RFI",
            "r_code_density": "R30",
            "ncc_edition": "NCC 2022",
            "created_by": "tester",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def add_measurements(client, project_id):
    for payload in [
        {"key": "site_area_m2", "value": 500, "unit": "m2"},
        {"key": "building_footprint_m2", "value": 250, "unit": "m2"},
        {"key": "open_space_m2", "value": 200, "unit": "m2"},
        {"key": "front_setback_m", "value": 3.5, "unit": "m"},
        {"key": "garage_width_m", "value": 6, "unit": "m"},
        {"key": "frontage_width_m", "value": 12, "unit": "m"},
    ]:
        response = client.post(f"/v1/projects/{project_id}/measurements", json=payload)
        assert response.status_code == 200, response.text


def test_compliance_matrix_uses_deterministic_calculations_and_citations(client):
    seed_source(client)
    project = create_project(client)
    add_measurements(client, project["id"])

    response = client.post(f"/v1/projects/{project['id']}/checks/run")
    assert response.status_code == 200, response.text
    matrix = response.json()
    assert matrix["liability_notice"].startswith("Assistive drafting review only")
    statuses = {row["check_key"]: row["status"] for row in matrix["results"]}
    assert statuses["site_cover"] == "likely_pass"
    assert statuses["open_space"] == "likely_fail"
    assert statuses["front_setback"] == "likely_fail"
    assert statuses["garage_dominance"] == "likely_pass"
    assert all(row["requires_human_review"] for row in matrix["results"])
    cited = [row for row in matrix["results"] if row["citations"]]
    assert cited, "At least one compliance result should cite the approved source library"


def test_compliance_matrix_covers_requested_check_pack_and_missing_info(client):
    seed_source(client)
    project = create_project(client)

    response = client.post(f"/v1/projects/{project['id']}/checks/run")
    assert response.status_code == 200, response.text
    rows = response.json()["results"]
    statuses = {row["check_key"]: row["status"] for row in rows}
    required_keys = {
        "front_setback",
        "side_setback",
        "rear_setback",
        "site_cover",
        "open_space",
        "deep_soil_tree_planting",
        "garage_dominance",
        "street_surveillance",
        "outdoor_living_area",
        "solar_access",
        "privacy",
        "overshadowing",
        "vehicle_access",
        "bin_storage",
        "ancillary_dwelling_trigger",
        "retaining_fill_trigger",
        "bal_bushfire_trigger",
        "heritage_overlay_trigger",
        "boundary_wall",
        "title_block_completeness",
        "revision_completeness",
        "north_point_completeness",
        "scale_completeness",
        "dimension_completeness",
    }
    assert required_keys.issubset(statuses.keys())
    assert statuses["side_setback"] == "missing_info"
    assert statuses["bal_bushfire_trigger"] == "missing_info"


def test_rfi_response_export_and_audit_traceability(client):
    seed_source(client)
    project = create_project(client)
    rfi = client.post(
        f"/v1/projects/{project['id']}/rfi/parse",
        json={
            "text": "\n".join(
                [
                    "1. Could the garage be reoriented to reduce dominance and improve passive surveillance on A05?",
                    "2. Please confirm the front setback dimension and update the site plan.",
                ]
            )
        },
    )
    assert rfi.status_code == 200, rfi.text
    assert len(rfi.json()) == 2
    assert rfi.json()[0]["source_requirement_candidates"]

    draft = client.post(f"/v1/projects/{project['id']}/rfi/draft-response")
    assert draft.status_code == 200, draft.text
    draft_body = draft.json()
    assert "does not assert final compliance" in draft_body["draft_text"]
    assert draft_body["requires_human_review"] is True
    assert draft_body["liability_notice"].startswith("Draft only")

    export = client.post(
        f"/v1/projects/{project['id']}/exports",
        json={"format": "json", "sections": ["rfi_items", "rfi_response", "source_list"], "created_by": "tester"},
    )
    assert export.status_code == 200, export.text
    assert export.json()["file_sha256"]
    manifest = client.get(f"/v1/projects/{project['id']}/exports/{export.json()['id']}")
    assert manifest.status_code == 200
    assert manifest.json()["id"] == export.json()["id"]
    download = client.get(f"/v1/projects/{project['id']}/exports/{export.json()['id']}/download")
    assert download.status_code == 200
    assert download.headers["x-draftcheck-export-id"] == export.json()["id"]
    assert download.headers["content-type"].startswith("application/json")
    assert download.json()["requires_human_signoff"] is True

    audit = client.get(f"/v1/audit?project_id={project['id']}")
    assert audit.status_code == 200
    actions = {event["action"] for event in audit.json()}
    assert {"project.created", "rfi.parsed", "response_draft.generated", "export.created"}.issubset(actions)

    jobs = [event for event in audit.json() if event["action"] == "job.enqueued"]
    assert jobs, "Hermes adapter should create traceable disabled jobs locally"


def test_docx_export_download_returns_word_file(client):
    project = create_project(client)
    client.post(
        f"/v1/projects/{project['id']}/rfi/parse",
        json={"text": "1. Please confirm the front setback dimension."},
    )
    client.post(f"/v1/projects/{project['id']}/rfi/draft-response")
    export = client.post(
        f"/v1/projects/{project['id']}/exports",
        json={"format": "docx", "sections": ["rfi_response"], "created_by": "tester"},
    )
    assert export.status_code == 200, export.text
    download = client.get(f"/v1/projects/{project['id']}/exports/{export.json()['id']}/download")
    assert download.status_code == 200
    assert download.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    document = Document(BytesIO(download.content))
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    assert "DraftCheck WA Response Pack" in text
    assert "Human Signoff" in text
