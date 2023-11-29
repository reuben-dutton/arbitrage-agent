from sqlalchemy import select
from sqlalchemy.ext.serializer import dumps, loads
from sqlalchemy.orm import Session

import src.database.models as models


def serialize_model(model: models.DatabaseModel) -> str:
    modelClass = model.__class__
    if not hasattr(modelClass, "id"):
        raise ValueError(
            f"{modelClass} has no id attribute, and so cannot be serialized!"
        )
    query = select(modelClass).where(modelClass.id == model.id)
    encodedquery = dumps(query).hex()
    return encodedquery


def deserialize_model(serialized_model: str, session: Session):
    statement = bytes.fromhex(serialized_model)
    statement = loads(statement, metadata=models.DatabaseModel.metadata)
    model = session.scalars(statement).all()[0]
    return model
