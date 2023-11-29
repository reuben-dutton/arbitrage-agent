from sqlalchemy.orm import Session

from src.database.base import engine
from src.database.models import DatabaseModel
from src.database.models import (
    Bookmaker,
    ReferenceSport,
)


def main():
    DatabaseModel.metadata.drop_all(engine)
    DatabaseModel.metadata.create_all(engine)
    session = Session(bind=engine)
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
    s.append(ReferenceSport(b[2], refnum="10", refname="Cricket"))
    s.append(ReferenceSport(b[2], refnum="30", refname="Rugby League"))

    for sport in s:
        sport.added()

    session.add_all(b + s)
    session.commit()


if __name__ == "__main__":
    main()
