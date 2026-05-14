from __future__ import annotations

from sqlalchemy.orm import Session

from datetime import datetime

from sqlalchemy import func, select

from progrec_service.db.models import PipelineJob, PipelineResult, WorkerEvent


class PipelineJobRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_job(self, model: PipelineJob) -> PipelineJob:
        self.session.add(model)
        self.session.flush()
        return model

    def get_job(self, job_id: str) -> PipelineJob | None:
        return self.session.get(PipelineJob, job_id)

    def list_jobs(self, *, limit: int = 50) -> list[PipelineJob]:
        stmt = select(PipelineJob).order_by(PipelineJob.queued_at.desc()).limit(limit)
        return list(self.session.scalars(stmt))

    def add_result(self, model: PipelineResult) -> PipelineResult:
        self.session.add(model)
        self.session.flush()
        return model

    def get_result(self, job_id: str) -> PipelineResult | None:
        stmt = select(PipelineResult).where(PipelineResult.job_id == job_id)
        return self.session.scalar(stmt)

    def add_event(self, model: WorkerEvent) -> WorkerEvent:
        self.session.add(model)
        self.session.flush()
        return model

    def latest_event_at(self, job_id: str) -> datetime | None:
        stmt = select(func.max(WorkerEvent.created_at)).where(WorkerEvent.job_id == job_id)
        return self.session.scalar(stmt)
