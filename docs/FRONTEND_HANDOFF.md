# Frontend Handoff

Build the frontend from the generated OpenAPI JSON at `/openapi.json`. Do not invent endpoints.

Recommended stack:

- Next.js App Router
- TypeScript
- Tailwind
- shadcn/ui
- TanStack Query
- React Hook Form
- Zod
- OpenAPI-generated API client

UX principle: this should feel like a project checklist and response-pack builder, not a chatbot.

Core screens:

- Dashboard
- Projects
- Project dashboard
- Documents and plan QA
- Compliance matrix
- RFI parser/response builder
- Source questions
- Measurements
- Exports
- Source library
- Jobs
- Settings

Required components:

- `AppShell`
- `ProjectHeader`
- `StatusBadge`
- `RiskSummaryCard`
- `CitationCard`
- `CitationDrawer`
- `AssumptionList`
- `MissingInfoPanel`
- `HumanReviewBanner`
- `ComplianceMatrixTable`
- `RfiItemCard`
- `ResponseEditor`
- `SourceVersionBadge`
- `JobStatusPill`
- `DocumentUploadDropzone`
- `PdfPlanViewer`
- `AuditTimeline`
- `ExportBuilder`

Frontend safety copy:

- Use `likely pass`, `likely fail`, `missing information`, `needs human review`, and `unsupported`.
- Do not use `approved`, `certified`, or `compliant` as final status.
- Show source version and retrieved date wherever citations appear.
- Show human review warnings before export.

If an endpoint is missing, create a typed mock and list it in `FRONTEND_GAPS.md`.
