import pytest
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from agentic_service_py_template.models import Base, AiObservabilityLog


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite://", echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine)() as s:
        yield s
    await engine.dispose()


@pytest.mark.asyncio
async def test_create_ai_observability_log(session):
    log = AiObservabilityLog(
        feature_name="investment_summary",
        user_id="100",
        request="test prompt",
        response="test response",
        input_tokens=10,
        output_tokens=20,
        total_tokens=30,
        requested_at_utc=datetime.now(timezone.utc),
        responded_at_utc=datetime.now(timezone.utc),
    )
    session.add(log)
    await session.commit()
    await session.refresh(log)
    assert log.id is not None
    assert log.feature_name == "investment_summary"  # type: ignore[operator]


@pytest.mark.asyncio
async def test_investment_summary():
    from agentic_service_py_template.models import InvestmentSummary
    summary = InvestmentSummary(
        summary_highlights=["Good location", "Strong rental demand"],
        risk_factors=["High property tax"],
        investment_profile="Moderate risk",
    )
    assert len(summary.summary_highlights) == 2
    assert summary.investment_profile == "Moderate risk"
