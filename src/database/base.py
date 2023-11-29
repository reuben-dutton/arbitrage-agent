from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, declared_attr

import config

engine = create_engine(config.DATABASE_CONNECT_STRING, echo=True)


class DatabaseModel(DeclarativeBase):

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__
