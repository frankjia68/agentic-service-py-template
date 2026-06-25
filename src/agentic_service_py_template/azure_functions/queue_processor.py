import json
import logging

import azure.functions as func

logger = logging.getLogger(__name__)

bp = func.Blueprint()


@bp.queue_trigger(arg_name="msg", queue_name="agentic-service-py-template-tasks", connection="AzureWebJobsStorage")
def queue_processor(msg: func.QueueMessage) -> None:
    body = msg.get_body().decode("utf-8")
    logger.info("Queue message received: %s", body)
    try:
        data = json.loads(body)
        logger.info("Processed message payload: %s", data)
    except json.JSONDecodeError:
        logger.error("Invalid JSON in queue message: %s", body)
