import json
import logging
from typing import TypedDict

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from litellm import acompletion

from agentic_service_py_template.config import Settings
from agentic_service_py_template.models import InvestmentSummary

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a real estate investment advisor. Analyze the given property and provide "
    "an investment summary.\n\n"
    'Return a JSON object with these fields:\n'
    '- "summary_highlights": list of strings — key positive points about the property\n'
    '- "risk_factors": list of strings — potential risks or concerns\n'
    '- "investment_profile": string — overall investment recommendation '
    '(e.g. "Conservative growth", "Moderate growth with steady cash flow")\n\n'
    "Return ONLY valid JSON. No additional text."
)

MAX_RETRIES = 3


class InvestmentSummaryState(TypedDict):
    supply_id: str
    summary: InvestmentSummary | None
    error: str | None
    attempts: int


async def generate_summary(state: InvestmentSummaryState) -> dict:
    prev_attempts = state.get("attempts", 0)
    prev_error = state.get("error")
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Analyze property supply_id: {state['supply_id']}",
        },
    ]
    if prev_attempts > 0:
        messages.append({
            "role": "user",
            "content": (
                f"Your previous response had invalid JSON: {prev_error}. "
                "Fix it and return valid JSON only."
            ),
        })
    settings = Settings()
    response = await acompletion(
        model=settings.llm_model,
        messages=messages,
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content or ""
    attempts = prev_attempts + 1
    try:
        data = json.loads(content)
        summary = InvestmentSummary.model_validate(data)
        return {"summary": summary, "error": None, "attempts": attempts}
    except (json.JSONDecodeError, Exception) as e:
        logger.warning("Failed to parse LLM response (attempt %d/{%d}): %s", attempts, MAX_RETRIES, e)
        return {"summary": None, "error": str(e), "attempts": attempts}


def router(state: InvestmentSummaryState) -> str:
    if state["summary"] is not None:
        return END
    if state["attempts"] < MAX_RETRIES:
        return "generate_summary"
    return END


def create_investment_summary_graph() -> CompiledStateGraph:
    builder = StateGraph(InvestmentSummaryState)
    builder.add_node("generate_summary", generate_summary)
    builder.add_conditional_edges("generate_summary", router)
    builder.set_entry_point("generate_summary")
    return builder.compile()
