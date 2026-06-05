from __future__ import annotations

from tests.test_compliance_rfi_export import create_project


def test_document_upload_and_plan_qa(client):
    project = create_project(client)
    doc = client.post(
        f"/v1/projects/{project['id']}/documents",
        json={
            "document_type": "site_plan",
            "title": "Site Plan A01",
            "filename": "A01.pdf",
            "content_type": "application/pdf",
            "text_content": "Title block Project Rev A Scale 1:100 North dimensions site coverage open space parking FFL NGL",
        },
    )
    assert doc.status_code == 200, doc.text
    pages = client.get(f"/v1/projects/{project['id']}/documents/{doc.json()['id']}/pages")
    assert pages.status_code == 200
    assert pages.json()[0]["page_number"] == 1
    assert "Title block" in pages.json()[0]["text_content"]

    analysis = client.post(f"/v1/projects/{project['id']}/documents/{doc.json()['id']}/analyze")
    assert analysis.status_code == 200, analysis.text
    results = analysis.json()
    assert len(results) >= 5
    assert all(result["requires_human_review"] for result in results)
    assert any(result["status"] == "needs_human_review" for result in results)


def test_multipart_document_upload_stores_raw_file_and_pages(client):
    project = create_project(client)
    response = client.post(
        f"/v1/projects/{project['id']}/documents/upload",
        data={"document_type": "council_rfi", "title": "Council RFI email"},
        files={"file": ("rfi.txt", b"1. Please confirm the front setback dimension.\f2. Provide a revised site plan.", "text/plain")},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["filename"] == "rfi.txt"
    assert body["raw_object_key"]
    assert body["parse_status"] == "ok"

    pages = client.get(f"/v1/projects/{project['id']}/documents/{body['id']}/pages")
    assert pages.status_code == 200
    assert [page["page_number"] for page in pages.json()] == [1, 2]
    assert "front setback" in pages.json()[0]["text_content"]


def test_document_fact_extraction_creates_measurements_and_search_chunks(client):
    project = create_project(client)
    doc = client.post(
        f"/v1/projects/{project['id']}/documents",
        json={
            "document_type": "site_plan",
            "title": "Measured Site Plan A01",
            "filename": "A01.pdf",
            "content_type": "application/pdf",
            "text_content": (
                "Title block Rev B Scale 1:100 North. "
                "Site area 500m2. Open space 220m2. Front setback 4.5m. "
                "Garage width 6000mm. Frontage width 12m. FFL 10.250"
            ),
        },
    )
    assert doc.status_code == 200, doc.text
    facts = client.get(f"/v1/projects/{project['id']}/documents/{doc.json()['id']}/facts")
    assert facts.status_code == 200
    labels = {fact["label"] for fact in facts.json()}
    assert {"site area", "open space", "front setback", "garage width", "frontage width"}.issubset(labels)

    measurements = client.get(f"/v1/projects/{project['id']}/measurements")
    assert measurements.status_code == 200
    measurement_values = {row["key"]: row["value"] for row in measurements.json()}
    assert measurement_values["site_area_m2"] == 500
    assert measurement_values["garage_width_m"] == 6
    assert measurement_values["scale_present"] == 1

    search = client.get(f"/v1/projects/{project['id']}/document-search?q=front+setback")
    assert search.status_code == 200
    assert search.json()
    assert "front setback" in search.json()[0]["text"].lower()
    assert search.json()[0]["evidence_ref"].startswith(f"document:{doc.json()['id']}:page:")


def test_document_fact_extraction_handles_pdf_units_and_commas(client):
    project = create_project(client)
    doc = client.post(
        f"/v1/projects/{project['id']}/documents",
        json={
            "document_type": "site_plan",
            "title": "PDF Extracted Site Plan A02",
            "filename": "A02.pdf",
            "content_type": "application/pdf",
            "text_content": (
                "SITE AREA: 1,002.5 m²\n"
                "OPEN SPACE: 245 sqm\n"
                "FRONT SETBACK: 4,500 mm\n"
                "OUTDOOR LIVING AREA: 30 square metres\n"
            ),
        },
    )
    assert doc.status_code == 200, doc.text

    measurements = client.get(f"/v1/projects/{project['id']}/measurements")
    assert measurements.status_code == 200
    values = {row["key"]: row["value"] for row in measurements.json()}
    assert values["site_area_m2"] == 1002.5
    assert values["open_space_m2"] == 245
    assert values["front_setback_m"] == 4.5
    assert values["outdoor_living_area_m2"] == 30


def test_dxf_upload_extracts_layers_text_and_is_searchable(client):
    project = create_project(client)
    dxf = "\n".join(
        [
            "0",
            "SECTION",
            "2",
            "ENTITIES",
            "0",
            "LINE",
            "8",
            "SETBACK",
            "10",
            "0",
            "20",
            "0",
            "11",
            "4500",
            "21",
            "0",
            "0",
            "TEXT",
            "8",
            "NOTES",
            "1",
            "Front setback 4.5m Garage width 6000mm",
            "0",
            "ENDSEC",
        ]
    ).encode()
    upload = client.post(
        f"/v1/projects/{project['id']}/documents/upload",
        data={"document_type": "cad_drawing", "title": "CAD Site Plan"},
        files={"file": ("site_plan.dxf", dxf, "application/dxf")},
    )
    assert upload.status_code == 200, upload.text
    pages = client.get(f"/v1/projects/{project['id']}/documents/{upload.json()['id']}/pages")
    assert pages.status_code == 200
    assert "DXF drawing extraction summary" in pages.json()[0]["text_content"]
    assert "Layers: NOTES, SETBACK" in pages.json()[0]["text_content"]

    facts = client.get(f"/v1/projects/{project['id']}/documents/{upload.json()['id']}/facts")
    assert facts.status_code == 200
    assert any(fact["label"] == "front setback" and fact["numeric_value"] == 4.5 for fact in facts.json())

    search = client.get(f"/v1/projects/{project['id']}/document-search?q=setback")
    assert search.status_code == 200
    assert search.json()
    assert "setback" in search.json()[0]["text"].lower()


def test_dxf_upload_extracts_declared_units_and_dimension_summaries(client):
    project = create_project(client)
    dxf = "\n".join(
        [
            "0",
            "SECTION",
            "2",
            "HEADER",
            "9",
            "$INSUNITS",
            "70",
            "4",
            "0",
            "ENDSEC",
            "0",
            "SECTION",
            "2",
            "ENTITIES",
            "0",
            "LINE",
            "8",
            "SETBACK",
            "10",
            "0",
            "20",
            "0",
            "11",
            "4500",
            "21",
            "0",
            "0",
            "DIMENSION",
            "8",
            "DIMS",
            "1",
            "Front setback dimension",
            "42",
            "4500",
            "0",
            "ENDSEC",
        ]
    ).encode()
    upload = client.post(
        f"/v1/projects/{project['id']}/documents/upload",
        data={"document_type": "cad_drawing", "title": "CAD Dimension Plan"},
        files={"file": ("dimension_plan.dxf", dxf, "application/dxf")},
    )
    assert upload.status_code == 200, upload.text

    pages = client.get(f"/v1/projects/{project['id']}/documents/{upload.json()['id']}/pages")
    assert pages.status_code == 200
    page_text = pages.json()[0]["text_content"]
    assert "DXF declared units: mm" in page_text
    assert "Line length on layer SETBACK: 4500mm" in page_text
    assert "Dimension measurement on layer DIMS: 4500mm" in page_text

    facts = client.get(f"/v1/projects/{project['id']}/documents/{upload.json()['id']}/facts")
    assert facts.status_code == 200
    dimension_facts = [fact for fact in facts.json() if fact["fact_type"] == "drawing_dimension"]
    assert any(fact["label"] == "line length" and fact["numeric_value"] == 4.5 for fact in dimension_facts)
    assert any(
        fact["label"] == "dimension measurement" and fact["numeric_value"] == 4.5
        for fact in dimension_facts
    )

    search = client.get(f"/v1/projects/{project['id']}/document-search?q=4500mm+SETBACK")
    assert search.status_code == 200
    assert search.json()


def test_hermes_disabled_job_status_and_traces(client):
    project = create_project(client)
    parse = client.post(
        f"/v1/projects/{project['id']}/rfi/parse",
        json={"text": "1. Please confirm the front setback dimension."},
    )
    assert parse.status_code == 200

    audit = client.get(f"/v1/audit?project_id={project['id']}").json()
    job_event = next(event for event in audit if event["action"] == "job.enqueued")
    job_id = job_event["target_id"]

    status = client.get(f"/v1/jobs/{job_id}")
    assert status.status_code == 200
    assert status.json()["status"] == "disabled"
    assert status.json()["provider"] == "local-disabled"

    traces = client.get(f"/v1/jobs/{job_id}/traces")
    assert traces.status_code == 200
    assert traces.json()
    assert traces.json()[0]["correlation_id"] == status.json()["correlation_id"]
