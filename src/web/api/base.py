from typing import Optional

import httpx

from src.database.models import (
    OutcomeRecord,
    ReferenceContest,
    ReferenceEvent,
    ReferenceMarket,
    ReferenceOutcome,
    ReferenceSport,
)
from src.web.enums import WebRequestStatus


class BaseAPI:
    __api_name__ = None

    def __init__(self, client, apiKey=None):
        self.client = client

    def setup(self):
        ...

    async def make_request(
        self, url: str, params: dict, headers: dict = None
    ) -> Optional[dict]:
        response = await self.client.get(url, params=params, headers=headers)
        if response.is_success:
            return response.json()
        elif response.status_code == httpx.codes.NOT_FOUND:
            return None
        else:
            raise Exception(
                "Request to %s failed with error code %s" % (url, response.status_code)
            )

    def contest_request_info(self, referenceSport: ReferenceSport) -> dict:
        raise NotImplementedError

    def event_request_info(self, referenceContest: ReferenceContest) -> dict:
        raise NotImplementedError

    def market_request_info(self, referenceEvent: ReferenceEvent) -> dict:
        raise NotImplementedError

    async def get_contests(self, requestInfo: dict):
        raise NotImplementedError

    async def get_events(self, requestInfo: dict):
        raise NotImplementedError

    async def get_markets(self, requestInfo: dict):
        raise NotImplementedError

    async def get_outcomes(self, requestInfo: dict):
        raise NotImplementedError

    async def format_contests_data(self, responseData: dict):
        raise NotImplementedError

    async def format_events_data(self, responseData: dict):
        raise NotImplementedError

    async def format_markets_data(self, responseData: dict):
        raise NotImplementedError

    async def retrieve_contests(self, referenceSport: ReferenceSport):
        # get the information required to call the API
        requestInfo = self.contest_request_info(referenceSport)
        # construct a request and send it
        response = await self.get_contests(requestInfo)
        # check for missing content
        if response is None:
            return (WebRequestStatus.NOTFOUND, [])
        # format the data if it was returned
        data = await self.format_contests_data(response)
        # convert into ReferenceContests
        newContestEntities = []
        for item in data:
            newEntity = ReferenceContest(referenceSport, **item)
            newEntity.retrieved()
            newContestEntities.append(newEntity)

        return (WebRequestStatus.SUCCESS, newContestEntities)

    async def retrieve_events(self, referenceContest: ReferenceContest):
        # get the information required to call the API
        requestInfo = self.event_request_info(referenceContest)
        # construct a request and send it
        response = await self.get_events(requestInfo)
        # check for missing content
        if response is None:
            return (WebRequestStatus.NOTFOUND, [])
        # format the data if it was returned
        data = await self.format_events_data(response)
        # convert into ReferenceContests
        newEventEntities = []
        for item in data:
            newEntity = ReferenceEvent(referenceContest, **item)
            newEntity.retrieved()
            newEventEntities.append(newEntity)

        return (WebRequestStatus.SUCCESS, newEventEntities)

    async def retrieve_markets(self, referenceEvent: ReferenceEvent):
        # get the information required to call the API
        requestInfo = self.market_request_info(referenceEvent)
        # construct a request and send it
        response = await self.get_markets(requestInfo)
        # check for missing content
        if response is None:
            return (WebRequestStatus.NOTFOUND, [])
        # format the data if it was returned
        data = await self.format_markets_data(response)
        # convert into ReferenceContests
        newMarketEntities = []
        for marketItem in data:  # markets
            marketOutcomes = marketItem["outcomes"]
            del marketItem["outcomes"]
            market = ReferenceMarket(referenceEvent, **marketItem)
            market.retrieved()
            for outcomeData in marketOutcomes:
                timestamp = outcomeData["timestamp"]
                returns = outcomeData["returns"]
                del outcomeData["timestamp"]
                del outcomeData["returns"]
                referenceOutcome = ReferenceOutcome(market, **outcomeData)
                OutcomeRecord(referenceOutcome, timestamp, returns)
            newMarketEntities.append(market)

        return (WebRequestStatus.SUCCESS, newMarketEntities)
