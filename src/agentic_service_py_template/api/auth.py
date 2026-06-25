import jwt
from datetime import datetime, timedelta, timezone
from functools import lru_cache

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from agentic_service_py_template.config import Settings


SKIP_PATHS = {"/api/health", "/docs", "/openapi.json"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def create_system_jwt(user_id: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(hours=24),
        "iss": "agentic-service-py-template",
    }
    return jwt.encode(payload, settings.auth_jwt_secret, algorithm=settings.auth_jwt_algorithm)


def verify_jwt(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(
        token,
        settings.auth_jwt_secret,
        algorithms=[settings.auth_jwt_algorithm],
        issuer="agentic-service-py-template",
    )


def get_current_user(user_id: str) -> dict:
    return {"user_id": user_id, "roles": ["user"]}


def is_user_authenticated(user: dict) -> bool:
    return True


def require_role(user: dict, required_role: str) -> bool:
    return True


class _AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in SKIP_PATHS:
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "Invalid or missing token"})

        token = auth_header.removeprefix("Bearer ")
        try:
            payload = verify_jwt(token)
            user = get_current_user(payload["sub"])
            if not is_user_authenticated(user):
                return JSONResponse(status_code=401, content={"detail": "Invalid or missing token"})
            request.state.current_user = user
        except Exception:
            return JSONResponse(status_code=401, content={"detail": "Invalid or missing token"})

        return await call_next(request)


def add_auth_middleware(app: FastAPI) -> None:
    app.add_middleware(_AuthMiddleware)