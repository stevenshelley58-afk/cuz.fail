# Frontend → API Wiring (handoff)

Goal: replace the hard-coded `DB` object in `ui/index.html` with live calls to
the deployed API, **without changing the look or the renderers**. The render
functions (`renderHead`, `renderChat`, `renderEmails`, `renderFiles`,
`renderChecklist`) stay as-is; only their data source changes.

- Frontend (this file): `https://cuz.fail` (Vercel, static `ui/`).
- API: `https://api.cuz.fail` — FastAPI, routes under `/v1`. Local/test CORS may use a wildcard,
  but durable deployments require `CORS_ALLOWED_ORIGINS` to list explicit app origins. Health: `GET /v1/me`.
- DB: Supabase Postgres (schema applied). Writes from the API land there.

Status today: the API is real but the LLM/embedding providers are `mock`, so
Ask answers and RFI drafts come back as honest placeholders/refusals until the
rules pipeline (see RULES_EXTRACTION_PIPELINE.md) and a real provider land. Wire
the plumbing now; the content gets real as the backend fills in. Nothing below
should invent data the API didn't return.

---

## 0. Config + tiny client

Add near the top of the `<script>` in `ui/index.html`, replacing nothing else:

```js
const API = "https://api.cuz.fail/v1";
let TOKEN = null;

async function api(path, { method = "GET", body, isForm } = {}) {
  const headers = {};
  if (TOKEN) headers.authorization = `Bearer ${TOKEN}`;
  if (body && !isForm) headers["content-type"] = "application/json";
  const res = await fetch(API + path, {
    method,
    headers,
    body: isForm ? body : body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`${method} ${path} → ${res.status} ${await res.text()}`);
  return res.status === 204 ? null : res.json();
}

async function boot() {
  const auth = await api("/auth/dev-login", { method: "POST" });
  TOKEN = auth.access_token;                 // "dev-token" for now
  await loadProjects();                       // replaces the static DB
}
```

Call `boot()` instead of the current bare `renderAll()` at the bottom. Keep a
real error path: if `boot()` throws, render an inline "couldn't reach the
service" state — never silently fall back to demo data in production.

Auth note: `/auth/dev-login` is a local/development helper and is disabled when durable deployment
flags are enabled. Production clients must use the configured API key/auth path; do not hard-code a
token or wire production startup to `dev-login`.

---

## 1. Projects list + switcher

Replace the static `DB` keys with a fetch:

```js
let PROJECTS = {};            // id -> hydrated project view-model
let current = null;

async function loadProjects() {
  const rows = await api("/projects");        // ProjectRead[]
  PROJECTS = {};
  for (const p of rows) PROJECTS[p.id] = projectStub(p);
  current = rows[0]?.id ?? null;
  if (current) await hydrate(current);
  renderSidebar();
  if (current) renderAll();
}
```

- `GET /v1/projects` → `ProjectRead[]`. Fields you get: `id`, `project_name`,
  `client_name`, `address`, `local_government`, `lot_plan`, `project_type`,
  `stage`, `r_code_density`, `status` ("active"/"deleted"), timestamps.
- New project form (`#newproj`): `POST /v1/projects` with **required** body
  `{ project_name, address, local_government, project_type, stage }`. Today the
  prototype only collects an address — add `local_government` (the council) to
  the form, because the API requires it and every rule depends on it. Minimum
  viable body:
  `{ project_name: address, address, local_government: <council>, project_type:"single_house", stage:"concept" }`.
- Delete = `DELETE /v1/projects/{id}` (soft-deletes; filter `status==="active"`).

---

## 2. The dossier header (chips / links) — partial today

The prototype shows rich chips (Zone, MRS, Bushfire, Heritage, Sewer) and a row
of source links. The API does not produce all of that yet. Map what exists,
leave the rest for the address-profile work:

| Chip / field   | Source today | Notes |
|----------------|--------------|-------|
| address, sub   | `ProjectRead.address`, `local_government`, `lot_plan` | sub = `${local_government} · ${lot_plan ?? ''}` |
| Zone           | `PropertyRead.zoning` via `GET /v1/projects/{id}/property` | null until set |
| lot area       | `PropertyRead.lot_area_m2` | |
| overlays       | `PropertyRead.overlays` (string[]) | render each as a warn chip |
| MRS / Bushfire / Heritage / Sewer | **not in API yet** | omit; do NOT fake. These come from the dossier/PlanWA/DFES lookups in the pipeline spec |
| source links   | **not in API yet** | omit until a links/facts endpoint exists |

So `renderHead` gets: address + council + zone + lot area + overlay chips. The
"Details" expander shows whatever `PropertyRead` returned and nothing it didn't.
Property is set via `PUT /v1/projects/{id}/property`
(`{ address, zoning, lot_area_m2, overlays, planning_scheme }`).

**Status pill is derived, not stored.** `ProjectRead.status` is only
active/deleted. Compute the prototype's `["flag"|"ok"|"wait", label]` from the
checklist: any `likely_fail`/`needs_human_review` → `flag`; all resolved/pass →
`ok`; nothing run yet → `wait`.

---

## 3. Ask pane

```js
async function ask(question) {
  return api(`/projects/${current}/ask-source`, {
    method: "POST", body: { question, source_filters: {} },
  }); // -> StandardAnswer
}
```

`StandardAnswer` →

- `answer` → bubble text.
- `citations[]` → the collapsible "N sources" pills. Each `Citation` has
  `source_title`, `version_label`, `clause_id`, `heading`, `page_number`,
  `canonical_url`, `quote`. Render pill = `source_title · clause_id`; the quote
  is the 3-second-verify payload (show on tap).
- `status` ∈ `unsupported | needs_human_review | likely_* | missing_info |
  not_applicable`. When `unsupported` or `citations` is empty, render the honest
  "can't answer from the source library" bubble — that is the correct behaviour,
  not a bug. **Never** show an answer with no citation as if it were sourced.

Until sources are imported the library is empty, so expect `unsupported`. That
proves the guardrail works end to end.

---

## 4. Emails pane (RFI)

There is no inbox endpoint; emails/RFIs are pasted in. Flow:

1. Paste council text → `POST /v1/projects/{id}/rfi/parse` `{ text }` →
   `RfiItemRead[]` (each: `issue_summary`, `requested_action`,
   `relevant_drawing_sheet`, `priority`, `missing_evidence[]`,
   `source_requirement_candidates[]` citations).
2. `POST /v1/projects/{id}/rfi/draft-response` → `ResponseDraftRead`
   (`draft_text`, `content`, `citations`, `requires_human_review`,
   `liability_notice`). `draft_text` → the "Draft reply" body; keep the Copy
   button and the "yours to edit" label.
3. List existing drafts: `GET /v1/projects/{id}/responses`.

Draft text is template-generated under the mock provider — wire it now, quality
improves when the real provider lands. Keep `liability_notice` visible.

---

## 5. Plans pane (uploads) — fully real today

The UI already has `#fileinput` (`.pdf,.dwg,.dxf,.ifc`). Wire the drop/select to:

```js
async function upload(file) {
  const fd = new FormData();
  fd.append("document_type", "drawing");
  fd.append("title", file.name);
  fd.append("file", file);
  return api(`/projects/${current}/documents/upload`, { method: "POST", body: fd, isForm: true });
} // -> DocumentRead
```

- List: `GET /v1/projects/{id}/documents` → `DocumentRead[]`
  (`title`, `content_type`, `parse_status`, `analysis_status`, `created_at`).
- Tier tag (`measured` vs `read`): derive from `content_type` — DXF/IFC →
  `measured`, PDF/DOCX → `read`, while `parse_status==="pending"` → `queued`.
  (A real per-file tier field is a good backend add later; derive for now.)
- Extracted values for the checklist: `GET /v1/projects/{id}/documents/{doc}/facts`
  and `GET /v1/projects/{id}/measurements`.

This path writes real rows to Supabase — it's the most complete pane.

---

## 6. Checklist pane

```js
async function runChecks() {
  await api(`/projects/${current}/compliance/run`, { method: "POST" });
  return api(`/projects/${current}/compliance/matrix`);
}
```

`GET /compliance/matrix` returns the latest matrix envelope; map each `results[]`
item as a `CheckResultRead` row:

| Prototype field | API field |
|---|---|
| rule | `label` |
| req  | `requirement` |
| prop | `proposed` |
| src  | derive from `citations`/measurement source (`measured`/`read`/`missing`) |
| st   | map `status`: `likely_pass`→pass, `likely_fail`/`needs_human_review`→flag, `missing_info`→info, `not_applicable`→hide |
| note | first of `missing_information[]` / `assumptions[]` |

- "Resolve" on a flagged row → `PATCH /v1/projects/{id}/checks/{check_result_id}`
  `{ status: "needs_human_review", ...}` or record a signoff via
  `POST /v1/projects/{id}/signoffs`. (Confirm the exact resolve semantics with
  the backend; a human-ack field on the check result is the clean version.)
- Most rows return `missing_info`/`needs_human_review` until measurements exist
  and check definitions are seeded — that is expected and honest. The summary
  line should say "checked against vX" only when `source_version_ids` is present.

---

## 7. Build order

1. `boot()` + `loadProjects()` + project switcher/create (sections 0–1). Ship —
   real projects in Supabase, visible in the list.
2. Plans upload (section 5). Ship — real documents + extracted facts.
3. Checklist run/list (section 6). Ship — honest statuses.
4. Ask (section 3) and Emails (section 4). Ship — guardrail-correct placeholders.
5. Dossier chips/links (section 2) — blocked on the address-profile backend work;
   wire zone/overlays now, add the rest when the facts endpoint exists.

Each step is independently shippable and never shows data the API didn't return.

## 8. Backend asks (small, unblock the frontend)

- A derived **project status** field on `ProjectRead` (or a `/projects/{id}/summary`)
  so the sidebar dot doesn't require pulling every check.
- A **per-document tier** field (`measured`/`read`) instead of MIME-sniffing.
- A **facts/dossier endpoint** returning the chips + source links once the
  PlanWA/Landgate/DFES lookups exist.
- Confirm the **resolve/ack** semantics for a flagged check result.

## 9. Guardrails (do not regress)

- No answer renders without its citation; `unsupported` is a valid, expected state.
- Drafts and checks always show they need human review; keep liability notices.
- The frontend never computes compliance itself — it displays what the API returns.
- No demo-data fallback in production. If the API is unreachable, say so.
