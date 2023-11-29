import asyncio
import hashlib
import logging
import os
from dataclasses import dataclass
from functools import wraps
from json.decoder import JSONDecodeError
from typing import Optional

import simplejson as json
import tldextract
from httpx import AsyncClient, Request, Response


logger = logging.getLogger(__name__)

extract = tldextract.TLDExtract()


def get_top_level_domain(url: str) -> str:
    return extract(url).domain


@dataclass
class ClientSettings:
    global_rate: Optional[float]  # None -> unlimited
    domain_rate: Optional[float]  # None -> unlimited
    _global_concurrency: int = 1
    _domain_concurrency: int = 1
    max_retries: int = 0

    def __post_init__(self):
        self.update_intervals()

    def set_global_concurrency(self, global_concurrency):
        self._global_concurrency = global_concurrency
        self.update_intervals()

    def set_domain_concurrency(self, domain_concurrency):
        self._domain_concurrency = domain_concurrency
        self.update_intervals()

    def set_max_retries(self, max_retries):
        self.max_retries = max_retries

    def update_intervals(self):
        if self.global_rate:
            self.global_interval = self._global_concurrency / self.global_rate
        if self.domain_rate:
            self.domain_interval = self._domain_concurrency / self.domain_rate


DEFAULT_RATE_LIMIT = ClientSettings(None, None)


class RateLimitedClient(AsyncClient):
    def __init__(
        self,
        clientSettings: ClientSettings = DEFAULT_RATE_LIMIT,
        **kwargs,
    ):
        """
        Args:
            global_interval (Union[dt.timedelta, float]):
                Time between requests for the entire pool.
                If a float is given, seconds are assumed.
            domain_interval (Union[dt.timedelta, float]):
                Time between requests for each top-level domain.
                If a float is given, seconds are assumed.
            domain_concurrency (Union[dt.timedelta, float]):
                The maximum number of concurrent requests for each top-level domain.
                Defaults to 1.
        """
        self.clientSettings = clientSettings
        self._using_global_interval = clientSettings.global_rate is not None
        self._using_domain_interval = clientSettings.domain_rate is not None

        if self._using_global_interval:
            self.global_interval = clientSettings.global_interval
        if self._using_domain_interval:
            self.domain_interval = clientSettings.domain_interval

        self.global_concurrency = clientSettings._global_concurrency
        self.domain_concurrency = clientSettings._domain_concurrency

        self.max_retries = clientSettings.max_retries

        self._background_tasks = set()
        self._global_lock = asyncio.Semaphore(self.global_concurrency)
        self._domain_locks = dict()

        super().__init__(**kwargs)

    def _schedule_lock_release(self, domain: str, already_elapsed: float):
        """
        Given a top-level domain, and the time already elapsed making a successful
        request, schedule the release of the lock that was set after making the request.
        We schedule the lock to release after the domain_interval has already passed.
        This ensures that rate-limits are adhered to, but that the duration of the
        request/response cycle doesn't increase it.

        Args:
            domain (str): the specific top-level domain to unlock
            already_elapsed (float): the time already elapsed between creating the lock
                and recieving the complete request
        """
        logger.debug("Time elapsed during requests: %ss.", already_elapsed)

        # schedule the release of the domain lock for the given domain
        if self._using_domain_interval:
            domain_lock_duration = max(self.domain_interval - already_elapsed, 0)

            def release_domain_lock(task):
                self._get_domain_lock(domain).release()
                self._background_tasks.discard(task)

            wait_domain = asyncio.create_task(asyncio.sleep(domain_lock_duration))
            self._background_tasks.add(wait_domain)
            wait_domain.add_done_callback(release_domain_lock)

        # schedule the release of the global lock
        if self._using_global_interval:
            global_lock_duration = max(self.global_interval - already_elapsed, 0)

            def release_global_lock(task):
                self._global_lock.release()
                self._background_tasks.discard(task)

            wait_pool = asyncio.create_task(asyncio.sleep(global_lock_duration))
            self._background_tasks.add(wait_pool)
            wait_pool.add_done_callback(release_global_lock)

    def _get_domain_lock(self, domain):
        if self._domain_locks.get(domain, None) is None:
            self._domain_locks[domain] = asyncio.Semaphore(self.domain_concurrency)
        return self._domain_locks[domain]

    @wraps(AsyncClient.send)
    async def send(self, *args, **kwargs):
        retries = 0
        url = str(args[0].url)  # get the request url
        domain = get_top_level_domain(url)

        # await the lock for that domain
        if self._using_domain_interval:
            domain_lock = self._get_domain_lock(domain)
            await domain_lock.acquire()
        # await the lock for the connection pool
        if self._using_global_interval:
            await self._global_lock.acquire()

        total_elapsed = 0

        # create a task to make the request
        request = asyncio.create_task(super().send(*args, **kwargs))

        response = await request

        # we don't schedule the release until the request is returned

        total_elapsed += response.elapsed.total_seconds()

        # retry until successful
        while not response.is_success and retries < self.max_retries:
            logger.info(
                "Request to %s failed with status code %s. Retries left: %s.",
                domain,
                response.status_code,
                self.max_retries - retries,
            )
            retries += 1
            await asyncio.sleep(10)
            request = asyncio.create_task(super().send(*args, **kwargs))

            response = await request
            total_elapsed += response.elapsed.total_seconds()

        # schedule the release of the domain and pool locks
        self._schedule_lock_release(domain, total_elapsed)

        return response


class CachingClient(RateLimitedClient):
    def __init__(self, cache_location, *args, **kwargs):
        self.cache_location = os.path.join(os.getcwd(), cache_location)
        self.caching = self.cache_location is not None
        super().__init__(*args, **kwargs)

    def get_filepath(self, request: Request) -> str:
        filename = hashlib.md5(str(request.url).encode("utf-8")).hexdigest()
        filepath = os.path.join(self.cache_location, f"{filename}.json")
        return filepath

    def retrieve_cached_response(self, filepath):
        with open(filepath, "r") as j:
            data = json.load(j)

            response = Response(
                data["response"]["status_code"],
                json=data["response"]["json"],
            )

            return response

    def construct_cached_response(self, request: Request, response: Response):
        request = request.__dict__
        data = {
            "url": str(request["url"]),
            "headers": request.get("headers", {}).__dict__,
            "response": {
                "status_code": response.status_code,
                "headers": response.headers.__dict__,
            },
        }
        try:  # if json attached
            data["response"]["json"] = response.json()
        except JSONDecodeError:  # no json attached
            pass

        return data

    @wraps(RateLimitedClient.send)
    async def send(self, *args, **kwargs):
        request: Request = args[0]

        if self.caching:
            filepath = self.get_filepath(request)

            if os.path.exists(filepath):
                return self.retrieve_cached_response(filepath)

        response = await super().send(*args, **kwargs)

        if self.caching:
            cached_data = self.construct_cached_response(request, response)

            with open(filepath, "w") as j:
                json.dump(cached_data, j)

        return response
