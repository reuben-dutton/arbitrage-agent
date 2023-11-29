import asyncio
import logging

from src.tasks import (
    add_contests,
    add_events,
    add_markets,
    get_contests,
    get_events,
    get_sports,
)
from src.worker.broker import broker

logging.basicConfig(
    filename="logs/main.log",
    level=logging.getLevelName("INFO"),
    format=(
        "[%(asctime)s][%(name)s]" "[%(levelname)-7s][%(processName)s]" " %(message)s"
    ),
)


async def do_contests():
    task = await get_sports.kiq()
    result = await task.wait_result()
    sports = result.return_value

    tasks = []

    for sport in sports:
        tasks.append(await add_contests.kiq(sport))

    results = []
    for task in tasks:
        results.append(await task.wait_result())

    print(results)


async def do_events():
    task = await get_contests.kiq()
    result = await task.wait_result()
    contests = result.return_value

    tasks = []

    for contest in contests:
        tasks.append(await add_events.kiq(contest))

    results = []
    for task in tasks:
        results.append(await task.wait_result())

    print(results)


async def do_markets():
    task = await get_events.kiq()
    result = await task.wait_result()
    events = result.return_value

    tasks = []

    for event in events:
        tasks.append(await add_markets.kiq(event))

    results = []
    for task in tasks:
        results.append(await task.wait_result())

    print(results)


async def main():
    await broker.startup()

    await do_contests()

    await do_events()

    await do_markets()

    await broker.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
