"""
Background task definitions, run via arq (async-native, Redis-backed).

Start the worker with:
    arq app.worker.tasks.WorkerSettings
"""
import logging

from arq.connections import RedisSettings

from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_welcome_email(ctx, user_email: str) -> None:
    """Example task: send a welcome email without blocking the request path."""
    logger.info("Sending welcome email", extra={"email": user_email})
    # TODO: integrate real email provider (SES, Postmark, etc.)


async def startup(ctx) -> None:
    logger.info("Worker starting up")


async def shutdown(ctx) -> None:
    logger.info("Worker shutting down")


class WorkerSettings:
    functions = [send_welcome_email]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
