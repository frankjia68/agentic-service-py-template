import logging
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler

from agentic_service_py_template.api.observability import get_correlation_id

logger = logging.getLogger(__name__)

_EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_PATTERN = re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b")


def redact_pii(text: str | None) -> str | None:
    """Replace email addresses and phone numbers with placeholders."""
    if not text:
        return text
    text = _EMAIL_PATTERN.sub("[EMAIL]", text)
    text = _PHONE_PATTERN.sub("[PHONE]", text)
    return text


class ObservabilityCallback(BaseCallbackHandler):
    """LangGraph callback that persists LLM call metadata to ai_observability_log."""

    def __init__(
        self,
        session_factory: Any,
        feature_name: str = "chat",
        user_id: str = "system",
        llm_session_id: str | None = None,
    ):
        self.session_factory = session_factory
        self.feature_name = feature_name
        self.user_id = user_id
        self.llm_session_id = llm_session_id
        self._run_data: dict[str, dict] = {}

    async def on_llm_start(
        self, serialized: dict[str, Any], prompts: list[str], **kwargs: Any
    ) -> None:
        run_id = str(kwargs.get("run_id", ""))
        self._run_data[run_id] = {
            "start_time": time.perf_counter(),
            "audit_entry_id": str(uuid.uuid4()),
        }

    async def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        run_id = str(kwargs.get("run_id", ""))
        run_info = self._run_data.pop(run_id, {})
        start_time = run_info.get("start_time", time.perf_counter())
        audit_entry_id = run_info.get("audit_entry_id") or str(uuid.uuid4())
        duration_ms = int((time.perf_counter() - start_time) * 1000)

        try:
            log_entry = self._build_log_entry(response, kwargs, audit_entry_id, duration_ms)
            async with self.session_factory() as session:
                session.add(log_entry)
                await session.commit()
        except Exception:
            logger.exception("Failed to persist AiObservabilityLog")

    async def on_llm_error(self, error: BaseException, **kwargs: Any) -> None:
        logger.error("LLM call failed: %s", error)

    @staticmethod
    def _parse_llm_response(
        response: Any, kwargs: dict[str, Any]
    ) -> tuple[int, int, str, str]:
        prompt_tokens = 0
        completion_tokens = 0
        if hasattr(response, "llm_output") and response.llm_output:
            token_usage = response.llm_output.get("token_usage", {})
            prompt_tokens = token_usage.get("prompt_tokens", 0)
            completion_tokens = token_usage.get("completion_tokens", 0)

        request_text = ""
        if "inputs" in kwargs:
            request_text = str(kwargs["inputs"])
        elif "prompts" in kwargs:
            request_text = str(kwargs["prompts"])

        response_text = str(response.generations[0][0].text) if response.generations else ""

        return prompt_tokens, completion_tokens, request_text, response_text

    def _build_log_entry(
        self,
        response: Any,
        kwargs: dict[str, Any],
        audit_entry_id: str,
        duration_ms: int,
    ) -> Any:
        from agentic_service_py_template.models import AiObservabilityLog

        prompt_tokens, completion_tokens, request_text, response_text = self._parse_llm_response(response, kwargs)

        return AiObservabilityLog(
            feature_name=self.feature_name,
            user_id=self.user_id,
            request=redact_pii(request_text),
            response=redact_pii(response_text),
            input_tokens=prompt_tokens,
            output_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            requested_at_utc=datetime.now(timezone.utc),
            responded_at_utc=datetime.now(timezone.utc),
            llm_session_id=self.llm_session_id,
            llm_audit_entry_id=audit_entry_id,
            correlation_id=get_correlation_id(),
        )
