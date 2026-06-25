import json
import logging

import pytest


class MockQueueMessage:
    def __init__(self, body: str) -> None:
        self._body = body.encode("utf-8")

    def get_body(self) -> bytes:
        return self._body


@pytest.mark.asyncio
async def test_queue_processor_processes_valid_json(caplog: pytest.LogCaptureFixture) -> None:
    from agentic_service_py_template.azure_functions.queue_processor import queue_processor

    caplog.set_level(logging.INFO)
    msg = MockQueueMessage(json.dumps({"task": "ping", "payload": {}}))

    queue_processor(msg)

    assert "Queue message received" in caplog.text
    assert "Processed message payload" in caplog.text
    assert "ping" in caplog.text


@pytest.mark.asyncio
async def test_queue_processor_logs_error_on_invalid_json(caplog: pytest.LogCaptureFixture) -> None:
    from agentic_service_py_template.azure_functions.queue_processor import queue_processor

    caplog.set_level(logging.ERROR)
    msg = MockQueueMessage("not valid json")

    queue_processor(msg)

    assert "Invalid JSON" in caplog.text
    assert "not valid json" in caplog.text


@pytest.mark.asyncio
async def test_blueprint_is_exported() -> None:
    from agentic_service_py_template.azure_functions.queue_processor import bp

    assert bp is not None
    assert bp.queue_trigger is not None


@pytest.mark.asyncio
async def test_function_app_can_register_blueprint() -> None:
    import function_app

    assert function_app.app is not None
