from typing import Optional, Type

from sqlalchemy import select
from sqlalchemy.orm import Session

import src.database.models as models
from src.database.enums import Status


def get_recorded_entities(
    session: Session,
    model: Type[models.DatabaseModel],
    parent: Optional[models.DatabaseModel] = None,
):
    stmt = select(model).where(model.status != Status.EXPIRED)
    if parent:
        stmt = stmt.where(model.parentid == parent.id)
    models = session.scalars(stmt).all()
    return models
