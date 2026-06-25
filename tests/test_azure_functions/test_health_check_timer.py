import logging

import pytest


class MockTimerRequest:
    def __init__(self, past_due: bool = False) -> None:
        self.past_due = past_due


@pytest.mark.asyncio
async def test_timer_triggers_when_not_past_due(caplog: pytest.LogCaptureFixture) -> None:
    from agentic_service_py_template.azure_functions.health_check_timer import health_check_timer

    caplog.set_level(logging.INFO)
    timer = MockTimerRequest(past_due=False)

    health_check_timer(timer)

    assert "Health check OK" in caplog.text
    assert "running late" not in caplog.text


@pytest.mark.asyncio
async def test_timer_logs_warning_when_past_due(caplog: pytest.LogCaptureFixture) -> None:
    from agentic_service_py_template.azure_functions.health_check_timer import health_check_timer

    caplog.set_level(logging.WARNING)
    timer = MockTimerRequest(past_due=True)

    health_check_timer(timer)

    assert "running late" in caplog.text


@pytest.mark.asyncio
async def test_blueprint_is_exported() -> None:
    from agentic_service_py_template.azure_functions.health_check_timer import bp

    assert bp is not None
    assert bp.timer_trigger is not None


@pytest.mark.asyncio
async def test_function_app_can_register_blueprint() -> None:
    import function_app

    assert function_app.app is not None
