from src.web.api.sportsbet import Sportsbet
from src.web.api.tab import Tab
from src.web.api.ladbrokes import Ladbrokes

api_map = {
    "Sportsbet": Sportsbet,
    "TAB": Tab,
    "Ladbrokes": Ladbrokes,
}


def get_bookmaker_api(bookmaker_name: str):
    api = api_map.get(bookmaker_name, None)

    if not api:
        raise Exception("No api for bookmaker %s!" % bookmaker_name)

    return api
