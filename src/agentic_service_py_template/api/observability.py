import logging
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Request

logger = logging.getLogger(__name__)

correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def generate_correlation_id() -> str:
    cid = str(uuid.uuid4())
    correlation_id_var.set(cid)
    return cid


def get_correlation_id() -> str | None:
    return correlation_id_var.get()


async def _persist_request_log(
    session_factory: Any,
    correlation_id: str,
    endpoint: str,
    method: str,
    protocol: str,
    status_code: int,
    duration_ms: int,
    user_id: str | None = None,
) -> None:
    from agentic_service_py_template.models import RequestLog

    entry = RequestLog(
        correlation_id=correlation_id,
        endpoint=endpoint,
        method=method,
        protocol=protocol,
        status_code=status_code,
        duration_ms=duration_ms,
        user_id=user_id,
        requested_at_utc=datetime.now(timezone.utc),
    )
    async with session_factory() as session:
        session.add(entry)
        await session.commit()


def add_observability_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def observability_middleware(request: Request, call_next):
        cid = generate_correlation_id()
        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration_ms = int((time.perf_counter() - start) * 1000)
            user_id = getattr(request.state, "user", None)
            try:
                await _persist_request_log(
                    session_factory=request.app.state.session_factory,
                    correlation_id=cid,
                    endpoint=str(request.url.path),
                    method=request.method,
                    protocol="REST",
                    status_code=status_code,
                    duration_ms=duration_ms,
                    user_id=user_id,
                )
            except Exception:
                logger.exception("Failed to persist RequestLog")
