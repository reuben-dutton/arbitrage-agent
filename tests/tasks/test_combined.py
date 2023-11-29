import datetime

import pytest
from sqlalchemy import select

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
        Bookmaker("Ladbrokes")
    ]
    s = []
    s.append(ReferenceSport(b[0], refnum="16", refname="Basketball - US"))
    s.append(ReferenceSport(b[0], refnum="25", refname="Cricket"))
    s.append(ReferenceSport(b[0], refnum="23", refname="Rugby League"))

    s.append(ReferenceSport(b[1], refnum="4", refname="Basketball"))
    s.append(ReferenceSport(b[1], refnum="2", refname="Cricket"))
    s.append(ReferenceSport(b[1], refnum="10", refname="Rugby League"))

    s.append(ReferenceSport(b[2], refnum="6", refname="Basketball"))

    c = []
    c.append(
        ReferenceContest(
            s[0],
            refnum="6927",
            refname="NBA",
            starttime=datetime.datetime(
                2023, 10, 24, 23, 30, tzinfo=datetime.timezone.utc
            ),
        )
    )
    c.append(
        ReferenceContest(
            s[0],
            refnum="2436",
            refname="WNBA Matches",
            starttime=datetime.datetime(
                2023, 9, 24, 17, 0, tzinfo=datetime.timezone.utc
            ),
        )
    )

    c.append(
        ReferenceContest(
            s[3],
            refnum="1001",
            refname="NBA",
            starttime=None,
        )
    )

    c.append(
        ReferenceContest(
            s[6],
            refnum="35",
            refname="Australian NBL",
            starttime=None,
        )
    )

    e = []
    e.append(
        ReferenceEvent(
            c[0],
            refnum="7557976",
            refname="Philadelphia 76ers At Miami Heat",
            starttime=datetime.datetime(
                2023, 12, 26, 1, 10, tzinfo=datetime.timezone.utc
            ),
        )
    )

    e.append(
        ReferenceEvent(
            c[2],
            refnum="DenvLAL",
            refname="Denver v LA Lakers",
            starttime=datetime.datetime(
                2023, 10, 24, 23, 30, tzinfo=datetime.timezone.utc
            ),
        )
    )

    e.append(
        ReferenceEvent(
            c[3],
            refnum="241760482",
            refname="Illawarra Hawks v Sydney Kings",
            starttime=datetime.datetime(
                2023, 9, 30, 10, 00, tzinfo=datetime.timezone.utc
            ),
        )
    )

    session.add_all(b + s + c + e)
    session.commit()


@pytest.mark.anyio
async def test_contests(dbsession, betapi):
    populate_database(dbsession)

    stmt = select(ReferenceSport).where(
        ReferenceSport.bookmaker.has(Bookmaker.name == betapi.__api_name__)
    ).limit(1)
    item = dbsession.scalars(stmt).all()[0]

    response = await betapi.retrieve_contests(item)

    newContests = response[1]

    stmt = select(ReferenceContest)
    existingContests = dbsession.scalars(stmt).all()

    newEntities = list(set(newContests) - set(existingContests))

    dbsession.add_all(newEntities)

    dbsession.commit()

    assert dbsession.query(ReferenceContest).count() > 4


@pytest.mark.anyio
async def test_events(dbsession, betapi):
    populate_database(dbsession)

    stmt = select(ReferenceContest).where(
        ReferenceContest.bookmaker.has(Bookmaker.name == betapi.__api_name__)
    ).limit(1)
    item = dbsession.scalars(stmt).all()[0]

    response = await betapi.retrieve_events(item)

    newEvents = response[1]

    stmt = select(ReferenceEvent)
    existingEvents = dbsession.scalars(stmt).all()

    newEntities = list(set(newEvents) - set(existingEvents))

    dbsession.add_all(newEntities)

    dbsession.commit()

    assert dbsession.query(ReferenceEvent).count() > 3


@pytest.mark.anyio
async def test_markets(dbsession, betapi):
    populate_database(dbsession)

    stmt = select(ReferenceEvent).where(
        ReferenceEvent.bookmaker.has(Bookmaker.name == betapi.__api_name__)
    ).limit(1)
    item = dbsession.scalars(stmt).all()[0]

    response = await betapi.retrieve_markets(item)

    newMarkets = response[1]

    dbsession.add_all(newMarkets)

    dbsession.commit()

    assert dbsession.query(ReferenceMarket).count() > 0

    assert dbsession.query(ReferenceOutcome).count() > 0

    assert dbsession.query(OutcomeRecord).count() > 0
