import logging
from datetime import datetime, timezone

import azure.functions as func

logger = logging.getLogger(__name__)

bp = func.Blueprint()


@bp.timer_trigger(arg_name="timer", schedule="0 */15 * * * *")
def health_check_timer(timer: func.TimerRequest) -> None:
    if timer.past_due:
        logger.warning("Health check timer is running late")
    logger.info("Health check OK at %s", datetime.now(timezone.utc).isoformat())
