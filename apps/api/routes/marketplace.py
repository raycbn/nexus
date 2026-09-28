from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


class MarketplaceItem(BaseModel):
    slug: str
    name: str
    version: str
    category: str
    description: str
    publisher: str
    status: str = "available"
    docs_url: str


CATALOG = (
    MarketplaceItem(
        slug="nexus-public-api", name="NEXUS Public API", version="v1",
        category="Developer", description="Tenant-scoped REST API for resources and incidents.",
        publisher="NEXUS", docs_url="/docs#tag/public-api",
    ),
    MarketplaceItem(
        slug="nexus-python-sdk", name="NEXUS Python SDK", version="0.1.0",
        category="SDK", description="Typed Python client for the NEXUS Public API.",
        publisher="NEXUS", docs_url="/sdk/python",
    ),
    MarketplaceItem(
        slug="nexus-typescript-sdk", name="NEXUS TypeScript SDK", version="0.1.0",
        category="SDK", description="Browser and Node.js client for the NEXUS Public API.",
        publisher="NEXUS", docs_url="/sdk/typescript",
    ),
)


@router.get("/catalog", response_model=list[MarketplaceItem])
async def marketplace_catalog() -> list[MarketplaceItem]:
    return list(CATALOG)


@router.get("/catalog/{slug}", response_model=MarketplaceItem)
async def marketplace_item(slug: str) -> MarketplaceItem:
    for item in CATALOG:
        if item.slug == slug:
            return item
    raise HTTPException(status_code=404, detail="Marketplace item not found")
