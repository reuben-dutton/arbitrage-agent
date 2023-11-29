import datetime
from logging import getLogger
from typing import Type

from sqlalchemy import select
from sqlalchemy.ext.serializer import dumps, loads
from taskiq import Context, TaskiqDepends

from src.database.core import get_recorded_entities

from src.database.models import (
    Bookmaker,
    DatabaseModel,
    ReferenceContest,
    ReferenceEntity,
    ReferenceEvent,
    ReferenceMarket,
    ReferenceOutcome,
    ReferenceSport,
)
from src.database.utils import deserialize_model, serialize_model
from src.web.api.utils import get_bookmaker_api
from src.web.enums import WebRequestStatus
from src.worker import dependencies
from src.worker.broker import broker


logger = getLogger(__name__)


@broker.task
async def get_bookmakers(context: Context = TaskiqDepends()):
    session = dependencies.get_session(context)

    stmt = select(Bookmaker)
    bookmakers = session.scalars(stmt).all()
    return bookmakers


@broker.task
async def get_sports(context: Context = TaskiqDepends()):
    return await get_entities(ReferenceSport, context)


@broker.task
async def get_contests(context: Context = TaskiqDepends()):
    return await get_entities(ReferenceContest, context)


@broker.task
async def get_events(context: Context = TaskiqDepends()):
    return await get_entities(ReferenceEvent, context)


async def get_entities(
    modelType: Type[ReferenceEntity], context: Context = TaskiqDepends()
):
    session = dependencies.get_session(context)

    entities = get_recorded_entities(session, modelType)

    return [serialize_model(entity) for entity in entities]


@broker.task
async def add_contests(model: str, context: Context = TaskiqDepends()):
    return await add_entities(model, ReferenceContest, context)


@broker.task
async def add_events(model: str, context: Context = TaskiqDepends()):
    return await add_entities(model, ReferenceEvent, context)


@broker.task
async def add_markets(model: str, context: Context = TaskiqDepends()):
    return await add_entities(model, ReferenceMarket, context)


async def add_entities(
    referenceParentModel: str,
    modelType: Type[ReferenceEntity],
    context: Context = TaskiqDepends(),
):
    # get dependencies
    session = dependencies.get_session(context)
    client = dependencies.get_client(context)

    # deserialize arguments
    referenceParent = deserialize_model(referenceParentModel, session)

    # construct api
    apiModel = get_bookmaker_api(referenceParent.bookmaker.name)
    api = apiModel(client)

    # retrieve novel entities (may be new or old)
    if modelType is ReferenceContest:
        status, novelEntities = await api.retrieve_contests(referenceParent)
    elif modelType is ReferenceEvent:
        status, novelEntities = await api.retrieve_events(referenceParent)
    elif modelType is ReferenceMarket:
        status, novelEntities = await api.retrieve_markets(referenceParent)

    # timestamp when the request was made
    timestamp = datetime.datetime.now(datetime.timezone.utc)

    if status is not WebRequestStatus.SUCCESS:
        referenceParent.not_found(timestamp)
        session.commit()
        return

    referenceParent.found(timestamp)

    # get recorded entities which are of type modelType and have
    # the given referenceParent as a parent
    recordedEntities = get_recorded_entities(session, modelType, parent=referenceParent)

    # add new outcome records for recorded markets
    if modelType is ReferenceMarket:
        for novelMarket in novelEntities:
            for recordedMarket in recordedEntities:
                if novelMarket == recordedMarket:
                    recordedMarket.copy_records(novelMarket)

    # entities that were found but have not already been recorded
    newEntities = set(novelEntities) - set(recordedEntities)

    # entities that have been recorded but not found
    expiredEntities = set(recordedEntities) - set(novelEntities)

    # entities that have both been recorded and found again
    unexpiredEntities = set(recordedEntities) - expiredEntities

    # entities were not found
    for entity in expiredEntities:
        entity.not_found(timestamp)

    # entities were found
    for entity in unexpiredEntities:
        entity.found(timestamp)

    # record new entities
    for entity in newEntities:
        entity.added()

    session.add_all(newEntities)
    session.commit()

    return
