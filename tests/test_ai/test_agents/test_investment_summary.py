import json
from unittest.mock import AsyncMock, patch

import pytest

from agentic_service_py_template.ai.agents.investment_summary import (
    InvestmentSummaryState,
    create_investment_summary_graph,
    router,
)
from agentic_service_py_template.models import InvestmentSummary


class _MockMessage:
    def __init__(self, content: str):
        self.content = content


class _MockChoice:
    def __init__(self, content: str):
        self.message = _MockMessage(content)


class _MockResponse:
    def __init__(self, content: str):
        self.choices = [_MockChoice(content)]


_VALID_SUMMARY = {
    "summary_highlights": [
        "Prime location near downtown",
        "Strong rental demand",
        "Recent renovations",
    ],
    "risk_factors": [
        "Property tax increase risk",
        "Aging HVAC system",
    ],
    "investment_profile": "Moderate growth with steady cash flow",
}
_VALID_JSON = json.dumps(_VALID_SUMMARY)


def test_state_typeddict_fields():
    annotations = InvestmentSummaryState.__annotations__
    assert "supply_id" in annotations
    assert annotations["supply_id"] is str
    assert "summary" in annotations
    assert "error" in annotations
    assert "attempts" in annotations
    assert annotations["attempts"] is int


def test_create_graph_compiled():
    graph = create_investment_summary_graph()
    assert hasattr(graph, "ainvoke")


def test_router_routes_to_end_on_success():
    state: InvestmentSummaryState = {
        "supply_id": "test",
        "summary": InvestmentSummary(
            summary_highlights=["ok"],
            risk_factors=[],
            investment_profile="moderate",
        ),
        "error": None,
        "attempts": 1,
    }
    assert router(state) == "__end__"


def test_router_routes_to_retry_on_error_under_limit():
    state: InvestmentSummaryState = {
        "supply_id": "test",
        "summary": None,
        "error": "invalid json",
        "attempts": 1,
    }
    assert router(state) == "generate_summary"


def test_router_routes_to_end_on_max_retries():
    state: InvestmentSummaryState = {
        "supply_id": "test",
        "summary": None,
        "error": "invalid json",
        "attempts": 3,
    }
    assert router(state) == "__end__"


@pytest.mark.asyncio
async def test_happy_path_returns_summary():
    with patch(
        "agentic_service_py_template.ai.agents.investment_summary.acompletion",
        new_callable=AsyncMock,
    ) as mock_completion:
        mock_completion.return_value = _MockResponse(_VALID_JSON)
        graph = create_investment_summary_graph()
        result = await graph.ainvoke({"supply_id": "MLS-456"})

        assert result["summary"] is not None
        assert result["error"] is None
        assert result["summary"].summary_highlights == _VALID_SUMMARY["summary_highlights"]
        assert result["summary"].investment_profile == _VALID_SUMMARY["investment_profile"]
        assert result["attempts"] == 1


@pytest.mark.asyncio
async def test_retry_on_invalid_json_then_success():
    with patch(
        "agentic_service_py_template.ai.agents.investment_summary.acompletion",
        new_callable=AsyncMock,
    ) as mock_completion:
        mock_completion.side_effect = [
            _MockResponse("not valid json"),
            _MockResponse("also not valid"),
            _MockResponse(_VALID_JSON),
        ]
        graph = create_investment_summary_graph()
        result = await graph.ainvoke({"supply_id": "MLS-789"})

        assert result["summary"] is not None
        assert result["summary"].summary_highlights == _VALID_SUMMARY["summary_highlights"]
        assert result["attempts"] == 3


@pytest.mark.asyncio
async def test_max_retries_exceeded():
    with patch(
        "agentic_service_py_template.ai.agents.investment_summary.acompletion",
        new_callable=AsyncMock,
    ) as mock_completion:
        mock_completion.side_effect = [
            _MockResponse("bad json"),
            _MockResponse("bad json again"),
            _MockResponse("still bad"),
        ]
        graph = create_investment_summary_graph()
        result = await graph.ainvoke({"supply_id": "MLS-999"})

        assert result["summary"] is None
        assert result["error"] is not None
        assert result["attempts"] == 3
