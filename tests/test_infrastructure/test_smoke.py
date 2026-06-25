"""Smoke tests — verify the agentic_service_py_template package is importable."""

import importlib
import sys

import pytest

# All subpackages in our source tree
OUR_PACKAGES = [
    "agentic_service_py_template",
    "agentic_service_py_template.ai",
    "agentic_service_py_template.api",
    "agentic_service_py_template.azure_functions",
]


@pytest.mark.parametrize("module_name", OUR_PACKAGES)
def test_package_imports(module_name: str):
    """Each agentic_service_py_template subpackage must import without errors."""
    sys.modules.pop(module_name, None)
    mod = importlib.import_module(module_name)
    assert mod is not None
    assert hasattr(mod, "__name__")
    assert hasattr(mod, "__file__")
    assert mod.__name__ == module_name


def test_package_surface_describes_template_intent():
    package = importlib.import_module("agentic_service_py_template")
    ai_package = importlib.import_module("agentic_service_py_template.ai")
    api_package = importlib.import_module("agentic_service_py_template.api")
    main_package = importlib.import_module("agentic_service_py_template.main")

    assert package.__title__ == "agentic-service-py-template"
    assert package.__summary__ == "Sample implementation package for the agentic-service-py-template repository."
    assert "sample implementation" in (package.__doc__ or "").lower()

    assert hasattr(package, "Base")
    assert hasattr(package, "InvestmentSummary")
    assert hasattr(ai_package, "ALL_TOOLS")
    assert hasattr(ai_package, "TOOL_DEFINITIONS")
    assert hasattr(api_package, "create_router")
    assert hasattr(api_package, "add_auth_middleware")
    assert hasattr(api_package, "add_observability_middleware")
    assert hasattr(main_package, "create_app")
    assert hasattr(main_package, "default_app_plugins")
