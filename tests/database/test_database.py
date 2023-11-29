import datetime
import time

import pytest

from src.database.models import (
    Bookmaker,
    ReferenceContest,
    ReferenceEvent,
    ReferenceSport,
    SourceContest,
    SourceEvent,
    SourceSport,
)


def populate_database(session):
    b = [
        Bookmaker("Sportsbet"),
        Bookmaker("TAB"),
        Bookmaker("Ladbrokes"),
    ]
    s = []
    for sport in ["Soccer", "Basketball", "Cricket"]:
        for bookmaker in b:
            s.append(ReferenceSport(bookmaker, refname=sport))

    c = []
    for refsport in s:
        if refsport.refname == "Soccer":
            c.append(ReferenceContest(refsport, refname="Soccer Cup"))
            c.append(ReferenceContest(refsport, refname="Womens Soccer Cup"))
            c.append(ReferenceContest(refsport, refname="European Soccer Cup"))
        elif refsport.refname == "Basketball":
            c.append(ReferenceContest(refsport, refname="Basketball Cup"))
            c.append(ReferenceContest(refsport, refname="Womens Basketball Cup"))
            c.append(ReferenceContest(refsport, refname="European Basketball Cup"))
        elif refsport.refname == "Cricket":
            c.append(ReferenceContest(refsport, refname="Cricket Cup"))
            c.append(ReferenceContest(refsport, refname="Womens Cricket Cup"))
            c.append(ReferenceContest(refsport, refname="European Cricket Cup"))

    session.add_all(b + s + c)
    session.commit()
    pass


@pytest.mark.anyio
def test_database_engine(dbsession):
    pass


@pytest.mark.anyio
def test_bookmaker(dbsession):
    populate_database(dbsession)

    assert dbsession.query(Bookmaker).count() == 3

    assert dbsession.query(ReferenceSport).count() == 9

    assert dbsession.query(ReferenceContest).count() == 27
