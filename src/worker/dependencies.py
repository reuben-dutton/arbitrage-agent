from taskiq import Context
from httpx import AsyncClient
from sqlalchemy.orm import scoped_session


def get_client(context: Context) -> AsyncClient:
    return context.state.client


def get_session(context: Context) -> scoped_session:
    return context.state.session
