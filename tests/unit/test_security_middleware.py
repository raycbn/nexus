import httpx
from apps.api.security import SecurityMiddleware, configure_security
from fastapi import FastAPI


async def request(app: FastAPI, method: str, path: str) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, path)


def make_app() -> FastAPI:
    app = FastAPI()

    @app.get("/health")
    async def health():
        return {"ok": True}

    configure_security(app)
    return app


async def test_security_headers_and_request_id():
    response = await request(make_app(), "GET", "/health")
    assert response.status_code == 200
    assert response.headers["X-Request-ID"]
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["Permissions-Policy"]
    assert response.headers["Content-Security-Policy"]


async def test_auth_rate_limit():
    app = FastAPI()

    @app.post("/api/auth/login")
    async def login():
        return {"ok": True}

    app.add_middleware(SecurityMiddleware, max_requests=2, window_seconds=60)
    assert (await request(app, "POST", "/api/auth/login")).status_code == 200
    assert (await request(app, "POST", "/api/auth/login")).status_code == 200
    assert (await request(app, "POST", "/api/auth/login")).status_code == 429
