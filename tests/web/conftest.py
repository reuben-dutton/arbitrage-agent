import pytest
import config
from src.web.client import RateLimitedClient, ClientSettings, CachingClient


@pytest.fixture
async def unlimited_client():
    clientSettings: ClientSettings = ClientSettings(None, None)
    client = RateLimitedClient(clientSettings)
    yield client
    await client.aclose()


@pytest.fixture
async def caching_client():
    clientSettings: ClientSettings = ClientSettings(10, 2)
    client = CachingClient(config.REQUEST_CACHE_LOCATION, clientSettings)
    yield client
    await client.aclose()


@pytest.fixture
async def retry_client():
    clientSettings: ClientSettings = ClientSettings(None, None)
    clientSettings.set_max_retries(2)
    client = RateLimitedClient(clientSettings)
    yield client
    await client.aclose()


@pytest.fixture(params=[17, 23, 31], ids=lambda rate: f"global_rate={rate}")
async def global_limited_client(request):
    clientSettings: ClientSettings = ClientSettings(request.param, None)
    client = RateLimitedClient(clientSettings)
    yield client
    await client.aclose()


@pytest.fixture(params=[7, 11, 17], ids=lambda rate: f"domain_rate={rate}")
async def domain_limited_client(request):
    clientSettings: ClientSettings = ClientSettings(None, request.param)
    clientSettings.set_domain_concurrency(1)
    client = RateLimitedClient(clientSettings)
    yield client
    await client.aclose()
