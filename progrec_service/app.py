from __future__ import annotations

from fastapi import FastAPI

from progrec_service.api.routes.agent import router as agent_router
from progrec_service.api.routes.pipeline import router as pipeline_router
from progrec_service.api.routes.runtime_profiles import router as runtime_profile_router
from progrec_service.api.routes.system import router as system_router
from progrec_service.db.models import Base
from progrec_service.db.session import engine


def create_app() -> FastAPI:
    Base.metadata.create_all(engine)
    app = FastAPI(title="ProgRec API")
    app.include_router(system_router)
    app.include_router(runtime_profile_router)
    app.include_router(agent_router)
    app.include_router(pipeline_router)
    return app
