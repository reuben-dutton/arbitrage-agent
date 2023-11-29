from typing import Optional
import datetime
import dateutil.parser

import httpx

from src.database.models import (
    ReferenceSport,
    ReferenceContest,
    ReferenceEvent,
    ReferenceMarket,
    ReferenceOutcome,
    OutcomeRecord,
)

from src.web.api.base import BaseAPI


baseURL = "https://ss-aka-ori.ladbrokes.com/openbet-ssviewer/Drilldown/2.31"


class Ladbrokes(BaseAPI):
    __api_name__ = "Ladbrokes"

    def __init__(self, client, apiKey=None):
        self.client = client

    def setup(self):
        ...

    def contest_request_info(self, referenceSport: ReferenceSport) -> dict:
        requestInfo = dict()
        requestInfo['categoryID'] = referenceSport.refnum
        requestInfo['params'] = [
            ('responseFormat', 'json'),
            ('translationLang', 'en'),
        ]
        return requestInfo

    def event_request_info(self, referenceContest: ReferenceContest) -> dict:
        requestInfo = dict()
        requestInfo["typeID"] = referenceContest.refnum
        requestInfo['params'] = [
            ('responseFormat', 'json'),
            ('translationLang', 'en'),
        ]
        return requestInfo

    def market_request_info(self, referenceEvent: ReferenceEvent) -> dict:
        requestInfo = dict()
        requestInfo['eventID'] = referenceEvent.refnum
        requestInfo['params'] = [
            ('responseFormat', 'json'),
            ('translationLang', 'en'),
        ]
        return requestInfo

    async def get_contests(self, requestInfo: dict):
        categoryID = requestInfo["categoryID"]
        params = requestInfo.get("params", None)

        requestURL = baseURL + "/ClassToSubType"

        params.extend([
            ("simpleFilter", "class.siteChannels:contains:M"),
            ("simpleFilter", "class.isActive"),
            ("simpleFilter", "type.hasOpenEvent"),
            ("simpleFilter", f"class.categoryId:equals:{categoryID}")
        ])

        # ladbrokes returns 403 unless user agent is spoofed
        headers = dict()
        headers['User-Agent'] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) \
            AppleWebKit/537.36 (KHTML, like Gecko) \
            Chrome/117.0.0.0 Safari/537.36"

        return await self.make_request(requestURL, params, headers=headers)

    async def get_events(self, requestInfo: dict):
        typeID = requestInfo["typeID"]
        params = requestInfo.get("params", None)

        requestURL = baseURL + "/Event"

        params.extend([
            ("simpleFilter", "class.siteChannels:contains:M"),
            ("simpleFilter", "class.isActive"),
            ("simpleFilter", "type.hasOpenEvent"),
            ("simpleFilter", f"event.typeId:equals:{typeID}")
        ])

        # ladbrokes returns 403 unless user agent is spoofed
        headers = dict()
        headers['User-Agent'] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) \
            AppleWebKit/537.36 (KHTML, like Gecko) \
            Chrome/117.0.0.0 Safari/537.36"

        return await self.make_request(requestURL, params, headers=headers)

    async def get_markets(self, requestInfo: dict):
        eventID = requestInfo["eventID"]
        params = requestInfo.get("params", None)

        requestURL = baseURL + f"/EventToOutcomeForEvent/{eventID}"

        # for now we are only concerned with head to head
        params.extend([
            ("simpleFilter", "market.dispSortName:intersects:HH")
        ])

        # ladbrokes returns 403 unless user agent is spoofed
        headers = dict()
        headers['User-Agent'] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) \
            AppleWebKit/537.36 (KHTML, like Gecko) \
            Chrome/117.0.0.0 Safari/537.36"

        return await self.make_request(requestURL, params, headers=headers)

    async def get_outcomes(self, requestInfo: dict):
        raise NotImplementedError

    async def format_contests_data(self, responseData: dict):
        classes = responseData['SSResponse']["children"]
        newEntities = []
        for classItem in classes:
            info = classItem.get("class", None)
            if not info:
                continue
            for typeItem in info.get("children", []):
                newEntity = dict()
                newEntity["refnum"] = str(typeItem['type']["id"])
                newEntity["refname"] = str(typeItem['type']["name"])
                # no start time for ladbrokes competitions
                newEntity["starttime"] = None
                newEntities.append(newEntity)
        return newEntities

    async def format_events_data(self, responseData: dict):
        eventData = responseData["SSResponse"]["children"]
        newEntities = []
        for event in eventData:
            info = event.get("event", None)
            if not info:
                continue
            if info['eventSortCode'] == "TNMT":
                continue
            newEntity = dict()
            newEntity["refnum"] = str(info["id"])
            newEntity["refname"] = str(info["name"])
            # no start time for ladbrokes competitions
            newEntity["starttime"] = dateutil.parser.isoparse(str(info["startTime"]))
            newEntities.append(newEntity)
        return newEntities

    async def format_markets_data(self, responseData: dict):
        retrievalTimestamp = datetime.datetime.utcnow()

        newEntities = []

        marketData = responseData['SSResponse']["children"][0]["event"]
        if not marketData.get("children", None):
            return []
        marketData = marketData["children"]
        for market in marketData:
            # already limited to head to head from the response
            info = market['market']
            newMarket = dict()
            newMarket["refnum"] = info['id']
            newMarket["refname"] = info["name"]
            filteredOutcomes = []
            for outcome in info["children"]:
                newOutcome = dict()
                outcomeInfo = outcome['outcome']
                newOutcome['refnum'] = outcomeInfo['id']
                newOutcome['refname'] = outcomeInfo['name']
                newOutcome["returns"] = outcomeInfo['children'][0]['price']['priceDec']
                newOutcome["timestamp"] = retrievalTimestamp
                filteredOutcomes.append(newOutcome)
            newMarket["outcomes"] = filteredOutcomes
            newEntities.append(newMarket)

        return newEntities
