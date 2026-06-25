import json
from unittest.mock import AsyncMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from agentic_service_py_template.ai.agents.investment_advisor import (
    _messages_to_openai,
    create_investment_advisor_graph,
    should_continue,
)
from agentic_service_py_template.ai.tools import ALL_TOOLS


# ─── Mock classes for litellm responses ────────────────────────────

class _MockToolCallFunction:
    def __init__(self, name: str, arguments: str):
        self.name = name
        self.arguments = arguments


class _MockToolCall:
    def __init__(self, id: str, name: str, arguments: str):
        self.id = id
        self.function = _MockToolCallFunction(name, arguments)
        self.type = "function"


class _MockMessage:
    def __init__(self, content: str | None = None, tool_calls: list | None = None):
        self.content = content
        self.tool_calls = tool_calls or []


class _MockChoice:
    def __init__(self, message: _MockMessage):
        self.message = message


class _MockResponse:
    def __init__(self, content: str | None = None, tool_calls: list | None = None):
        self.choices = [_MockChoice(_MockMessage(content=content, tool_calls=tool_calls))]


# ─── _messages_to_openai tests ─────────────────────────────────────

def test_messages_to_openai_converts_human():
    result = _messages_to_openai([HumanMessage(content="hello")])
    assert result == [{"role": "user", "content": "hello"}]


def test_messages_to_openai_converts_ai():
    result = _messages_to_openai([AIMessage(content="hi there")])
    assert result == [{"role": "assistant", "content": "hi there"}]


def test_messages_to_openai_converts_ai_with_tool_calls():
    msg = AIMessage(
        content="",
        tool_calls=[{
            "name": "get_weather",
            "args": {"location": "Austin, TX"},
            "id": "call_1",
            "type": "tool_call",
        }],
    )
    result = _messages_to_openai([msg])
    assert len(result) == 1
    entry = result[0]
    assert entry["role"] == "assistant"
    assert entry["tool_calls"] == [
        {
            "id": "call_1",
            "type": "function",
            "function": {
                "name": "get_weather",
                "arguments": '{"location": "Austin, TX"}',
            },
        }
    ]


def test_messages_to_openai_converts_system():
    result = _messages_to_openai([SystemMessage(content="be helpful")])
    assert result == [{"role": "system", "content": "be helpful"}]


def test_messages_to_openai_converts_tool():
    msg = ToolMessage(content='{"temp": 75}', tool_call_id="call_1")
    result = _messages_to_openai([msg])
    assert result == [{"role": "tool", "content": '{"temp": 75}', "tool_call_id": "call_1"}]


# ─── should_continue tests ─────────────────────────────────────────

def test_should_continue_ends_when_no_tool_calls():
    state = {"messages": [AIMessage(content="hello")]}
    assert should_continue(state) == "__end__"


def test_should_continue_routes_to_tools():
    state = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[{"name": "get_weather", "args": {}, "id": "1", "type": "tool_call"}],
            )
        ]
    }
    assert should_continue(state) == "tools"


def test_should_continue_ends_at_max_iterations():
    messages: list = []
    for i in range(10):
        messages.append(
            AIMessage(
                content=f"round{i}",
                tool_calls=[{"name": "get_weather", "args": {}, "id": str(i), "type": "tool_call"}],
            )
        )
        messages.append(ToolMessage(content="result", tool_call_id=str(i)))
    messages.append(
        AIMessage(
            content="",
            tool_calls=[{"name": "get_weather", "args": {}, "id": "10", "type": "tool_call"}],
        )
    )
    state = {"messages": messages}
    assert should_continue(state) == "__end__"


# ─── Factory tests ─────────────────────────────────────────────────

def test_create_graph_returns_compiled():
    graph = create_investment_advisor_graph()
    assert hasattr(graph, "ainvoke")


def test_create_graph_with_checkpointer():
    from langgraph.checkpoint.sqlite import SqliteSaver

    with SqliteSaver.from_conn_string(":memory:") as checkpointer:
        graph = create_investment_advisor_graph(checkpointer=checkpointer)
        assert graph.checkpointer is not None


# ─── Integration tests (mocked LLM) ────────────────────────────────

@pytest.mark.asyncio
async def test_agent_responds_without_tools():
    with patch(
        "agentic_service_py_template.ai.agents.investment_advisor.acompletion",
        new_callable=AsyncMock,
    ) as mock_acompletion:
        mock_acompletion.return_value = _MockResponse(content="Hello! How can I help?")
        graph = create_investment_advisor_graph()
        result = await graph.ainvoke({"messages": [HumanMessage(content="hi")]})

        messages = result["messages"]
        assert len(messages) == 2
        assert messages[0].content == "hi"
        assert "Hello" in messages[-1].content


@pytest.mark.asyncio
async def test_agent_calls_tool_then_responds():
    with patch(
        "agentic_service_py_template.ai.agents.investment_advisor.acompletion",
        new_callable=AsyncMock,
    ) as mock_acompletion:
        mock_acompletion.side_effect = [
            _MockResponse(tool_calls=[
                _MockToolCall(
                    id="call_1",
                    name="get_weather",
                    arguments='{"location": "Austin, TX"}',
                ),
            ]),
            _MockResponse(content="The weather in Austin is sunny and 78°F."),
        ]
        graph = create_investment_advisor_graph()
        result = await graph.ainvoke({
            "messages": [HumanMessage(content="What is the weather in Austin?")]
        })

        messages = result["messages"]
        assert len(messages) >= 3
        assert "Austin" in messages[-1].content


@pytest.mark.asyncio
async def test_graph_with_checkpointer_persists_state():
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    async with AsyncSqliteSaver.from_conn_string(":memory:") as checkpointer:
        graph = create_investment_advisor_graph(checkpointer=checkpointer)

        with patch(
            "agentic_service_py_template.ai.agents.investment_advisor.acompletion",
            new_callable=AsyncMock,
        ) as mock_acompletion:
            mock_acompletion.side_effect = [
                _MockResponse(content="I am fine."),
                _MockResponse(content="Sure, here you go."),
            ]
            config = {"configurable": {"thread_id": "test-thread-1"}}
            await graph.ainvoke(
                {"messages": [HumanMessage(content="How are you?")]},
                config,
            )
            result2 = await graph.ainvoke(
                {"messages": [HumanMessage(content="Tell me more.")]},
                config,
            )

            messages = result2["messages"]
            assert len(messages) == 4
            assert messages[0].content == "How are you?"
            assert messages[2].content == "Tell me more."
