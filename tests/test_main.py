import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI

from agentic_service_py_template.main import APP_TITLE, app, create_app


@pytest.mark.asyncio
async def test_main_app_health():
    assert app.title == APP_TITLE
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_create_app_accepts_plugin_components():
    def add_probe_endpoint(app: FastAPI) -> None:
        @app.get("/probe")
        async def probe():
            return {"plugin": "ok"}

    custom_app = create_app(plugins=[add_probe_endpoint])

    assert custom_app.title == APP_TITLE
    transport = ASGITransport(app=custom_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/probe")

    assert resp.status_code == 200
    assert resp.json() == {"plugin": "ok"}
