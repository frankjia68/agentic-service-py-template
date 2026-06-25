import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from agentic_service_py_template.ai.agents.investment_summary import create_investment_summary_graph
from agentic_service_py_template.api.auth import add_auth_middleware
from agentic_service_py_template.api.routes import create_router


# ─── Mock helpers (mirrors test_investment_summary.py) ───────────────

class _MockMsg:
    def __init__(self, content: str):
        self.content = content

class _MockChoice:
    def __init__(self, content: str):
        self.message = _MockMsg(content)

class _MockResponse:
    def __init__(self, content: str):
        self.choices = [_MockChoice(content)]

class _MockChunk:
    def __init__(self, content: str):
        self.content = content

_VALID_SUMMARY = json.dumps({
    "summary_highlights": ["Near downtown", "Strong demand"],
    "risk_factors": ["Tax risk"],
    "investment_profile": "Moderate growth",
})

# ─── App fixture ────────────────────────────────────────────────────

@pytest.fixture
def app_with_routes(valid_jwt):
    app = FastAPI()
    # summary_graph is a real compiled LangGraph; its LLM calls are
    # intercepted via patch("...acompletion") in each test below.
    app.state.summary_graph = create_investment_summary_graph()
    # advisor_graph is a mock so tests can inject fake streaming events
    # without compiling a real graph or calling any models.
    app.state.advisor_graph = AsyncMock()
    add_auth_middleware(app)
    app.include_router(create_router())
    return app


@pytest.fixture
def client(app_with_routes):
    transport = ASGITransport(app=app_with_routes)
    return AsyncClient(transport=transport, base_url="http://test")


# ─── GET /api/health ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_returns_ok(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ─── POST /api/investment-summary ───────────────────────────────────

@pytest.mark.asyncio
async def test_investment_summary_requires_auth(client):
    resp = await client.post("/api/investment-summary", json={"supply_id": "test-1"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_investment_summary_returns_summary(client, valid_jwt):
    headers = {"Authorization": f"Bearer {valid_jwt}"}

    # The graph at app.state.summary_graph is a real compiled LangGraph.
    # It calls litellm.acompletion() internally. Patching acompletion at
    # the source module lets the graph run with a fake LLM response.
    with patch(
        "agentic_service_py_template.ai.agents.investment_summary.acompletion",
        new_callable=AsyncMock,
    ) as mock_acompletion:
        mock_acompletion.return_value = _MockResponse(_VALID_SUMMARY)
        resp = await client.post(
            "/api/investment-summary",
            json={"supply_id": "MLS-456"},
            headers=headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"]["summary_highlights"] == ["Near downtown", "Strong demand"]
    assert data["summary"]["investment_profile"] == "Moderate growth"
    assert data["error"] is None
    assert data["attempts"] == 1


@pytest.mark.asyncio
async def test_investment_summary_retries_on_invalid_json(client, valid_jwt):
    headers = {"Authorization": f"Bearer {valid_jwt}"}

    with patch(
        "agentic_service_py_template.ai.agents.investment_summary.acompletion",
        new_callable=AsyncMock,
    ) as mock_acompletion:
        mock_acompletion.side_effect = [
            _MockResponse("bad json"),
            _MockResponse("also bad"),
            _MockResponse(_VALID_SUMMARY),
        ]
        resp = await client.post(
            "/api/investment-summary",
            json={"supply_id": "MLS-789"},
            headers=headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"] is not None
    assert data["attempts"] == 3


@pytest.mark.asyncio
async def test_investment_summary_returns_error_on_max_retries(client, valid_jwt):
    headers = {"Authorization": f"Bearer {valid_jwt}"}

    with patch(
        "agentic_service_py_template.ai.agents.investment_summary.acompletion",
        new_callable=AsyncMock,
    ) as mock_acompletion:
        mock_acompletion.side_effect = [
            _MockResponse("bad"),
            _MockResponse("bad"),
            _MockResponse("bad"),
        ]
        resp = await client.post(
            "/api/investment-summary",
            json={"supply_id": "MLS-999"},
            headers=headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"] is None
    assert data["error"] is not None
    assert data["attempts"] == 3


# ─── POST /api/chat/stream ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_chat_stream_requires_auth(client):
    resp = await client.post(
        "/api/chat/stream",
        json={"message": "hi", "thread_id": "t1"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_chat_stream_returns_sse_events(app_with_routes, client, valid_jwt):
    headers = {"Authorization": f"Bearer {valid_jwt}"}

    async def mock_astream(*args, **kwargs):
        yield {"event": "on_chat_model_stream", "data": {"chunk": _MockChunk("Hello")}}
        yield {"event": "on_chat_model_stream", "data": {"chunk": _MockChunk(" world")}}
        yield {"event": "on_chain_end", "data": {"output": "__end__"}}

    # Configure the mock already on app.state.advisor_graph (set in fixture).
    app_with_routes.state.advisor_graph.astream_events = mock_astream
    app_with_routes.state.advisor_graph.ainvoke = AsyncMock(return_value={"messages": []})

    async with client.stream(
        "POST",
        "/api/chat/stream",
        json={"message": "hello", "thread_id": "session-1"},
        headers=headers,
    ) as resp:
        assert resp.status_code == 200
        body = await resp.aread()
        text = body.decode()

    assert 'event: token' in text
    assert 'data: Hello' in text
    assert 'data:  world' in text
    assert 'event: done' in text