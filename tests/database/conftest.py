import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from src.database.models import DatabaseModel


@pytest.fixture(scope="session")
def engine(request):
    dburl = request.config.getoption("--dburl")
    return create_engine(dburl, echo=False)


@pytest.fixture(scope="session")
def tables(engine):
    DatabaseModel.metadata.create_all(engine)
    yield
    DatabaseModel.metadata.drop_all(engine)


# https://gist.github.com/kissgyorgy/e2365f25a213de44b9a2#file-sqlalchemy_conftest-py-L13
@pytest.fixture
def dbsession(engine, tables):
    """
        Returns an sqlalchemy session, and after the
        test tears down everything properly.
    """
    connection = engine.connect()
    # begin the nested transaction
    transaction = connection.begin()
    # use the connection with the already started transaction
    session = scoped_session(sessionmaker(bind=connection))

    yield session

    session.close()
    # roll back the broader transaction
    transaction.rollback()
    # put back the connection to the connection pool
    connection.close()
