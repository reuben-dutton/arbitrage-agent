import logging
import os

import sqlalchemy
from sqlalchemy.orm import scoped_session, sessionmaker
from taskiq import AsyncBroker, InMemoryBroker, TaskiqEvents, TaskiqState
from taskiq_aio_pika import AioPikaBroker
from taskiq_pipelines import PipelineMiddleware
from taskiq_redis import RedisAsyncResultBackend

import config
from src.web.client import ClientSettings, RateLimitedClient
from src.database.models import DatabaseModel


logging.basicConfig(
    filename="logs/main.log",
    level=logging.getLevelName("INFO"),
    format=(
        "[%(asctime)s][%(name)s]" "[%(levelname)-7s][%(processName)s]" " %(message)s"
    ),
)
logger = logging.getLogger(__name__)

env = os.environ.get("ENVIRONMENT")


broker: AsyncBroker = AioPikaBroker(
    config.RABBITMQ_URL,
).with_result_backend(RedisAsyncResultBackend(config.REDIS_URL))

if env and env == "pytest":  # use memory broker for testing
    broker = InMemoryBroker()

broker.add_middlewares(PipelineMiddleware())  # for pipelines


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def startup(state: TaskiqState) -> None:
    clientSettings = ClientSettings(config.GLOBAL_RATE_LIMIT, config.DOMAIN_RATE_LIMIT)
    # maximum concurrent requests per worker
    clientSettings.set_global_concurrency(config.GLOBAL_CONCURRENCY_LIMIT)
    # maximum concurrent requests per TLD
    clientSettings.set_domain_concurrency(config.DOMAIN_CONCURRENCY_LIMIT)
    # maximum retry per request
    clientSettings.max_retries = config.MAX_RETRIES_PER_REQUEST
    # create httpx.AsyncClient with rate limits
    state.client = RateLimitedClient(clientSettings)
    logger.info("HTTP client opened (%s).", type(state.client))
    logger.info("Rate limits: %s", clientSettings)

    if not config.USING_DATABASE:
        return

    engine = sqlalchemy.create_engine(config.DATABASE_CONNECT_STRING)

    DatabaseModel.metadata.create_all(engine)

    logger.info(
        "Database engine created, connected to %s",
        config.DATABASE_CONNECT_STRING,
    )

    state.session = scoped_session(sessionmaker(bind=engine))
    logger.info("Database session opened.")


@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def shutdown(state: TaskiqState) -> None:
    if hasattr(state, "client"):
        await state.client.aclose()
        logger.info("HTTP client closed (%s).", type(state.client))
    else:
        logger.info("No HTTP client found. Continuing...")

    if hasattr(state, "session"):
        state.session.close()
        logger.info("Database session closed.")
    else:
        logger.info("No database session found. Continuing...")
