-- DraftCheck WA Core initial schema for Supabase Postgres.

-- Generated from SQLAlchemy metadata; keep Alembic revision in sync.


CREATE TABLE audit_events (
	id VARCHAR NOT NULL, 
	actor_id VARCHAR NOT NULL, 
	project_id VARCHAR, 
	action VARCHAR NOT NULL, 
	target_type VARCHAR NOT NULL, 
	target_id VARCHAR NOT NULL, 
	metadata_json TEXT NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);


CREATE TABLE background_jobs (
	id VARCHAR NOT NULL, 
	job_type VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	correlation_id VARCHAR NOT NULL, 
	project_id VARCHAR, 
	source_version_id VARCHAR, 
	provider VARCHAR NOT NULL, 
	model VARCHAR, 
	payload_json TEXT NOT NULL, 
	remote_job_id VARCHAR, 
	error TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);


CREATE TABLE check_definitions (
	id VARCHAR NOT NULL, 
	key VARCHAR NOT NULL, 
	label VARCHAR NOT NULL, 
	category VARCHAR NOT NULL, 
	method VARCHAR NOT NULL, 
	requirement_json TEXT NOT NULL, 
	source_query VARCHAR NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (key)
);


CREATE TABLE local_governments (
	id VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	website_url VARCHAR, 
	planning_scheme_url VARCHAR, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);


CREATE TABLE organisations (
	id VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);


CREATE TABLE source_documents (
	id VARCHAR NOT NULL, 
	title VARCHAR NOT NULL, 
	jurisdiction VARCHAR NOT NULL, 
	authority VARCHAR NOT NULL, 
	local_government VARCHAR, 
	source_type VARCHAR NOT NULL, 
	canonical_url VARCHAR, 
	licence_notes TEXT NOT NULL, 
	access_type VARCHAR NOT NULL, 
	scrape_allowed BOOLEAN NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);


CREATE TABLE users (
	id VARCHAR NOT NULL, 
	email VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	role VARCHAR NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (email)
);


CREATE TABLE job_traces (
	id VARCHAR NOT NULL, 
	job_id VARCHAR NOT NULL, 
	correlation_id VARCHAR NOT NULL, 
	project_id VARCHAR, 
	source_version_id VARCHAR, 
	prompt TEXT NOT NULL, 
	model VARCHAR, 
	provider VARCHAR NOT NULL, 
	input_tokens INTEGER, 
	output_tokens INTEGER, 
	cost FLOAT, 
	status VARCHAR NOT NULL, 
	started_at TIMESTAMP WITHOUT TIME ZONE, 
	finished_at TIMESTAMP WITHOUT TIME ZONE, 
	error TEXT, 
	artifacts_json TEXT NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(job_id) REFERENCES background_jobs (id)
);


CREATE TABLE projects (
	id VARCHAR NOT NULL, 
	organisation_id VARCHAR, 
	project_name VARCHAR NOT NULL, 
	client_name VARCHAR, 
	address VARCHAR NOT NULL, 
	local_government VARCHAR NOT NULL, 
	lot_plan VARCHAR, 
	project_type VARCHAR NOT NULL, 
	stage VARCHAR NOT NULL, 
	r_code_density VARCHAR, 
	ncc_edition VARCHAR, 
	status VARCHAR NOT NULL, 
	created_by VARCHAR NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organisation_id) REFERENCES organisations (id)
);


CREATE TABLE source_fetch_logs (
	id VARCHAR NOT NULL, 
	source_document_id VARCHAR, 
	url VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	http_status INTEGER, 
	error_message TEXT, 
	retrieved_at TIMESTAMP WITHOUT TIME ZONE, 
	content_sha256 VARCHAR, 
	metadata_json TEXT NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(source_document_id) REFERENCES source_documents (id)
);


CREATE TABLE source_update_events (
	id VARCHAR NOT NULL, 
	source_document_id VARCHAR NOT NULL, 
	event_type VARCHAR NOT NULL, 
	notes TEXT NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(source_document_id) REFERENCES source_documents (id)
);


CREATE TABLE source_versions (
	id VARCHAR NOT NULL, 
	source_document_id VARCHAR NOT NULL, 
	version_label VARCHAR, 
	effective_date VARCHAR, 
	published_date VARCHAR, 
	retrieved_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	content_sha256 VARCHAR NOT NULL, 
	raw_object_key VARCHAR, 
	parsed_object_key VARCHAR, 
	superseded_by_id VARCHAR, 
	is_superseded BOOLEAN NOT NULL, 
	parse_status VARCHAR NOT NULL, 
	raw_text TEXT NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (source_document_id, content_sha256), 
	FOREIGN KEY(source_document_id) REFERENCES source_documents (id), 
	FOREIGN KEY(superseded_by_id) REFERENCES source_versions (id)
);


CREATE TABLE assumptions (
	id VARCHAR NOT NULL, 
	project_id VARCHAR NOT NULL, 
	text TEXT NOT NULL, 
	source VARCHAR NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(project_id) REFERENCES projects (id)
);


CREATE TABLE check_runs (
	id VARCHAR NOT NULL, 
	project_id VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	ruleset_version VARCHAR NOT NULL, 
	source_version_ids_json TEXT NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(project_id) REFERENCES projects (id)
);


CREATE TABLE clauses (
	id VARCHAR NOT NULL, 
	source_version_id VARCHAR NOT NULL, 
	clause_id VARCHAR NOT NULL, 
	heading VARCHAR, 
	parent_clause_id VARCHAR, 
	page_number INTEGER, 
	text TEXT NOT NULL, 
	normalized_text TEXT NOT NULL, 
	start_anchor VARCHAR NOT NULL, 
	end_anchor VARCHAR, 
	text_sha256 VARCHAR NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(source_version_id) REFERENCES source_versions (id)
);


CREATE TABLE exports (
	id VARCHAR NOT NULL, 
	project_id VARCHAR NOT NULL, 
	export_type VARCHAR NOT NULL, 
	format VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	object_key VARCHAR, 
	file_sha256 VARCHAR, 
	manifest_json TEXT NOT NULL, 
	created_by VARCHAR NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(project_id) REFERENCES projects (id)
);


CREATE TABLE extracted_measurements (
	id VARCHAR NOT NULL, 
	project_id VARCHAR NOT NULL, 
	key VARCHAR NOT NULL, 
	value FLOAT NOT NULL, 
	unit VARCHAR NOT NULL, 
	source VARCHAR NOT NULL, 
	confidence FLOAT NOT NULL, 
	evidence_ref VARCHAR, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(project_id) REFERENCES projects (id)
);


CREATE TABLE human_signoffs (
	id VARCHAR NOT NULL, 
	project_id VARCHAR NOT NULL, 
	target_type VARCHAR NOT NULL, 
	target_id VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	signed_by VARCHAR NOT NULL, 
	notes TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(project_id) REFERENCES projects (id)
);


CREATE TABLE planning_overlays (
	id VARCHAR NOT NULL, 
	project_id VARCHAR NOT NULL, 
	overlay_type VARCHAR NOT NULL, 
	label VARCHAR NOT NULL, 
	source_url VARCHAR, 
	detected_by VARCHAR NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(project_id) REFERENCES projects (id)
);


CREATE TABLE project_documents (
	id VARCHAR NOT NULL, 
	project_id VARCHAR NOT NULL, 
	document_type VARCHAR NOT NULL, 
	title VARCHAR NOT NULL, 
	filename VARCHAR, 
	content_type VARCHAR NOT NULL, 
	raw_object_key VARCHAR, 
	text_content TEXT NOT NULL, 
	content_sha256 VARCHAR, 
	parse_status VARCHAR NOT NULL, 
	analysis_status VARCHAR NOT NULL, 
	metadata_json TEXT NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(project_id) REFERENCES projects (id)
);


CREATE TABLE properties (
	id VARCHAR NOT NULL, 
	project_id VARCHAR NOT NULL, 
	address VARCHAR NOT NULL, 
	zoning VARCHAR, 
	lot_area_m2 FLOAT, 
	overlays_json TEXT NOT NULL, 
	planning_scheme VARCHAR, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (project_id), 
	FOREIGN KEY(project_id) REFERENCES projects (id)
);


CREATE TABLE response_drafts (
	id VARCHAR NOT NULL, 
	project_id VARCHAR NOT NULL, 
	title VARCHAR NOT NULL, 
	draft_text TEXT NOT NULL, 
	content_json TEXT NOT NULL, 
	confidence FLOAT NOT NULL, 
	assumptions_json TEXT NOT NULL, 
	missing_information_json TEXT NOT NULL, 
	citations_json TEXT NOT NULL, 
	created_by_model VARCHAR NOT NULL, 
	prompt_version VARCHAR NOT NULL, 
	requires_human_review BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(project_id) REFERENCES projects (id)
);


CREATE TABLE check_results (
	id VARCHAR NOT NULL, 
	check_run_id VARCHAR, 
	project_id VARCHAR NOT NULL, 
	check_key VARCHAR NOT NULL, 
	label VARCHAR NOT NULL, 
	category VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	requirement TEXT NOT NULL, 
	proposed TEXT NOT NULL, 
	evidence_refs_json TEXT NOT NULL, 
	citations_json TEXT NOT NULL, 
	assumptions_json TEXT NOT NULL, 
	missing_information_json TEXT NOT NULL, 
	confidence FLOAT NOT NULL, 
	requires_human_review BOOLEAN NOT NULL, 
	created_by_model VARCHAR NOT NULL, 
	prompt_version VARCHAR NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(check_run_id) REFERENCES check_runs (id), 
	FOREIGN KEY(project_id) REFERENCES projects (id)
);


CREATE TABLE document_assets (
	id VARCHAR NOT NULL, 
	document_id VARCHAR NOT NULL, 
	asset_type VARCHAR NOT NULL, 
	object_key VARCHAR NOT NULL, 
	content_sha256 VARCHAR, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(document_id) REFERENCES project_documents (id)
);


CREATE TABLE document_pages (
	id VARCHAR NOT NULL, 
	document_id VARCHAR NOT NULL, 
	page_number INTEGER NOT NULL, 
	text_content TEXT NOT NULL, 
	image_object_key VARCHAR, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(document_id) REFERENCES project_documents (id)
);


CREATE TABLE extracted_document_facts (
	id VARCHAR NOT NULL, 
	project_id VARCHAR NOT NULL, 
	document_id VARCHAR NOT NULL, 
	page_number INTEGER, 
	fact_type VARCHAR NOT NULL, 
	label VARCHAR NOT NULL, 
	value_text VARCHAR NOT NULL, 
	numeric_value FLOAT, 
	unit VARCHAR, 
	source_text TEXT NOT NULL, 
	confidence FLOAT NOT NULL, 
	metadata_json TEXT NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(project_id) REFERENCES projects (id), 
	FOREIGN KEY(document_id) REFERENCES project_documents (id)
);


CREATE TABLE rfi_items (
	id VARCHAR NOT NULL, 
	project_id VARCHAR NOT NULL, 
	source_document_id VARCHAR, 
	item_number INTEGER NOT NULL, 
	issue_summary TEXT NOT NULL, 
	requested_action TEXT NOT NULL, 
	relevant_drawing_sheet VARCHAR, 
	due_date VARCHAR, 
	source_requirement_candidates_json TEXT NOT NULL, 
	priority VARCHAR NOT NULL, 
	status VARCHAR NOT NULL, 
	missing_evidence_json TEXT NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(project_id) REFERENCES projects (id), 
	FOREIGN KEY(source_document_id) REFERENCES project_documents (id)
);


CREATE TABLE source_chunks (
	id VARCHAR NOT NULL, 
	source_version_id VARCHAR NOT NULL, 
	clause_id VARCHAR NOT NULL, 
	heading VARCHAR, 
	page_number INTEGER, 
	text TEXT NOT NULL, 
	embedding_ref VARCHAR, 
	token_count INTEGER NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(source_version_id) REFERENCES source_versions (id), 
	FOREIGN KEY(clause_id) REFERENCES clauses (id)
);


CREATE TABLE document_chunks (
	id VARCHAR NOT NULL, 
	project_id VARCHAR NOT NULL, 
	document_id VARCHAR NOT NULL, 
	page_id VARCHAR, 
	page_number INTEGER, 
	chunk_index INTEGER NOT NULL, 
	text TEXT NOT NULL, 
	token_count INTEGER NOT NULL, 
	metadata_json TEXT NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(project_id) REFERENCES projects (id), 
	FOREIGN KEY(document_id) REFERENCES project_documents (id), 
	FOREIGN KEY(page_id) REFERENCES document_pages (id)
);


CREATE TABLE source_citations (
	id VARCHAR NOT NULL, 
	source_chunk_id VARCHAR NOT NULL, 
	source_version_id VARCHAR NOT NULL, 
	clause_id VARCHAR NOT NULL, 
	citation_json TEXT NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(source_chunk_id) REFERENCES source_chunks (id), 
	FOREIGN KEY(source_version_id) REFERENCES source_versions (id), 
	FOREIGN KEY(clause_id) REFERENCES clauses (id)
);


CREATE TABLE tasks (
	id VARCHAR NOT NULL, 
	project_id VARCHAR NOT NULL, 
	rfi_item_id VARCHAR, 
	title VARCHAR NOT NULL, 
	description TEXT NOT NULL, 
	status VARCHAR NOT NULL, 
	priority VARCHAR NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(project_id) REFERENCES projects (id), 
	FOREIGN KEY(rfi_item_id) REFERENCES rfi_items (id)
);

CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY);

INSERT INTO alembic_version (version_num) VALUES ('0001_initial_metadata') ON CONFLICT (version_num) DO NOTHING;
