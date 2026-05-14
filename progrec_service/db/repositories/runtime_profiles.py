from __future__ import annotations

from sqlalchemy.orm import Session

from progrec_service.db.models import RuntimeProfile


class RuntimeProfileRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, profile: RuntimeProfile) -> RuntimeProfile:
        self.session.add(profile)
        self.session.flush()
        return profile

    def get(self, profile_id: str) -> RuntimeProfile | None:
        return self.session.get(RuntimeProfile, profile_id)
