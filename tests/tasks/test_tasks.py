
import pytest
import respx
from taskiq import Context

from src.tasks_example import make_request
from src.tasks import get_bookmakers, get_sports, get_contests
from tests import utils
from src.database.models import (
    Bookmaker,
    OutcomeRecord,
    ReferenceContest,
    ReferenceEvent,
    ReferenceMarket,
    ReferenceOutcome,
    ReferenceSport,
    SourceContest,
    SourceEvent,
    SourceSport,
)


def populate_database(session):
    b = [
        Bookmaker("Sportsbet"),
        Bookmaker("TAB"),
    ]
    s = []
    s.append(ReferenceSport(b[0], refnum="16", refname="Basketball - US"))
    s.append(ReferenceSport(b[0], refnum="25", refname="Cricket"))
    s.append(ReferenceSport(b[0], refnum="23", refname="Rugby League"))

    s.append(ReferenceSport(b[1], refnum="4", refname="Basketball"))
    s.append(ReferenceSport(b[1], refnum="2", refname="Cricket"))
    s.append(ReferenceSport(b[1], refnum="10", refname="Rugby League"))

    session.add_all(b + s)
    session.commit()


@respx.mock
@pytest.mark.anyio
async def test_make_request_unlimited(monkeypatch, unlimited_client, dbsession):
    server_response = utils.construct_delayed_response(0)

    respx.get("https://httpbin.org/get").mock(side_effect=server_response)

    def get_client(context: Context):
        return unlimited_client

    def get_session(context: Context):
        return dbsession

    monkeypatch.setattr("src.worker.dependencies.get_client", get_client)
    monkeypatch.setattr("src.worker.dependencies.get_session", get_session)

    tasks = []

    for _ in range(10):
        tasks.append(await make_request.kiq("https://httpbin.org/get"))

    for task in tasks:
        result = await task.wait_result()

    assert result.return_value.status_code == 200


@pytest.mark.anyio
async def test_get_bookmakers(monkeypatch, dbsession):
    populate_database(dbsession)

    def get_session(context: Context):
        return dbsession

    monkeypatch.setattr("src.worker.dependencies.get_session", get_session)

    task = await get_bookmakers.kiq()
    result = await task.wait_result()

    assert len(result.return_value) == 2


@pytest.mark.anyio
async def test_get_sports(monkeypatch, dbsession):
    populate_database(dbsession)

    def get_session(context: Context):
        return dbsession

    monkeypatch.setattr("src.worker.dependencies.get_session", get_session)

    task = await get_sports.kiq()
    result = await task.wait_result()

    print(result.return_value[0])


@pytest.mark.anyio
async def test_get_contests(monkeypatch, caching_client, dbsession):
    populate_database(dbsession)

    def get_client(context: Context):
        return caching_client

    def get_session(context: Context):
        return dbsession

    monkeypatch.setattr("src.worker.dependencies.get_client", get_client)
    monkeypatch.setattr("src.worker.dependencies.get_session", get_session)

    task = await get_sports.kiq()
    result = await task.wait_result()
    sports = result.return_value

    tasks = []

    assert dbsession.query(ReferenceContest).count() == 0

    for sport in sports:
        tasks.append(await get_contests.kiq(sport))

    for task in tasks:
        await task.wait_result()

    assert dbsession.query(ReferenceContest).count() > 0
