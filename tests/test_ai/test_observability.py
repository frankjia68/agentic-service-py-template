import uuid

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from agentic_service_py_template.ai.observability import ObservabilityCallback, redact_pii
from agentic_service_py_template.api.observability import generate_correlation_id
from agentic_service_py_template.models import Base, AiObservabilityLog


# ─── redact_pii tests ─────────────────────────────────────────────

def test_redact_pii_email():
    text = "Contact me at john.doe@example.com"
    result = redact_pii(text)
    assert result is not None
    assert "[EMAIL]" in result
    assert "john.doe@example.com" not in result


def test_redact_pii_phone():
    text = "Call 512-555-0142 for details"
    result = redact_pii(text)
    assert result is not None
    assert "[PHONE]" in result
    assert "512-555-0142" not in result


def test_redact_pii_both():
    text = "Email john@test.com or call 512-555-0142"
    result = redact_pii(text)
    assert result is not None
    assert "[EMAIL]" in result
    assert "[PHONE]" in result


def test_redact_pii_no_pii():
    text = "This is a normal message without any PII"
    result = redact_pii(text)
    assert result == text


def test_redact_pii_none():
    assert redact_pii(None) is None


def test_redact_pii_empty_string():
    assert redact_pii("") == ""


# ─── ObservabilityCallback constructor tests ──────────────────────

def test_callback_handler_has_session_factory():
    handler = ObservabilityCallback(session_factory="fake_factory")
    assert handler.session_factory == "fake_factory"
    assert handler.feature_name == "chat"
    assert handler.user_id == "system"
    assert handler.llm_session_id is None


def test_callback_handler_with_session_id():
    handler = ObservabilityCallback(
        session_factory="fake_factory",
        llm_session_id="thread-abc-123",
    )
    assert handler.llm_session_id == "thread-abc-123"


# ─── _parse_llm_response tests ───────────────────────────────────

def _make_llm_result(text: str, prompt_tokens: int = 10, completion_tokens: int = 20):
    """Create a minimal mock LLMResult for testing."""
    from langchain_core.outputs import LLMResult, Generation

    return LLMResult(
        generations=[[Generation(text=text)]],
        llm_output={
            "token_usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
            }
        },
    )


def test_parse_llm_response_with_tokens():
    response = _make_llm_result("Hello world", prompt_tokens=5, completion_tokens=15)
    pt, ct, req, resp = ObservabilityCallback._parse_llm_response(response, {})
    assert pt == 5
    assert ct == 15
    assert resp == "Hello world"
    assert req == ""


def test_parse_llm_response_no_output():
    from langchain_core.outputs import LLMResult, Generation

    response = LLMResult(generations=[[Generation(text="hi")]])
    pt, ct, req, resp = ObservabilityCallback._parse_llm_response(response, {})
    assert pt == 0
    assert ct == 0
    assert resp == "hi"


def test_parse_llm_response_reads_inputs():
    response = _make_llm_result("")
    pt, ct, req, resp = ObservabilityCallback._parse_llm_response(response, {"inputs": "user prompt"})
    assert req == "user prompt"


def test_parse_llm_response_falls_back_to_prompts():
    response = _make_llm_result("")
    pt, ct, req, resp = ObservabilityCallback._parse_llm_response(response, {"prompts": ["sys prompt"]})
    assert req == "['sys prompt']"


def test_parse_llm_response_empty_generations():
    from langchain_core.outputs import LLMResult, Generation

    response = LLMResult(generations=[[Generation(text="")]])
    pt, ct, req, resp = ObservabilityCallback._parse_llm_response(response, {})
    assert resp == ""


# ─── Enhanced callback tests (on_llm_start / on_llm_end) ─────────

@pytest.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite://", echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine)
    yield factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_on_llm_start_stores_run_data(session_factory):
    handler = ObservabilityCallback(session_factory=session_factory)
    run_id = uuid.uuid4()
    await handler.on_llm_start(
        serialized={},
        prompts=["test prompt"],
        run_id=run_id,
    )
    assert len(handler._run_data) == 1
    assert str(run_id) in handler._run_data
    data = handler._run_data[str(run_id)]
    assert "start_time" in data
    assert "audit_entry_id" in data
    assert uuid.UUID(data["audit_entry_id"])


@pytest.mark.asyncio
async def test_on_llm_end_persists_with_audit_id(session_factory):
    correlation_id = generate_correlation_id()
    handler = ObservabilityCallback(
        session_factory=session_factory,
        feature_name="test-feature",
        user_id="test-user",
        llm_session_id="test-session",
    )
    run_id = uuid.uuid4()
    await handler.on_llm_start(serialized={}, prompts=["hello"], run_id=run_id)
    response = _make_llm_result("world", prompt_tokens=5, completion_tokens=15)
    await handler.on_llm_end(response=response, run_id=run_id)

    async with session_factory() as session:
        result = await session.get(AiObservabilityLog, 1)
    assert result is not None
    assert result.feature_name == "test-feature"
    assert result.user_id == "test-user"
    assert result.input_tokens == 5
    assert result.output_tokens == 15
    assert result.total_tokens == 20
    assert result.llm_session_id == "test-session"
    assert result.correlation_id == correlation_id
    assert result.llm_audit_entry_id is not None
    assert uuid.UUID(result.llm_audit_entry_id)


@pytest.mark.asyncio
async def test_on_llm_end_without_start(session_factory):
    handler = ObservabilityCallback(session_factory=session_factory)
    run_id = uuid.uuid4()
    response = _make_llm_result("no start called")
    await handler.on_llm_end(response=response, run_id=run_id)
    async with session_factory() as session:
        result = await session.get(AiObservabilityLog, 1)
    assert result is not None
    assert result.llm_audit_entry_id is not None


@pytest.mark.asyncio
async def test_on_llm_error_does_not_crash():
    handler = ObservabilityCallback(session_factory="fake")
    run_id = uuid.uuid4()
    # Should not raise any exception
    await handler.on_llm_error(
        Exception("test error"),
        run_id=run_id,
    )


@pytest.mark.asyncio
async def test_on_llm_end_reads_correlation_id_from_contextvars(session_factory):
    cid = generate_correlation_id()
    handler = ObservabilityCallback(session_factory=session_factory)
    run_id = uuid.uuid4()
    await handler.on_llm_start(serialized={}, prompts=["hi"], run_id=run_id)
    response = _make_llm_result("bye")
    await handler.on_llm_end(response=response, run_id=run_id)
    async with session_factory() as session:
        result = await session.get(AiObservabilityLog, 1)
    assert result is not None
    assert result.correlation_id == cid
