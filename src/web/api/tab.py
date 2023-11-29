import copy
import datetime
import urllib.parse
from typing import Optional

import dateutil.parser
import httpx

from src.database.models import (
    ReferenceContest,
    ReferenceEvent,
    ReferenceMarket,
    ReferenceOutcome,
    ReferenceSport,
)
from src.web.api.base import BaseAPI


valid_jurisdictions = ["NSW", "VIC", "ACT", "QLD", "SA", "NT", "TAS"]

baseURL = "https://api.beta.tab.com.au/v1/tab-info-service/sports"


class Tab(BaseAPI):
    __api_name__ = "TAB"

    def __init__(self, session, apiKey=None):
        super().__init__(session, apiKey=apiKey)
        ...

    def setup(self):
        ...

    def validate_params(self, params):
        if not params or params["jurisdiction"] not in valid_jurisdictions:
            raise ValueError("Jurisdiction must be valid.")

    def contest_request_info(self, referenceSport: ReferenceSport):
        requestInfo = {"sportName": referenceSport.refname}
        requestInfo["params"] = {"jurisdiction": "QLD"}
        return requestInfo

    def event_request_info(self, referenceContest: ReferenceContest):
        requestInfo = {
            "sportName": referenceContest.parent.refname,
            "contestName": referenceContest.refname,
        }
        requestInfo["params"] = {"jurisdiction": "QLD"}
        return requestInfo

    def market_request_info(self, referenceEvent: ReferenceEvent):
        requestInfo = {
            "sportName": referenceEvent.parent.parent.refname,
            "contestName": referenceEvent.parent.refname,
            "eventName": referenceEvent.refname,
        }
        requestInfo["params"] = {"jurisdiction": "QLD"}
        return requestInfo

    async def get_contests(self, requestInfo: dict) -> Optional[dict]:
        """
        Params:
            sportName [str]
                The name of the sport (e.g. Basketball)
            jurisdiction [str] NSW VIC ACT QLD SA NT TAS
                A string code corresponding to an Australian state.
                The returned sports will be those available for betting in
                that state (I assume)

        Options:

        """
        sportName = urllib.parse.quote(requestInfo["sportName"])
        params = requestInfo.get("params", None)
        self.validate_params(params)

        requestURL = baseURL + f"/{sportName}/competitions"

        response = await self.make_request(requestURL, params)
        response["sportName"] = sportName  # for formatting
        return response

    async def get_contest(self, requestInfo: dict) -> Optional[dict]:
        """
        Params:
            sportName [str]
                The name of the sport (e.g. Basketball)
            contestName [str]
                The name of the contest
            jurisdiction [str] NSW VIC ACT QLD SA NT TAS
                A string code corresponding to an Australian state.
                The returned sports will be those available for betting in
                that state (I assume)

        Options:

        """
        # these have already been encoded in get_contests()
        # sportName = urllib.parse.quote(requestInfo['sportName'])
        sportName = requestInfo["sportName"]
        contestName = urllib.parse.quote(requestInfo["contestName"])

        params = requestInfo.get("params", None)

        self.validate_params(params)

        requestURL = baseURL + f"/{sportName}/competitions/{contestName}"

        return await self.make_request(requestURL, params)

    async def get_events(self, requestInfo: dict) -> Optional[dict]:
        """
        Params:
            sportName [str]
                The name of the sport (e.g. Basketball)
            contestName
                The name of the contest (e.g. NBA)
            jurisdiction [str] NSW VIC ACT QLD SA NT TAS
                A string code corresponding to an Australian state.
                The returned sports will be those available for betting in
                that state (I assume)

        Options:

        """
        sportName = urllib.parse.quote(requestInfo["sportName"])
        contestName = urllib.parse.quote(requestInfo["contestName"])
        params = requestInfo.get("params", None)

        self.validate_params(params)

        requestURL = baseURL + f"/{sportName}/competitions/{contestName}/matches"

        return await self.make_request(requestURL, params)

    async def get_markets(self, requestInfo: dict) -> Optional[dict]:
        """
        Params:
            sportName [str]
                The name of the sport (e.g. Basketball)
            contestName [str]
                The name of the contest (e.g. NBA)
            eventName [str]
                The name of the event (e.g. Boston v Philadelphia)
            jurisdiction [str] NSW VIC ACT QLD SA NT TAS
                A string code corresponding to an Australian state.
                The returned sports will be those available for betting in
                that state (I assume)

        Options:

        """
        sportName = urllib.parse.quote(requestInfo["sportName"])
        contestName = urllib.parse.quote(requestInfo["contestName"])
        eventName = urllib.parse.quote(requestInfo["eventName"])
        params = requestInfo.get("params", None)

        self.validate_params(params)

        requestURL = (
            baseURL
            + f"/{sportName}/competitions/{contestName}/matches/{eventName}/markets"
        )

        return await self.make_request(requestURL, params)

    async def format_contests_data(self, responseData):
        nonFutures = []
        # sportName = responseData["sportName"]
        for contest in responseData["competitions"]:
            # contestName = contest['name']
            # compData = await self.get_contest(
            #     {
            #         "sportName": sportName,
            #         "contestName": contestName,
            #         "params": {"jurisdiction": "QLD"},
            #     }
            # )
            # if compData is None:
            #     continue
            # # eliminate futures markets and same game multi(?)
            # if compData['hasFuturePredictions'] or not compData['hasMarkets']:
            #     continue
            compData = contest
            nonFutures.append(compData)

        results = []
        for compData in nonFutures:
            newContest = dict()
            newContest["refnum"] = str(compData["id"])
            newContest["refname"] = str(compData["name"])
            # no start time for TAB contests
            newContest["starttime"] = None
            results.append(newContest)

        return results

    async def format_events_data(self, responseData):
        results = []
        for event in responseData["matches"]:
            newEvent = dict()
            newEvent["refnum"] = str(event["id"])
            newEvent["refname"] = str(event["name"])
            newEvent["starttime"] = dateutil.parser.isoparse(str(event["startTime"]))
            results.append(newEvent)
        return results

    async def format_markets_data(self, responseData):
        retrievalTimestamp = datetime.datetime.utcnow()

        results = []

        for market in responseData["markets"]:
            # limited to head to head for now
            if market["betOption"] != "Head To Head":
                continue

            if market["isFuture"]:
                continue

            newMarket = dict()
            newMarket["refnum"] = market["betOptionSpectrumId"]
            newMarket["refname"] = market["betOption"]
            filteredOutcomes = []
            for outcome in market["propositions"]:
                newOutcome = dict()
                newOutcome["returns"] = outcome["returnWin"]
                newOutcome["refname"] = outcome["name"]
                newOutcome["timestamp"] = retrievalTimestamp
                filteredOutcomes.append(newOutcome)
            newMarket["outcomes"] = filteredOutcomes
            results.append(newMarket)

        return results
