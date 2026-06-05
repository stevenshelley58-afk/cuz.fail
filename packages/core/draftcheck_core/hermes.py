from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from draftcheck_core.audit import record_audit
from draftcheck_core.config import get_settings
from draftcheck_core.json_utils import from_json, to_json
from draftcheck_core.models import BackgroundJob, JobTrace
from draftcheck_shared.schemas import JobStatus


class HermesAdapter:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def enqueue_source_ingestion_job(self, payload: dict, source_version_id: str | None = None) -> JobStatus:
        return self._enqueue("source_ingestion", payload, source_version_id=source_version_id)

    def enqueue_council_pack_job(self, project_id: str, payload: dict) -> JobStatus:
        return self._enqueue("council_pack", payload, project_id=project_id)

    def enqueue_rfi_analysis_job(self, project_id: str, payload: dict) -> JobStatus:
        return self._enqueue("rfi_analysis", payload, project_id=project_id)

    def enqueue_source_freshness_audit(self, payload: dict) -> JobStatus:
        return self._enqueue("source_freshness_audit", payload)

    def poll_job_status(self, job_id: str) -> JobStatus:
        job = self._get_job(job_id)
        if self.settings.hermes_enabled and job.remote_job_id and self.settings.hermes_base_url:
            try:
                response = httpx.get(
                    f"{self.settings.hermes_base_url.rstrip('/')}/jobs/{job.remote_job_id}",
                    headers=self._headers(),
                    timeout=self.settings.hermes_timeout_ms / 1000,
                )
                response.raise_for_status()
                status = response.json().get("status", job.status)
                job.status = status
            except Exception as exc:  # pragma: no cover - network failure shape depends on Hermes
                job.status = "failed"
                job.error = str(exc)
        return _job_to_schema(job)

    def store_job_trace(
        self,
        *,
        job_id: str,
        prompt: str,
        status: str,
        project_id: str | None = None,
        source_version_id: str | None = None,
        model: str | None = None,
        provider: str = "hermes",
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        cost: float | None = None,
        error: str | None = None,
        artifacts: list | None = None,
    ) -> JobTrace:
        job = self._get_job(job_id)
        trace = JobTrace(
            job_id=job_id,
            correlation_id=job.correlation_id,
            project_id=project_id or job.project_id,
            source_version_id=source_version_id or job.source_version_id,
            prompt=prompt,
            model=model or job.model,
            provider=provider,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            status=status,
            started_at=datetime.now(UTC).replace(tzinfo=None),
            finished_at=(
                datetime.now(UTC).replace(tzinfo=None)
                if status in {"completed", "failed", "cancelled"}
                else None
            ),
            error=error,
            artifacts_json=to_json(artifacts or []),
        )
        self.db.add(trace)
        self.db.flush()
        return trace

    def retry_failed_job(self, job_id: str) -> JobStatus:
        job = self._get_job(job_id)
        if job.status != "failed":
            raise ValueError("Only failed jobs can be retried")
        job.status = "queued"
        job.error = None
        record_audit(
            self.db,
            action="job.retried",
            target_type="background_job",
            target_id=job.id,
            project_id=job.project_id,
        )
        return _job_to_schema(job)

    def cancel_job(self, job_id: str) -> JobStatus:
        job = self._get_job(job_id)
        job.status = "cancelled"
        record_audit(
            self.db,
            action="job.cancelled",
            target_type="background_job",
            target_id=job.id,
            project_id=job.project_id,
        )
        return _job_to_schema(job)

    def list_traces(self, job_id: str) -> list[dict]:
        return [
            {
                "id": trace.id,
                "job_id": trace.job_id,
                "correlation_id": trace.correlation_id,
                "prompt": trace.prompt,
                "model": trace.model,
                "provider": trace.provider,
                "input_tokens": trace.input_tokens,
                "output_tokens": trace.output_tokens,
                "cost": trace.cost,
                "status": trace.status,
                "started_at": trace.started_at,
                "finished_at": trace.finished_at,
                "error": trace.error,
                "artifacts": from_json(trace.artifacts_json, []),
            }
            for trace in self.db.scalars(select(JobTrace).where(JobTrace.job_id == job_id)).all()
        ]

    def _enqueue(
        self,
        job_type: str,
        payload: dict,
        *,
        project_id: str | None = None,
        source_version_id: str | None = None,
    ) -> JobStatus:
        correlation_id = f"corr_{uuid4().hex}"
        provider = "hermes" if self.settings.hermes_enabled else "local-disabled"
        model = (
            self.settings.hermes_review_model
            if job_type in {"council_pack", "final_review"}
            else self.settings.hermes_default_model
        )
        job = BackgroundJob(
            job_type=job_type,
            status="queued" if self.settings.hermes_enabled else "disabled",
            correlation_id=correlation_id,
            project_id=project_id,
            source_version_id=source_version_id,
            provider=provider,
            model=model,
            payload_json=to_json(payload),
        )
        self.db.add(job)
        self.db.flush()

        if self.settings.hermes_enabled:
            try:
                response = httpx.post(
                    f"{self.settings.hermes_base_url.rstrip('/')}/jobs",
                    headers=self._headers(),
                    json={
                        "job_type": job_type,
                        "correlation_id": correlation_id,
                        "project_id": project_id,
                        "source_version_id": source_version_id,
                        "model": model,
                        "payload": payload,
                    },
                    timeout=self.settings.hermes_timeout_ms / 1000,
                )
                response.raise_for_status()
                data = response.json()
                job.remote_job_id = data.get("id")
                job.status = data.get("status", "queued")
            except Exception as exc:  # pragma: no cover - network failure shape depends on Hermes
                job.status = "failed"
                job.error = str(exc)
        else:
            job.error = "Hermes disabled by HERMES_ENABLED=false"

        self.store_job_trace(
            job_id=job.id,
            prompt=to_json(payload),
            status=job.status,
            project_id=project_id,
            source_version_id=source_version_id,
            model=model,
            provider=provider,
            error=job.error,
        )
        record_audit(
            self.db,
            action="job.enqueued",
            target_type="background_job",
            target_id=job.id,
            project_id=project_id,
            metadata={"job_type": job_type, "status": job.status, "provider": provider},
        )
        return _job_to_schema(job)

    def _headers(self) -> dict[str, str]:
        headers = {"content-type": "application/json"}
        if self.settings.hermes_api_key:
            headers["authorization"] = f"Bearer {self.settings.hermes_api_key}"
        return headers

    def _get_job(self, job_id: str) -> BackgroundJob:
        job = self.db.get(BackgroundJob, job_id)
        if not job:
            raise KeyError("Job not found")
        return job


def _job_to_schema(job: BackgroundJob) -> JobStatus:
    return JobStatus(
        id=job.id,
        job_type=job.job_type,
        status=job.status,
        correlation_id=job.correlation_id,
        project_id=job.project_id,
        source_version_id=job.source_version_id,
        provider=job.provider,
        model=job.model,
        remote_job_id=job.remote_job_id,
        error=job.error,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )
