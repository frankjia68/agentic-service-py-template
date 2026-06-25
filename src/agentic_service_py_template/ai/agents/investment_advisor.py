import json
import logging
from collections.abc import Callable
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.base import BaseCheckpointSaver
from litellm import acompletion

from agentic_service_py_template.ai.tools import ALL_TOOLS, TOOL_DEFINITIONS
from agentic_service_py_template.config import Settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a helpful real estate advisor. Use the available tools to answer "
    "the user's questions about properties, MLS listings, and weather. If you "
    "don't know the answer or don't have the right tool to find it, say so "
    "honestly. Do not make up information or hallucinate — only state what you "
    "can verify from tool outputs."
)

MAX_ITERATIONS = 10


_ROLE_MAP = {
    "human": "user",
    "ai": "assistant",
    "system": "system",
    "tool": "tool",
}


def _messages_to_openai(messages: list[BaseMessage]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for m in messages:
        entry: dict[str, Any] = {"role": _ROLE_MAP.get(m.type, m.type), "content": m.content}
        if m.type == "ai" and hasattr(m, "tool_calls") and m.tool_calls:
            entry["tool_calls"] = [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": json.dumps(tc["args"]),
                    },
                }
                for tc in m.tool_calls
            ]
        if m.type == "tool":
            assert isinstance(m, ToolMessage)
            entry["tool_call_id"] = m.tool_call_id
        result.append(entry)
    return result


async def _agent_node(state: MessagesState) -> dict[str, list[BaseMessage]]:
    openai_messages = _messages_to_openai(state["messages"])
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *openai_messages,
    ]
    settings = Settings()
    response = await acompletion(
        model=settings.llm_model,
        messages=messages,
        tools=TOOL_DEFINITIONS,
    )
    choice = response.choices[0].message
    content = choice.content or ""
    raw_tool_calls = choice.tool_calls or []

    if raw_tool_calls:
        tool_calls = [
            {
                "name": tc.function.name,
                "args": json.loads(tc.function.arguments),
                "id": tc.id,
                "type": "tool_call",
            }
            for tc in raw_tool_calls
        ]
        ai_msg = AIMessage(content=content, tool_calls=tool_calls)
    else:
        ai_msg = AIMessage(content=content)

    return {"messages": [ai_msg]}


def should_continue(state: MessagesState) -> str:
    last = state["messages"][-1]
    if not last.tool_calls:
        return END
    tool_rounds = sum(1 for m in state["messages"] if hasattr(m, "tool_call_id"))
    if tool_rounds >= MAX_ITERATIONS:
        return END
    return "tools"


def create_investment_advisor_graph(
    *,
    tools: list[Callable[..., Any]] = ALL_TOOLS,
    checkpointer: BaseCheckpointSaver | None = None,
) -> CompiledStateGraph:
    builder = StateGraph(MessagesState)
    builder.add_node("agent", _agent_node)
    builder.add_node("tools", ToolNode(tools))
    builder.add_conditional_edges("agent", should_continue)
    builder.add_edge("tools", "agent")
    builder.set_entry_point("agent")
    return builder.compile(checkpointer=checkpointer)
