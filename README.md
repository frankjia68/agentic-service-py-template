# agentic-service-py-template — A Structured Project Template for Agentic Python Services

![tests](https://img.shields.io/badge/tests-88%2F88%20passing-brightgreen)
![python](https://img.shields.io/badge/python-3.14-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.x-009688)
![LangGraph](https://img.shields.io/badge/LangGraph-0.x-ff69b4)
![uv](https://img.shields.io/badge/uv-package--manager-purple)

> **A reference implementation and project template for building agentic REST services in Python,
> borrowing established service patterns from the .NET ecosystem (ASP.NET Core, middleware
> pipelines, composition roots, dependency-injection thinking) — but without the boilerplate.**

---

## What is this?

Most agentic Python projects grow organically — agent logic bleeds into routes, tools are
scattered across files, settings hide in ad hoc modules, and observability is bolted on after
the first production incident. This template gives the service a recognizable shape early:
HTTP edges, middleware, application composition, agent orchestration, tool adapters,
persistence, and tests each have a clear home.

**It is not a framework.** It is a working example of one proven approach to organizing an
agentic Python service. The intent is to provide a practical starting structure inspired by
the modularity, SOLID boundaries, and DRY conventions that mature .NET service codebases tend
to rely on. Fork it, adapt it, discard the parts that don't fit your needs.

It is also a work in progress and a set of living architecture notes. Part of the purpose is
to document the author's learning path while translating a .NET service architecture mental
model into idiomatic Python: composition instead of a DI container, FastAPI middleware instead
of ASP.NET Core middleware, LangGraph agents instead of application services, and tool modules
instead of typed infrastructure adapters.

The current `src/agentic_service_py_template/` package intentionally ships with an
investment/property-themed sample implementation. Treat those domain-specific names, routes,
and tools as placeholders that demonstrate the template structure, not as the canonical
identity of the repository.

In this repository, "plugin based" primarily means composable Python middleware and
application components in the same spirit as the .NET middleware pipeline.

---

## Why a layered structure?

| Principle | What it means here |
|-----------|-------------------|
| **Single responsibility by module** | Routes handle HTTP, agents orchestrate use cases, tools adapt external APIs, models own persistence contracts. |
| **One-way dependency flow** | `API → AI Agents → Tools/LLM → Data`. No circular imports, no shortcuts across layers. |
| **Composition root** | `main.py` owns app construction, lifespan resources, middleware registration, and sample agent wiring. |
| **Plugin-style composition** | Middleware and explicit app wiring act as pluggable components, similar to the ASP.NET Core request pipeline model. |
| **Replaceable adapters** | LLM providers, tools, auth, observability, and storage can change behind stable module boundaries. |
| **Testability at every boundary** | Each layer can be mocked or substituted independently; tests prove the contracts. |
| **DRY conventions** | Shared concerns such as config, auth, observability, and persistence live in one place instead of being copied into each route or agent. |
| **Configuration by environment** | All settings load from `ASPT_`-prefixed env vars (or `.env`); no code changes to switch environments. |

---

## Architecture at a glance

```
┌────────────────────────────────────────────────────────────┐
│  Presentation   FastAPI routes, SSE streaming, request DTOs│
├────────────────────────────────────────────────────────────┤
│  Auth            JWT middleware (Bearer token validation)   │
├────────────────────────────────────────────────────────────┤
│  Observability   correlation_id, RequestLog, AiObsLog     │
├────────────────────────────────────────────────────────────┤
│  AI Agents       LangGraph state machines (2 graphs)       │
├────────────────────────────────────────────────────────────┤
│  Tool / LLM      litellm, 3 mock tools (→ swap for real)  │
├────────────────────────────────────────────────────────────┤
│  Data            SQLAlchemy async + SQLite + Alembic       │
└────────────────────────────────────────────────────────────┘
```

Each layer depends only on the layer below it (or on external libraries). The observability
layer cuts across all layers via `contextvars`, linking HTTP request logs to LLM telemetry
without coupling them directly.

> For the full architecture, component diagrams, and workflow details,
> see [`docs/architecture.md`](docs/architecture.md).

---

## Project layout

The files under `src/agentic_service_py_template/` are the bundled sample implementation that
comes with the template today.

```
src/agentic_service_py_template/
│
│   config.py                  Settings — single source of truth, ASPT_-prefixed
│                              (cf. appsettings.json / Options pattern)
│
│   models.py                  SQLAlchemy ORM entities + Pydantic DTOs
│                              (cf. Entities + DTOs separation)
│
│   main.py                    Composition root — wires lifespan, registers
│                              middleware, builds agents, owns the DB engine
│                              (cf. Program.cs / Application.java)
│
├── ai/
│   ├── tools.py               Tool functions + OpenAI schema definitions
│   │                          — swap implementations, keep the interface
│   │
│   ├── observability.py       LangGraph callback → AiObservabilityLog
│   │                          (cf. ILogger<T>)
│   │
│   └── agents/
│       ├── investment_summary.py    Stateless graph — JSON retry loop
│       └── investment_advisor.py    Tool-calling graph with checkpointer
│                                   (one file per agent — new agent = new file)
│
├── api/
│   ├── auth.py                JWT create/verify + FastAPI middleware
│   │                          — add OAuth2, API keys, etc. here
│   │
│   ├── routes.py              Endpoints — thin, delegate to agents
│   │                          (cf. Controller-per-resource)
│   │
│   └── observability.py       FastAPI middleware — request metrics,
│                              correlation_id ContextVar
│
└── azure_functions/
    ├── health_check_timer.py  Timer-triggered health check
    └── queue_processor.py     Queue-triggered message processor
```

---

## Enterprise pattern map

If you come from the .NET world, here is a mapping of familiar service concepts to this project:

| .NET concept | This project's equivalent | Notes |
|---|---|---|
| `appsettings.json` / Options pattern | `config.py` + `ASPT_` env vars | Configuration-by-convention, environment-overridable |
| Dependency injection container | `create_app()` + lifespan + `app.state` | Manual composition root — more lines, less magic, fully explicit |
| Middleware pipeline | FastAPI middleware (auth → observability) | Chain-of-responsibility, composable |
| Controller → Application Service → Adapter | Route → Agent Graph → Tool | Thin controller, use-case orchestrator, external adapter |
| `ILogger<T>` | `ObservabilityCallback` | Structured telemetry, swappable backends |
| Entities → DTOs | SQLAlchemy ORM → Pydantic models | Serialization boundary is explicit and enforced |
| EF Core Migrations | Alembic | Schema versioning, rollback support |

This is not a claim that Python *should* look like .NET — only that the same architectural
concerns (configuration, composition, middleware, adapters, data boundaries, observability)
show up everywhere, and these are one reasonable set of Python-native solutions for each.

---

## Extensibility walkthrough

### Add an app component

1. Define a callable that accepts `FastAPI` and registers middleware, routes, event hooks, or state.
2. Pass it to `create_app(plugins=[...])` in tests or compose it into `default_app_plugins()` for the sample service.
3. Keep the component small and explicit, like an ASP.NET Core middleware or service registration extension.

### Add a new agent

1. Create `src/agentic_service_py_template/ai/agents/my_agent.py` — define a LangGraph `StateGraph`
2. Register it in `main.py` lifespan — store on `app.state.my_agent`
3. Add a route in `api/routes.py` — read from `request.app.state.my_agent`

No other files need to change. Existing agents, tools, and middleware are unaffected.

That is the main template rule: add new behavior by extending the relevant module boundary,
not by threading special cases through unrelated layers.

### Add a new tool

1. Implement your async function in `ai/tools.py`
2. Add its OpenAI schema to `TOOL_DEFINITIONS`
3. The tool-calling agent picks it up automatically via LangGraph's `ToolNode`

### Swap the LLM provider

Change two env vars:

```bash
ASPT_LLM_ENDPOINT=https://your-provider.com/v1
ASPT_LLM_MODEL=your-model-name
ASPT_LLM_API_KEY=your-key
```

No code changes. `litellm` handles the routing.

---

## Quick start

```bash
# Install dependencies
uv sync

# Copy and edit config
cp .env.example .env
# — set ASPT_LLM_API_KEY in .env —

# Run the server
uv run uvicorn agentic_service_py_template.main:app --reload
```

Open <http://localhost:8000/docs> for the Swagger UI.

---

## Configuration

All settings are `ASPT_`-prefixed and load from environment variables or `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `ASPT_DB_CONNECTION_STRING` | `sqlite+aiosqlite:///./agentic_service_py_template.db` | Database URL |
| `ASPT_LLM_ENDPOINT` | `https://models.inference.ai.azure.com` | LLM API endpoint |
| `ASPT_LLM_MODEL` | `gpt-4o-mini` | Model name |
| `ASPT_LLM_API_KEY` | — | LLM API key (uses `${{secrets.GITHUB_TOKEN}}` on GitHub Models) |
| `ASPT_AUTH_JWT_SECRET` | `dev-secret-change-in-prod` | JWT signing key |
| `ASPT_HTTP_HOST` | `0.0.0.0` | Bind address |
| `ASPT_HTTP_PORT` | `8000` | Port |

---

## API

The repository currently includes these sample endpoints as placeholder implementation content:

| Endpoint | Auth | Description |
|----------|------|-------------|
| `GET /api/health` | No | Health check |
| `POST /api/investment-summary` | JWT | Sample endpoint that generates a structured investment summary (`{"supply_id": "..."}`) |
| `POST /api/chat/stream` | JWT | Sample SSE chat endpoint backed by the bundled tool-calling advisor graph (`{"message": "...", "thread_id": "..."}`) |

**Auth:** Obtain a JWT signed with the configured secret and pass it as
`Authorization: Bearer <token>`. The `/api/health` endpoint is anonymous.

---

## Key design decisions

1. **No `AIProvider` ABC** — LangGraph nodes call `litellm.acompletion()` directly; one abstraction fewer, one fewer thing to stub in tests.
2. **No `CacheService`** — session persistence is delegated to LangGraph's built-in `AsyncSqliteSaver`. Reimplementing it would add code without adding value.
3. **No `AgentSessionManager`** — replaced by LangGraph's `thread_id` + checkpointer. The LLM framework owns its own state.
4. **Two-tier observability linked by `contextvars`** — HTTP request logs and LLM audit logs share a `correlation_id`, so you can trace a single user request across all LLM calls it triggered.
5. **Three mock tools, intentionally minimal** — `get_weather`, `get_property_info`, `get_mls_property_raw_data`. They are bundled placeholder examples that demonstrate the pattern; replace them with real API calls for production.

---

## Testing

```bash
uv run pytest              # all tests (88)
uv run pytest -v           # verbose
uv run pytest -k "summary" # filter by name
uv run pytest --cov        # with coverage
```

All async tests use `pytest-asyncio` with `asyncio_mode = "auto"`. Database tests run
against an in-memory SQLite engine. LLM calls are mocked via `unittest.mock.patch`.

---

## Docker

```bash
docker compose up --build
```

Mounts `./data/` for SQLite persistence. Override config via `docker-compose.yml` environment section.

---

## Alembic

```bash
# Create a new migration (autogenerate)
alembic revision --autogenerate -m "description"

# Apply pending migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1
```

---

## Azure Functions

Two timer/queue-triggered functions are defined as blueprints in
`src/agentic_service_py_template/azure_functions/`. Deploy via the Azure Functions Core Tools:

```bash
func start
```

The root `function_app.py` registers both blueprints into the Functions host.

---

## Roadmap

This template is a work in progress. The following areas are planned for gradual addition:

- **CI/CD pipeline** — GitHub Actions workflow for test + lint + build
- **Integration test suite** — end-to-end tests against a running service
- **Deployment guides** — Azure App Service, AWS ECS, and Fly.io examples
- **Docker production profile** — multi-stage build, healthcheck, non-root user
- **Observability backend** — OpenTelemetry export, structured JSON logs
- **Additional agent examples** — multi-step planning agent, RAG agent

Contributions and feedback are welcome.

---

## License

MIT
