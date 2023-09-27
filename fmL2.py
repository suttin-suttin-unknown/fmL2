import configparser
import csv
import glob
import json
import os
import sqlite3
import sys
from itertools import chain
from functools import lru_cache
from itertools import chain

import requests

def config():
    config = configparser.ConfigParser()
    config.read("config.ini")
    return config

api_host = config()["api"]["host"]

@lru_cache(maxsize=None)
def league(id, tab=None, type=None, timezone=None):
    response = requests.get(f"{api_host}/leagues",
        headers={"Cache-Control": "no-cache"},
        params={"id": id, "tab": tab or "overview", 
                "type": type or "league", 
                "timeZone": timezone or "America/Los_Angeles"
        }
    )
    response.raise_for_status()
    return response.json()

def league_details(id):
    details = league(id)["details"]
    return {"details": {
        "name": details["name"], "country": details["country"],
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

def countries_list():
    with open("countries.json", "r") as f:
        countries = json.load(f)
        leagues = set(chain(*[country["leagues"] for country in countries]))
        return list(leagues)
    
def save_league(id):
    info = league_info(id)
    if info:
        path = "{root}/leagues/{id}.json".format(root=config()["data"]["root"], id=id)
        os.makedirs(os.path.split(path)[0], exist_ok=True)
        with open(path, "w") as f:
            json.dump(info, f)

def leagues_info():
    root = config()["data"]["root"]
    paths = glob.glob(f"{root}/leagues/*")
    info = []
    for path in paths:
        id = os.path.splitext(os.path.basename(path))[0]
        with open(path, "r") as f:
            info.append({"id": id, **json.load(f)})
    return info

def save_league_totw(league_id, until_year=2020):
    info = [i for i in leagues_info() if i["id"] == str(league_id)][0]
    stat_links = [l["link"] for l in info["stat_links"] 
                  if int(l["name"].split("/")[0]) >= until_year]
    if info and stat_links:
        totws = []
        for link in stat_links:
            response = requests.get(link).json()
            for round in response["rounds"]:
                if round["isCompleted"]:
                    totw_link = round["link"]
                    totw = requests.get(totw_link).json()
                    if totw and not totw.get("errorMessage"):
                        totws.append(totw)

        path = f"{config()['data']['root']}/totw/{league_id}.json"
        os.makedirs(os.path.split(path)[0], exist_ok=True)
        with open(path, "w") as f:
            json.dump(totws, f)

def group_players_by_totw_count():
    root = config()["data"]["root"]
    player_dict = {}
    for path in glob.glob(f"{root}/totw/*"):
        with open(path, "r") as f:
            for player in list(chain(*[players["players"] for players in json.load(f)])):
                id = player["participantId"]
                if player_dict.get(id):
                    player_dict[id].append(player)
                else:
                    player_dict[id] = [player]
    return player_dict

def update_players_list():
    player_dict = group_players_by_totw_count()
    header = list(player_dict.values())[0][0].keys()
    with open("{root}/players.csv".format(root=config()["data"]["root"]), "w") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(header))
        writer.writeheader()
        writer.writerows(list(chain(*player_dict.values())))

@lru_cache(maxsize=None)
def player(id):
    response = requests.get(f"{api_host}/playerData?id={id}", headers={"Cache-Control": "no-cache"})
    response.raise_for_status()
    return response.json()

def convert_market_value(market_value):
    if not market_value:
        return
    suffixes = {"K": 1000, "M": 1000000}
    suffix = market_value[-1].upper()
    if suffix in suffixes:
        value = float(market_value[:-1].strip("€"))
        return int(value * suffixes[suffix])

def player_info(id):
    player_info = player(id)
    name = player_info["name"]
    positions = sorted(player_info["origin"]["positionDesc"]["positions"], key=lambda d: -d["isMainPosition"])
    positions = [position["strPosShort"]["label"] for position in positions]
    player_props = dict([(prop["translationKey"], prop) for prop in player_info["playerProps"]])
    height = int(player_props["height_sentencecase"]["value"]["fallback"].split()[0])
    birth_date = int(player_props["years"]["dateOfBirth"]["utcTime"] / 1000)
    foot = player_props["preferred_foot"]["value"]["fallback"] # enum
    country = player_props["country_sentencecase"]["countryCode"]
    market_value = convert_market_value(player_props["transfer_value"]["value"]["fallback"])
    return {
        "id": id, "name": name, "positions": positions, "height": height, 
        "birth_date": birth_date, "foot": foot, 
        "country": country, "market_value": market_value
    }

def create_players_table():
    conn = sqlite3.connect("players.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY,
            name TEXT,
            height INTEGER,
            positions TEXT,
            birth_date INTEGER,
            foot TEXT,
            country TEXT,
            market_value INT
        )
    """)
    return conn

def save_player_info(id):
    info = player_info(id)
    conn = create_players_table()
    cursor = conn.cursor()
    name = info["name"]
    positions = ",".join(info["positions"])
    height = info["height"]
    birth_date = info["birth_date"]
    foot = info["foot"]
    country = info["country"]
    market_value = info["market_value"]
    cursor.execute("""
        INSERT INTO players (id, name, height, positions, birth_date, foot, country, market_value)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (id, name, height, positions, birth_date, foot, country, market_value))

def main():
    if not os.path.exists("countries.json"):
        print("Countries file not found.")
        sys.exit(1)

    info = leagues_info()
    totw_leagues = [i for i in info if i["stat_links"]]
    for league in totw_leagues:
        id = league["id"]
        print(f"Saving {id}.")
        try:
            save_league_totw(id)
        except:
            print(f"Error saving TOTW for league {id}")
            continue
        else:
            print(f"Saved.")

# Features

# def compress_data():
#     pass

# def backup_data():
#     pass

if __name__ == "__main__":
    pass