"""Azure Functions v2 host entry point.

Usage:
    func start

This registers blueprints from agentic_service_py_template.azure_functions.* into the
Functions host. Deploy as a standalone Function App alongside the FastAPI
service.
"""

import azure.functions as func

from agentic_service_py_template.azure_functions.health_check_timer import bp as health_check_bp
from agentic_service_py_template.azure_functions.queue_processor import bp as queue_processor_bp

app = func.FunctionApp()

app.register_functions(health_check_bp)
app.register_functions(queue_processor_bp)
