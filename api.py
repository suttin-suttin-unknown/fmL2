from utils import get_api_host

from functools import lru_cache
import requests

api_host = get_api_host()
session = requests.Session()
session.headers.update({"Cache-Control": "no-cache"})

@lru_cache(maxsize=None)
def get_league(id, timezone="America/Los_Angeles"):
    response = session.get(f"{api_host}/leagues", params={
        "id": id, "tab": "overview", "type": "league", "timeZone": timezone
    })
    response.raise_for_status()
    return response.json()

@lru_cache(maxsize=None)
def get_player(id):
    response = session.get(f"{api_host}/playerData?id={id}", headers={"Cache-Control": "no-cache"})
    response.raise_for_status()
    return response.json()

@lru_cache(maxsize=None)
def get_team(id, timezone="America/Los_Angeles"):
    response = session.get(f"{api_host}/teams", params={
        "id": id, "tab": "overview", "type": "league", "timeZone": timezone
    })
    response.raise_for_status()
    return response.json()