from apps.api.routes.agents import router as agents_router
from apps.api.routes.audit import router as audit_router
from apps.api.routes.incidents import router as incidents_router
from apps.api.routes.resources import router as resources_router

__all__ = [
    "agents_router",
    "audit_router",
    "incidents_router",
    "resources_router",
]
