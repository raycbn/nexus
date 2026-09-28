from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from packages.auth import get_settings, hash_password
from packages.persistence.database import get_session_factory, init_db
from packages.persistence.repositories.core import CoreRepository
from packages.platform.metrics import metrics

from apps.api.readiness import readiness_status
from apps.api.routes.agents import router as agents_router
from apps.api.routes.alerts import router as alerts_router
from apps.api.routes.audit import router as audit_router
from apps.api.routes.auth import router as auth_router
from apps.api.routes.billing import router as billing_router
from apps.api.routes.connectors import router as connectors_router
from apps.api.routes.credentials import router as credentials_router
from apps.api.routes.discovery_schedules import router as discovery_schedules_router
from apps.api.routes.incidents import router as incidents_router
from apps.api.routes.investigations import router as investigations_router
from apps.api.routes.metering import router as metering_router
from apps.api.routes.organization_access import router as organization_access_router
from apps.api.routes.public_api import router as public_api_router
from apps.api.routes.remediations import router as remediations_router
from apps.api.routes.resources import router as resources_router
from apps.api.routes.setup import router as setup_router
from apps.api.routes.sso import router as sso_router
from apps.api.routes.workspaces import router as workspaces_router
from apps.api.security import configure_security


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    if settings.app_environment == "local" and settings.auto_migrate:
        await init_db()
    if settings.app_environment == "local" and settings.auto_bootstrap:
        async with get_session_factory()() as session:
            repo = CoreRepository(session)
            organization, _, workspace = await repo.ensure_local_bootstrap(
                settings.bootstrap_email, hash_password(settings.bootstrap_password_str)
            )
            await repo.ensure_dev_resource(organization.id, workspace.id)
            await repo.ensure_dev_agent(organization.id, workspace.id)
            await session.commit()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="NEXUS API",
        description="NEXUS - Multi-tenant AI Operations Platform",
        version="0.2.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-API-Key"],
    )
    app.include_router(auth_router, prefix="/api")
    app.include_router(alerts_router, prefix="/api")
    app.include_router(billing_router, prefix="/api")
    app.include_router(setup_router, prefix="/api")
    app.include_router(workspaces_router, prefix="/api")
    app.include_router(organization_access_router, prefix="/api")
    app.include_router(incidents_router, prefix="/api")
    app.include_router(connectors_router, prefix="/api")
    app.include_router(credentials_router, prefix="/api")
    app.include_router(discovery_schedules_router, prefix="/api")
    app.include_router(resources_router, prefix="/api")
    app.include_router(remediations_router, prefix="/api")
    app.include_router(agents_router, prefix="/api")
    app.include_router(audit_router, prefix="/api")
    app.include_router(investigations_router, prefix="/api")
    app.include_router(sso_router, prefix="/api")
    app.include_router(metering_router, prefix="/api")
    app.include_router(public_api_router, prefix="/api")

    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}

    @app.get("/ready")
    async def readiness_check():
        return await readiness_status()

    @app.get("/metrics")
    async def metrics_check():
        return Response(content=metrics.prometheus(), media_type="text/plain; version=0.0.4")

    return app


app = create_app()
mfa_module = __import__("apps.api.routes.mfa", fromlist=["router"])
app.include_router(mfa_module.router, prefix="/api")
app.openapi_schema = None
configure_security(app)

marketplace_module = __import__("apps.api.routes.marketplace", fromlist=["router"])
app.include_router(marketplace_module.router, prefix="/api")
app.openapi_schema = None
