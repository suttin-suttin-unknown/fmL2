import configparser
import glob
import json
import os
from functools import lru_cache
from itertools import chain
from operator import itemgetter

import requests

# Utils
def config():
    config = configparser.ConfigParser()
    config.read("config.ini")
    return config

def country_leagues():
    with open("countries.json", "r") as f:
        countries = json.load(f)
        leagues = set(chain(*[country["leagues"] for country in countries]))
        return list(leagues)

# League
def format_league_params():
    c = config()["league"]
    params = {}
    params["tab"] = c["default_tab"]
    params["type"] = c["default_type"]
    params["timeZone"] = c["default_timezone"]
    return params

@lru_cache(maxsize=None)
def league(id):
    api_host = config()["api"]["host"]
    headers = {"Cache-Control": "no-cache"}
    params = {"id": id, **format_league_params()}
    response = requests.get(f"{api_host}/leagues", headers=headers, params=params)
    response.raise_for_status()
    return response.json()

def league_details(id):
    details = league(id)["details"]
    return {"details": {
        "name": details["name"],
        "country": details["country"],
        "latest_season": details["latestSeason"]
    }}

def league_stat_links(id):
    stat_links = []
    for item in league(id)["stats"].get("seasonStatLinks", []):
        link = item.get("TotwRoundsLink", None)
        if link is not None:
            stat_links.append({"name": item["Name"], "link": link})
    return {"stat_links": stat_links}

def league_teams(id):
    table_data = league(id)["table"][0]["data"]
    table = None
    try:
        table = table_data["table"]
        teams = set(team["id"] for team in table["all"])
        return {"teams": list(teams)}
    except LookupError:
        if not table:
            tables = table_data["tables"]
            teams = set(chain(*[[team["id"] for team in table["table"]["all"]] for table in tables]))
            return {"teams": list(teams)}

def league_info(id):
    return {**league_details(id), **league_stat_links(id), **league_teams(id)}

def save_league(id):
    info = league_info(id)
    if info:
        root_path = config()["data"]["root_path"]
        path = f"{root_path}/leagues/{id}.json"
        os.makedirs(os.path.split(path)[0], exist_ok=True)
        with open(path, "w") as f:
            json.dump(info, f)

def read_league_info_files():
    root_path = config()["data"]["root_path"]
    paths = glob.glob(f"{root_path}/leagues/*")
    info = []
    for path in paths:
        id = os.path.splitext(os.path.basename(path))[0]
        with open(path, "r") as f:
            info.append({"id": id, **json.load(f)})
    return info
        

def main(leagues):
    for id in leagues:
        print(f"Saving league {id} info...")
        try:
            save_league(id)
        except:
            print(f"Error saving league {id}. Skipping.")
            continue
        else:
            print(f"League {id} info saved.")
            
if __name__ == "__main__":
    from pprint import pprint
    leagues = country_leagues()
    leagues_info = read_league_info_files()


