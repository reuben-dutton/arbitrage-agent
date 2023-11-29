import copy
import datetime
from typing import Optional

from src.database.models import (
    ReferenceContest,
    ReferenceEvent,
    ReferenceMarket,
    ReferenceOutcome,
    ReferenceSport,
)

from src.web.api.base import BaseAPI

baseURL = "https://www.sportsbet.com.au/apigw/sportsbook-sports/Sportsbook/Sports"


class Sportsbet(BaseAPI):
    __api_name__ = "Sportsbet"

    def __init__(self, client, apiKey=None):
        super().__init__(client, apiKey=apiKey)
        ...

    def contest_request_info(self, referenceSport: ReferenceSport):
        return {"sportID": referenceSport.refnum}

    def event_request_info(self, referenceContest: ReferenceContest):
        return {"contestID": referenceContest.refnum}

    def market_request_info(self, referenceEvent: ReferenceEvent):
        return {"eventID": referenceEvent.refnum}

    async def get_contests(self, requestInfo: dict) -> Optional[dict]:
        """
        Params:
            sportId [int]
                The id corresponding to the desired sport
                e.g. Basketball - US is 16

        Options:
            displayType [str] - default
                UNKNOWN

        """
        sportID = requestInfo["sportID"]
        params = requestInfo.get("params", None)

        requestURL = baseURL + f"/{sportID}/Competitions"
        if not params:
            params = dict()
            params["displayType"] = "default"
            params["eventFilter"] = "matches"

        return await self.make_request(requestURL, params)

    async def get_events(self, requestInfo: dict) -> Optional[dict]:
        """
        Params:
            contestId [int]
                The id corresponding to the desired contest
                e.g. NBA is 6927

        Options:
            displayType [str] - default
                UNKNOWN
            includeTopMarkets [bool]
                Whether markets are included in the response data
                If not given, default is false
            eventFilter [str] - matches, outrights
                Filters for matches or futures (outrights)
                If not given, both are included
            numMarkets [int]
                Specify many markets are included in the response data
                If not given, then return all markets possible
        """

        contestID = requestInfo["contestID"]
        params = requestInfo.get("params", None)

        requestURL = baseURL + f"/Competitions/{contestID}/Events"

        if not params:
            params = dict()
            params["displayType"] = "default"
            params["includeTopMarkets"] = "false"
            # params['eventFilter'] = 'matches'
        else:
            # convert includeTopMarkets to a string in lowercase
            params["includeTopMarkets"] = str(
                params.get("includeTopMarkets", "false")
            ).lower()

        return await self.make_request(requestURL, params)

    async def get_markets(self, requestInfo: dict) -> Optional[dict]:
        """
        Params:
            eventId [int]
                The id corresponding to the desired event
                e.g. New York Knicks vs Miami Heat 9th May is 7333708

        Options:
        """

        eventID = requestInfo["eventID"]
        params = requestInfo.get("params", None)

        requestURL = baseURL + f"/Events/{eventID}/Markets"
        if not params:
            params = dict()

        return await self.make_request(requestURL, params)

    async def format_contests_data(self, responseData):
        newEntities = []
        for contest in responseData:
            # hasBIR = has Betting In Round
            # This means that betting is allowed throughout the contest
            # (as opposed to betting on the outcome of a contest at the onset)
            # This only allows for contests that are not bets on the overall
            # outcome of a tournament
            # if not contest['hasBIR']:
            #     continue
            # if the contest is extra markets, don't return it as
            # it is sportsbet-specific
            if "extra market" in contest["name"].lower():
                continue
            # copy the sport reference data to the taskdata object
            newEntity = dict()
            newEntity["refnum"] = str(contest["id"])
            newEntity["refname"] = str(contest["name"])
            newEntity["starttime"] = datetime.datetime.fromtimestamp(
                int(contest["startTime"]), datetime.timezone.utc
            )
            newEntities.append(newEntity)
        return newEntities

    async def format_events_data(self, responseData):
        newEntities = []
        for event in responseData:
            if not event["eventSort"] == "MTCH":
                continue
            # copy the contest reference data to the taskdata object
            newEntity = dict()
            newEntity["refnum"] = str(event["id"])
            newEntity["refname"] = str(event["displayName"])
            newEntity["starttime"] = datetime.datetime.fromtimestamp(
                int(event["startTime"]), datetime.timezone.utc
            )
            newEntities.append(newEntity)
        return newEntities

    async def format_markets_data(self, responseData):
        retrievalTimestamp = datetime.datetime.utcnow()

        newEntities = []
        for market in responseData:
            # limited to head to head for now
            if market["name"] != "Match Betting":
                continue

            newMarket = dict()
            newMarket["refnum"] = None
            newMarket["refname"] = market["name"]
            filteredOutcomes = []
            for outcome in market["selections"]:
                newOutcome = dict()
                newOutcome["returns"] = outcome["price"]["winPrice"]
                newOutcome["refname"] = outcome["name"]
                newOutcome["timestamp"] = retrievalTimestamp
                filteredOutcomes.append(newOutcome)
            newMarket["outcomes"] = filteredOutcomes
            newEntities.append(newMarket)

        return newEntities
