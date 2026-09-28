import asyncio
from uuid import UUID

import httpx
from packages.auth import create_access_token, get_settings
from packages.domain.models.identity import AuthenticatedPrincipal

ORG = UUID("1de37c99-ebc0-49d2-bf76-68e5bad1edbb")
WORKSPACE = UUID("00000000-0000-0000-0000-000000000001")
USER = UUID("00000000-0000-0000-0000-000000000001")


async def main() -> None:
    settings = get_settings()
    principal = AuthenticatedPrincipal(
        user_id=USER,
        organization_id=ORG,
        workspace_id=WORKSPACE,
        role="admin",
    )
    token = create_access_token(principal, settings)
    async with httpx.AsyncClient(timeout=240) as client:
        response = await client.post(
            "http://localhost:8000/api/investigations",
            json={
                "objective": (
                    "Investigate whether the API is slow and identify the most "
                    "likely cause using available read-only evidence."
                )
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        print("STATUS", response.status_code)
        print(response.text)


if __name__ == "__main__":
    asyncio.run(main())
