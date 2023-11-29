import pytest

# get client and database fixtures
from tests.web.conftest import *  # noqa
from tests.database.conftest import *  # noqa
from src.web.api.sportsbet import Sportsbet
from src.web.api.tab import Tab
from src.web.api.ladbrokes import Ladbrokes


@pytest.fixture(params=[Sportsbet, Tab, Ladbrokes])
async def betapi(caching_client, request):
    model = request.param
    return model(caching_client)
