from taskiq import Context, TaskiqDepends

from src.worker.broker import broker
from src.worker import dependencies


@broker.task
async def make_request(url: str, context: Context = TaskiqDepends()):
    client = dependencies.get_client(context)
    response = await client.get(url)
    return response
