"""agentic-service-py-template FastAPI application entry point.

Architecture overview
---------------------
create_app():
    build FastAPI app
    apply app plugins          -> middleware, routes, hooks, app.state
    expose module-level app    -> ASGI server entry point

create_lifespan(settings):
    create engine             -> app.state.session_factory
    create summary graph      -> app.state.summary_graph
    create advisor graph      -> app.state.advisor_graph (with AsyncSqliteSaver)
    yield  <- app serves requests here
    engine.dispose()          <- after all requests drained

api/observability.py:
    add_observability_middleware() - no args
    middleware reads request.app.state.session_factory at request time

api/routes.py:
    create_router() -> APIRouter
    endpoints read request.app.state.summary_graph / advisor_graph

api/auth.py:
    add_auth_middleware() - Bearer JWT check, sets request.state.current_user
"""

import logging
from collections.abc import Callable, Iterable
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from agentic_service_py_template.ai.agents.investment_summary import create_investment_summary_graph
from agentic_service_py_template.ai.agents.investment_advisor import create_investment_advisor_graph
from agentic_service_py_template.api.auth import add_auth_middleware
from agentic_service_py_template.api.observability import add_observability_middleware
from agentic_service_py_template.api.routes import create_router
from agentic_service_py_template.config import Settings
from agentic_service_py_template.models import Base

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

APP_TITLE = "agentic-service-py-template"
AppPlugin = Callable[[FastAPI], None]


def create_lifespan(settings: Settings):
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine = create_async_engine(settings.db_connection_string)
        app.state.session_factory = async_sessionmaker(engine)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        app.state.summary_graph = create_investment_summary_graph()

        async with AsyncSqliteSaver.from_conn_string(settings.db_connection_string) as checkpointer:
            app.state.advisor_graph = create_investment_advisor_graph(checkpointer=checkpointer)
            yield

        await engine.dispose()

    return lifespan


def add_api_routes(app: FastAPI) -> None:
    app.include_router(create_router())


def default_app_plugins() -> tuple[AppPlugin, ...]:
    return (
        add_auth_middleware,
        add_observability_middleware,
        add_api_routes,
    )


def create_app(
    settings: Settings | None = None,
    plugins: Iterable[AppPlugin] | None = None,
) -> FastAPI:
    resolved_settings = settings or Settings()
    app = FastAPI(title=APP_TITLE, lifespan=create_lifespan(resolved_settings))
    app.state.settings = resolved_settings

    for plugin in plugins if plugins is not None else default_app_plugins():
        plugin(app)

    return app


settings = Settings()
app = create_app(settings=settings)

if __name__ == "__main__":
    uvicorn.run(app, host=settings.http_host, port=settings.http_port)
