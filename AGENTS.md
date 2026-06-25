# agentic-service-py-template - Handoff Plan

## Current State

**88/88 tests passing.** Stack: FastAPI + SSE, litellm + LangGraph, SQLAlchemy async + SQLite.

**Project intention:** this repository is a generic template named `agentic-service-py-template`.
The investment/property terminology that appears under `src/agentic_service_py_template/` is
bundled sample implementation code and should be treated as placeholder example content, not as
the canonical product identity of the repository.

### Existing files

| File | Purpose |
|------|---------|
| `src/agentic_service_py_template/config.py` | Settings - trimmed sample config with `ASPT_` env vars |
| `src/agentic_service_py_template/models.py` | `AiObservabilityLog`, `RequestLog` ORM, `InvestmentSummary` Pydantic |
| `src/agentic_service_py_template/ai/tools.py` | 3 mock sample tools + `TOOL_DEFINITIONS` |
| `src/agentic_service_py_template/ai/observability.py` | `redact_pii()` + `ObservabilityCallback(BaseCallbackHandler)` |
| `src/agentic_service_py_template/api/observability.py` | `contextvars` correlation ID, `_persist_request_log`, `add_observability_middleware(FastAPI)` |
| `src/agentic_service_py_template/ai/agents/investment_summary.py` | `InvestmentSummaryGraph` sample retry loop for structured JSON output |
| `src/agentic_service_py_template/ai/agents/investment_advisor.py` | `InvestmentAdvisorGraph` sample tool-calling agent loop |

### Key design decisions

- No `AIProvider` ABC - LangGraph nodes call `litellm.acompletion()` directly.
- No `CacheService` - LangGraph `AsyncSqliteSaver` handles session persistence.
- No `AgentSessionManager` - replaced by LangGraph `thread_id` + checkpointer.
- Two-tier observability - FastAPI middleware writes `RequestLog`, LangGraph callback writes `AiObservabilityLog`, linked by `correlation_id`.
- Plugin-based in the .NET sense - composable Python middleware and application components provide the extension model.
- Three bundled placeholder tools - weather, property info, MLS raw data.
- REST-only - FastAPI + SSE; no gRPC surface.
- Python 3.14.3 and `uv`.

## Current Guidance

- Keep the repo name, package metadata, service names, and docs aligned to `agentic-service-py-template`.
- Treat the domain-specific graphs, routes, and tools under `src/agentic_service_py_template/` as sample placeholder implementations.
- When updating docs, describe the current investment/property flows as examples unless the task is specifically about those bundled samples.

### Bundled sample implementation

- `InvestmentSummaryGraph`
  - Stateless `StateGraph(dict)` retry loop returning `{"summary": InvestmentSummary | None, "error": str | None, "attempts": int}`.
- `InvestmentAdvisorGraph`
  - Tool-calling `MessagesState` graph with optional `AsyncSqliteSaver` persistence.
- `api/routes.py`
  - Sample endpoints: `/api/health`, `/api/investment-summary`, `/api/chat/stream`.
- `ai/tools.py`
  - Placeholder tools: `get_weather`, `get_property_info`, `get_mls_property_raw_data`.

### Current entrypoint wiring

- `main.py` compiles `InvestmentSummaryGraph` and `InvestmentAdvisorGraph`.
- `create_app(plugins=[...])` is the template's app composition entry point.
- `default_app_plugins()` registers auth middleware, observability middleware, and sample API routes.
- `add_observability_middleware(app)` is registered with no extra arguments.
- Uvicorn starts from `agentic_service_py_template.main:app`.

## Testing conventions

- TDD: test first, watch it fail, implement minimal code, verify green.
- `pytest-asyncio`: `@pytest.mark.asyncio` for async tests, `asyncio_mode = "auto"` in config.
- Mocking: `unittest.mock.patch("litellm.completion")` for LLM calls.
- DB tests: in-memory SQLite (`sqlite+aiosqlite://`), `create_async_engine`, `async_sessionmaker`.
- HTTP tests: `httpx.AsyncClient` + FastAPI `TestClient`.

## Useful commands

```powershell
uv sync                                                     # install project
.\.venv\Scripts\python.exe -m pytest                       # run all tests
.\.venv\Scripts\python.exe -m pytest -v                    # verbose
.\.venv\Scripts\python.exe -m pytest tests/test_ai/test_agents/ -v
```
