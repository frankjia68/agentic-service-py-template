import pytest

from agentic_service_py_template.api.auth import create_system_jwt


@pytest.fixture
def valid_jwt() -> str:
    return create_system_jwt("test-user")


@pytest.fixture
def other_jwt() -> str:
    return create_system_jwt("other-user")