import pytest
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from agentic_service_py_template.config import Settings
from agentic_service_py_template.api.auth import (
    add_auth_middleware,
    create_system_jwt,
    verify_jwt,
    get_current_user,
    is_user_authenticated,
    require_role,
)


@pytest.fixture
def settings():
    return Settings()


def test_create_jwt_returns_valid_token(settings):
    token = create_system_jwt("user-42")
    payload = verify_jwt(token)
    assert payload["sub"] == "user-42"
    assert payload["iss"] == "agentic-service-py-template"


def test_verify_jwt_rejects_expired_token(settings):
    expired = jwt.encode(
        {
            "sub": "test",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
            "iss": "agentic-service-py-template",
        },
        settings.auth_jwt_secret,
        algorithm=settings.auth_jwt_algorithm,
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        verify_jwt(expired)


def test_verify_jwt_rejects_tampered_token(settings):
    token = create_system_jwt("user-42")
    tampered = token.rstrip(".") + ".invalidsig"
    with pytest.raises(jwt.InvalidTokenError):
        verify_jwt(tampered)


def test_verify_jwt_rejects_bad_signature(settings):
    bogus = jwt.encode(
        {
            "sub": "x",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iss": "agentic-service-py-template",
        },
        "wrong-secret-key",
        algorithm=settings.auth_jwt_algorithm,
    )
    with pytest.raises(jwt.InvalidTokenError):
        verify_jwt(bogus)


def test_get_current_user_stub():
    user = get_current_user("alice")
    assert user == {"user_id": "alice", "roles": ["user"]}


def test_require_role_stub_returns_true():
    user = {"user_id": "alice", "roles": ["user"]}
    assert require_role(user, "user") is True
    assert require_role(user, "admin") is True


def test_is_user_authenticated_stub_returns_true():
    user = {"user_id": "bob", "roles": ["user"]}
    assert is_user_authenticated(user) is True


@pytest.fixture
def protected_app():
    app = FastAPI()
    add_auth_middleware(app)

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    @app.post("/api/chat/stream")
    async def chat():
        return {"streaming": True}

    return app


@pytest.mark.asyncio
async def test_health_anonymous(protected_app):
    transport = ASGITransport(app=protected_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_chat_stream_requires_token(protected_app):
    transport = ASGITransport(app=protected_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/chat/stream", json={"message": "hi", "thread_id": "t1"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid or missing token"


@pytest.mark.asyncio
async def test_chat_stream_with_valid_token(protected_app, valid_jwt):
    transport = ASGITransport(app=protected_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/chat/stream",
            json={"message": "hi", "thread_id": "t1"},
            headers={"Authorization": f"Bearer {valid_jwt}"},
        )
    assert resp.status_code == 200
    assert resp.json() == {"streaming": True}


@pytest.mark.asyncio
async def test_chat_stream_with_invalid_token(protected_app):
    transport = ASGITransport(app=protected_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/chat/stream",
            json={"message": "hi", "thread_id": "t1"},
            headers={"Authorization": "Bearer obviously.invalid.token"},
        )
    assert resp.status_code == 401
