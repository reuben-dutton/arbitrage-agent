import asyncio
import timeit

import pytest
import respx
from httpx import Response

from tests import utils
from src.web.api.ladbrokes import Ladbrokes
from src.database.models import Bookmaker, ReferenceSport


@pytest.mark.skip
@pytest.mark.anyio
async def test_api(unlimited_client):
    api = Ladbrokes(unlimited_client)
    bookmaker = Bookmaker("Ladbrokes")
    sport = ReferenceSport(bookmaker, refnum="6", refname="Basketball")

    status, response = await api.retrieve_contests(sport)

    contest = response[0]

    status, response = await api.retrieve_events(contest)

    event = response[0]

    status, response = await api.retrieve_markets(event)

    print(response)
