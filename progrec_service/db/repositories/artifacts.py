from __future__ import annotations

from sqlalchemy.orm import Session

from progrec_service.db.models import Artifact


class ArtifactRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, model: Artifact) -> Artifact:
        self.session.add(model)
        self.session.flush()
        return model
