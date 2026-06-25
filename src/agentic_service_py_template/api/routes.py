import logging

from fastapi import APIRouter, Request
from langchain_core.messages import HumanMessage
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

logger = logging.getLogger(__name__)


class InvestmentSummaryRequest(BaseModel):
    supply_id: str


class ChatStreamRequest(BaseModel):
    message: str
    thread_id: str


def create_router() -> APIRouter:
    router = APIRouter()

    @router.get("/api/health")
    async def health():
        return {"status": "ok"}

    @router.post("/api/investment-summary")
    async def investment_summary(body: InvestmentSummaryRequest, request: Request):
        graph = request.app.state.summary_graph
        result = await graph.ainvoke({"supply_id": body.supply_id})
        return {
            "summary": result["summary"].model_dump() if result["summary"] else None,
            "error": result["error"],
            "attempts": result["attempts"],
        }

    @router.post("/api/chat/stream")
    async def chat_stream(body: ChatStreamRequest, request: Request):
        graph = request.app.state.advisor_graph

        async def event_generator():
            config = {"configurable": {"thread_id": body.thread_id}}
            input_state = {"messages": [HumanMessage(content=body.message)]}

            try:
                async for event in graph.astream_events(input_state, config, version="v1"):  # type: ignore[arg-type]
                    event_type = event["event"]
                    if event_type == "on_chat_model_stream":
                        chunk = event["data"].get("chunk")
                        content = getattr(chunk, "content", "") or ""
                        if content:
                            yield {"event": "token", "data": content}
                    elif event_type == "on_tool_start":
                        yield {"event": "tool_start", "data": event.get("name", "")}
                    elif event_type == "on_tool_end":
                        yield {"event": "tool_end", "data": event.get("name", "")}
            except Exception:
                logger.exception("Error streaming chat response")
                yield {"event": "error", "data": "Internal streaming error"}

            yield {"event": "done", "data": ""}

        return EventSourceResponse(event_generator())

    return router