from __future__ import annotations

from fastapi import FastAPI

from progrec_service.api.routes.system import router as system_router


def create_app() -> FastAPI:
    app = FastAPI(title="ProgRec API")
    app.include_router(system_router)
    return app
