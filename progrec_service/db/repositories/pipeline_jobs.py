from __future__ import annotations

from sqlalchemy.orm import Session

from sqlalchemy import select

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
