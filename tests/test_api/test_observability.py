import pytest
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from agentic_service_py_template.models import Base, RequestLog
from agentic_service_py_template.api.observability import (
    get_correlation_id,
    generate_correlation_id,
    _persist_request_log,
)


@pytest.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite://", echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine)
    yield factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_generate_correlation_id_returns_uuid_string():
    cid = generate_correlation_id()
    assert isinstance(cid, str)
    assert len(cid) == 36


@pytest.mark.asyncio
async def test_generate_correlation_id_sets_contextvar():
    cid = generate_correlation_id()
    assert get_correlation_id() == cid


@pytest.mark.asyncio
async def test_get_correlation_id_returns_none_when_not_set():
    assert get_correlation_id() is None


@pytest.mark.asyncio
async def test_persist_request_log_creates_entry(session_factory):
    cid = "test-correlation-id"
    now = datetime.now(timezone.utc)
    await _persist_request_log(
        session_factory=session_factory,
        correlation_id=cid,
        endpoint="/rest/health-check",
        method="GET",
        protocol="REST",
        status_code=200,
        duration_ms=42,
        user_id="test-user",
    )
    async with session_factory() as session:
        result = await session.get(RequestLog, 1)
    assert result is not None
    assert result.correlation_id == cid
    assert result.endpoint == "/rest/health-check"
    assert result.method == "GET"
    assert result.protocol == "REST"
    assert result.status_code == 200
    assert result.duration_ms == 42
    assert result.user_id == "test-user"
    assert result.requested_at_utc is not None


@pytest.mark.asyncio
async def test_persist_request_log_minimal(session_factory):
    await _persist_request_log(
        session_factory=session_factory,
        correlation_id="cid-123",
        endpoint="/test",
        method="POST",
    protocol="REST",
    status_code=200,
        duration_ms=100,
    )
    async with session_factory() as session:
        result = await session.get(RequestLog, 1)
    assert result is not None
    assert result.user_id is None
