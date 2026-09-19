from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.routes.agents import router as agents_router
from apps.api.routes.audit import router as audit_router
from apps.api.routes.incidents import router as incidents_router
from apps.api.routes.resources import router as resources_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="NEXUS API",
        description="NEXUS - Multi-tenant AI Operations Platform",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(incidents_router, prefix="/api")
    app.include_router(resources_router, prefix="/api")
    app.include_router(agents_router, prefix="/api")
    app.include_router(audit_router, prefix="/api")

    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}

    return app


app = create_app()
