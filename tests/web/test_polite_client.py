import asyncio
import timeit

import pytest
import respx
from httpx import Response

from tests import utils

example_urls = [
    "https://test.example.com",
    "https://another.one.com",
]


class TestRetries(object):
    @respx.mock
    @pytest.mark.anyio
    async def test_retries_unused(self, retry_client):
        """
        Check that, even with max_retries > 1, the client still
        returns a response with code 2xx without retrying.
        """
        route = respx.get(example_urls[0])
        route.side_effect = [
            Response(200),
            Response(200),
            Response(200),
        ]

        response = await retry_client.get(example_urls[0])

        assert response.status_code == 200
        assert route.call_count == 1

    @pytest.mark.dependency(name="retries_used")
    @respx.mock
    @pytest.mark.anyio
    async def test_retries_used(self, retry_client):
        """
        Check that, given a response contains a status code 4xx,
        retries are made until a success such that retries <= max_retries.
        """
        route = respx.get(example_urls[0])
        route.side_effect = [
            Response(403),
            Response(403),
            Response(200),
        ]

        response = await retry_client.get(example_urls[0])

        assert response.status_code == 200
        assert route.call_count == 3

    @pytest.mark.dependency(depends=["retries_used"])
    @respx.mock
    @pytest.mark.anyio
    async def test_max_retries_used(self, retry_client):
        """
        Check that, given a response contains a status code 4xx,
        retries are made until retries == max_retries, at which point
        the failed response is returned.
        """
        route = respx.get(example_urls[0])
        route.side_effect = [
            Response(403),
            Response(403),
            Response(403),
        ]

        response = await retry_client.get(example_urls[0])

        assert response.status_code == 403
        assert route.call_count == 3


class TestRateLimits(object):
    @respx.mock
    @pytest.mark.anyio
    async def test_global_limits_adhered(self, global_limited_client):
        """
        Check that, given multiple responses are queued simultaneously,
        they are limited to the web client rate limits specified.
        """
        server_response = utils.construct_delayed_response(0)

        route = respx.get(example_urls[0])
        route.mock(side_effect=server_response)

        responses = []

        startTime = timeit.default_timer()

        num_requests = 47

        async with asyncio.TaskGroup() as tg:
            for _ in range(num_requests):
                tg.create_task(global_limited_client.get(example_urls[0]))

        for response in responses:
            assert response.status_code == 200

        time_elapsed = timeit.default_timer() - startTime

        global_rate = global_limited_client.clientSettings.global_rate
        time_needed = num_requests // global_rate
        if num_requests % global_rate == 0:
            time_needed -= 1

        # 3 requests with 1 per second = 2 seconds minimum
        assert time_elapsed >= time_needed
        assert time_elapsed < time_needed + 1

    @respx.mock
    @pytest.mark.anyio
    async def test_domain_limits_adhered(self, domain_limited_client):
        server_response = utils.construct_delayed_response(0)

        route1 = respx.get(example_urls[0])
        route1.mock(side_effect=server_response)

        route2 = respx.get(example_urls[1])
        route2.mock(side_effect=server_response)

        responses = []

        startTime = timeit.default_timer()

        base_num_requests_per_domain = 13

        async with asyncio.TaskGroup() as tg:
            for i, example_url in enumerate(example_urls):
                num_requests = base_num_requests_per_domain + i * 11
                for _ in range(num_requests):
                    tg.create_task(domain_limited_client.get(example_url))

        # should be limited by the maximum requests to a single domain
        max_requests_to_domain = (
            base_num_requests_per_domain + (len(example_urls) - 1) * 11
        )

        for response in responses:
            assert response.status_code == 200

        domain_rate = domain_limited_client.clientSettings.domain_rate
        time_needed = max_requests_to_domain // domain_rate
        if max_requests_to_domain % domain_rate == 0:
            time_needed -= 1

        time_elapsed = timeit.default_timer() - startTime

        assert time_elapsed >= time_needed
        assert time_elapsed < time_needed + 1
