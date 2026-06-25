"""Azure Functions sample blueprints bundled with the agentic-service-py-template repository."""

from agentic_service_py_template.azure_functions.health_check_timer import bp as health_check_bp
from agentic_service_py_template.azure_functions.queue_processor import bp as queue_processor_bp

__all__ = [
    "health_check_bp",
    "queue_processor_bp",
]
