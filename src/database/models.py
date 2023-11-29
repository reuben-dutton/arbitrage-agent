import datetime
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import ForeignKey, ForeignKeyConstraint, PrimaryKeyConstraint
from sqlalchemy.orm import declared_attr, Mapped, mapped_column, relationship
from sqlalchemy.types import DateTime, Enum

from src.database.base import DatabaseModel
from src.database.enums import Status


class Bookmaker(DatabaseModel):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column()
    active: Mapped[Optional[bool]] = mapped_column()

    def __init__(self, name):
        self.name = name


class ReferenceEntity:
    """
    Mixin used for reference entities. Contains reference names and numbers,
    as well as the bookmaker declared attribute.
    """

    # reference name and number (id or code)
    refnum: Mapped[Optional[str]] = mapped_column()
    refname: Mapped[Optional[str]] = mapped_column()

    # last time the reference entity was checked
    lastChecked: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    # last time the reference entity was found
    lastFound: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    # the current state of the entity
    status = mapped_column(Enum(Status))

    # bookmaker id
    bookmaker_id: Mapped[int] = mapped_column(ForeignKey("Bookmaker.id"))

    # corresponding bookmaker entity
    @declared_attr
    def bookmaker(cls) -> Mapped["Bookmaker"]:
        return relationship("Bookmaker", lazy="immediate")

    def __init__(self, refnum=None, refname=None):
        self.refnum = refnum
        self.refname = refname
        self.lastChecked = None
        self.status = Status.UNKNOWN

    def retrieved(self):
        self.status = Status.RETRIEVED

    def added(self):
        self.status = Status.ADDED

    def found(self, timestamp):
        self.lastChecked = timestamp
        self.lastFound = timestamp
        if self.status in [Status.NOT_FOUND, Status.ADDED, Status.CHECKED]:
            self.status = Status.CHECKED

    def not_found(self, timestamp):
        self.lastChecked = timestamp
        if self.status in [Status.CHECKED, Status.ADDED]:
            self.status = Status.NOT_FOUND
        elif self.status in [Status.NOT_FOUND]:
            # if the item was last found more than 2 days ago
            if (
                self.lastFound is not None
                and timestamp - self.lastFound > datetime.timedelta(days=2)
            ):
                self.status = Status.EXPIRED


class HashMixin:
    def __eq__(self, other):
        if hasattr(self, "starttime"):
            return (
                self.refnum == other.refnum
                and self.refname == other.refname
                and self.bookmaker.id == other.bookmaker.id
                and self.starttime == other.starttime
            )

        else:
            return (
                self.refnum == other.refnum
                and self.refname == other.refname
                and self.bookmaker.id == other.bookmaker.id
            )

    # just don't alter any of these attributes during runtime!!
    # you should be fine though...
    def __hash__(self):
        if hasattr(self, "starttime"):
            return hash(
                (
                    self.refnum,
                    self.refname,
                    self.bookmaker.id,
                    self.starttime,
                )
            )
        else:
            return hash((self.refnum, self.refname, self.bookmaker.id))


class SourceSport(DatabaseModel):
    id: Mapped[int] = mapped_column(primary_key=True)
    active: Mapped[Optional[bool]] = mapped_column()

    def __init__(self):
        ...


class SourceContest(DatabaseModel):
    id: Mapped[int] = mapped_column(primary_key=True)

    def __init__(self):
        ...


class SourceEvent(DatabaseModel):
    id: Mapped[int] = mapped_column(primary_key=True)

    def __init__(self):
        ...


class SourceMarket(DatabaseModel):
    id: Mapped[int] = mapped_column(primary_key=True)

    def __init__(self):
        ...


class SourceOutcome(DatabaseModel):
    id: Mapped[int] = mapped_column(primary_key=True)

    def __init__(self):
        ...


class ReferenceSport(DatabaseModel, ReferenceEntity):
    id: Mapped[int] = mapped_column(primary_key=True)

    sourceid: Mapped[Optional[int]] = mapped_column(ForeignKey("SourceSport.id"))
    source: Mapped[Optional["SourceSport"]] = relationship()

    def __init__(self, parent, *args, **kwargs):
        self.inherit(parent)
        super().__init__(*args, **kwargs)

    def inherit(self, parent):
        self.bookmaker = parent

    def __repr__(self):
        return f"{self.__class__.__name__}({self.bookmaker.name} | {self.refname})"


class ReferenceContest(DatabaseModel, ReferenceEntity, HashMixin):
    id: Mapped[int] = mapped_column(primary_key=True)

    parentid: Mapped[int] = mapped_column(ForeignKey("ReferenceSport.id"))
    sourceid: Mapped[Optional[int]] = mapped_column(ForeignKey("SourceContest.id"))
    parent: Mapped["ReferenceSport"] = relationship()
    source: Mapped[Optional["SourceContest"]] = relationship()

    starttime: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True)
    )

    def __init__(self, parent, starttime=None, *args, **kwargs):
        self.inherit(parent)
        super().__init__(*args, **kwargs)
        self.starttime = starttime

    def inherit(self, parent):
        self.bookmaker = parent.bookmaker
        self.parent = parent

    def __repr__(self):
        return (
            f"{self.__class__.__name__}({self.bookmaker.name}"
            f" | {self.parent.refname} | {self.refname})"
        )


class ReferenceEvent(DatabaseModel, ReferenceEntity, HashMixin):
    id: Mapped[int] = mapped_column(primary_key=True)

    parentid: Mapped[int] = mapped_column(ForeignKey("ReferenceContest.id"))
    sourceid: Mapped[Optional[int]] = mapped_column(ForeignKey("SourceEvent.id"))
    parent: Mapped["ReferenceContest"] = relationship()
    source: Mapped[Optional["SourceEvent"]] = relationship()

    starttime: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True)
    )

    def __init__(self, parent, starttime=None, *args, **kwargs):
        self.inherit(parent)
        super().__init__(*args, **kwargs)
        self.starttime = starttime

    def inherit(self, parent):
        self.bookmaker = parent.bookmaker
        self.parent = parent

    def __repr__(self):
        return (
            f"{self.__class__.__name__}({self.bookmaker.name}"
            f" | {self.parent.refname} | {self.refname})"
        )


class ReferenceMarket(DatabaseModel, ReferenceEntity, HashMixin):
    id: Mapped[int] = mapped_column(primary_key=True)

    parentid: Mapped[int] = mapped_column(ForeignKey("ReferenceEvent.id"))
    sourceid: Mapped[Optional[int]] = mapped_column(ForeignKey("SourceMarket.id"))
    parent: Mapped["ReferenceEvent"] = relationship()
    source: Mapped[Optional["SourceMarket"]] = relationship()

    outcomes: Mapped[List["ReferenceOutcome"]] = relationship(back_populates="parent")

    def __init__(self, parent, *args, **kwargs):
        self.inherit(parent)
        super().__init__(*args, **kwargs)

    def inherit(self, parent):
        self.bookmaker = parent.bookmaker
        self.parent = parent

    def copy_records(self, other: ReferenceEntity):
        if not hasattr(other, "outcomes"):
            raise Exception(f"{other} is not of type ReferenceMarket")

        for outcome in self.outcomes:
            for otherOutcome in other.outcomes:
                if outcome == otherOutcome:
                    outcome.records.extend(otherOutcome.records)


class ReferenceOutcome(DatabaseModel, ReferenceEntity, HashMixin):
    id: Mapped[int] = mapped_column(primary_key=True)

    parentid: Mapped[int] = mapped_column(ForeignKey("ReferenceMarket.id"))
    sourceid: Mapped[Optional[int]] = mapped_column(ForeignKey("SourceOutcome.id"))
    parent: Mapped["ReferenceMarket"] = relationship(back_populates="outcomes")
    source: Mapped[Optional["SourceOutcome"]] = relationship()

    records: Mapped[List["OutcomeRecord"]] = relationship(back_populates="refoutcome")

    def __init__(self, parent, *args, **kwargs):
        self.inherit(parent)
        super().__init__(*args, **kwargs)

    def inherit(self, parent):
        self.bookmaker = parent.bookmaker
        self.parent = parent


class OutcomeRecord(DatabaseModel):
    id: Mapped[int] = mapped_column(primary_key=True)

    outcomeid: Mapped[int] = mapped_column(ForeignKey("ReferenceOutcome.id"))
    refoutcome: Mapped["ReferenceOutcome"] = relationship(back_populates="records")

    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
    returns: Mapped[Decimal] = mapped_column()

    def __init__(self, outcome, timestamp, returns):
        self.refoutcome = outcome
        self.timestamp = timestamp
        self.returns = returns
