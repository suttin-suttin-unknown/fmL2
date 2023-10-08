import configparser
import csv
import glob
import json
import os
import sqlite3
import sys
import time
from functools import lru_cache
from itertools import chain

import requests

def config():
    config = configparser.ConfigParser()
    config.read("config.ini")
    return config

api_host = config()["api"]["host"]
data_dir = config()["data"]["root"]

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

def read_totw_file(league_id):
    path = f"{data_dir}/totw/{league_id}.json"
    with open(path, "r") as f:
        return json.load(f)
    
def get_totw_ids(league_id):
    try:
        totw_list = read_totw_file(league_id)
        ids = set(chain(*[[player["participantId"] for player in totw["players"]] 
                           for totw in totw_list]))
        return list(ids)
    except FileNotFoundError:
        pass

def save_totw_list(league_id):
    ids = get_totw_ids(league_id)
    if ids:
        with DB("players.db") as db:
            db.create_player_table()
            for i in ids:
                try:
                    print(f"Getting player {i}")
                    info = player_info(i)
                    db.insert_player(info)
                except requests.exceptions.HTTPError as error:
                    print(f"Error getting {i}: {str(error)}")
                    time.sleep(5)


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
    try:
        positions = sorted(player_info["origin"]["positionDesc"]["positions"], key=lambda d: -d["isMainPosition"])
        positions = "/".join(position["strPosShort"]["label"] for position in positions)
    except LookupError:
        positions = ""
    
    player_props = dict([(prop["translationKey"], prop) for prop in player_info["playerProps"]])
    try:
        height = int(player_props["height_sentencecase"]["value"]["fallback"].split()[0])
    except LookupError:
        height = -1

    birth_date = int(player_props["years"]["dateOfBirth"]["utcTime"] / 1000)
    
    try:
        foot = player_props["preferred_foot"]["value"]["fallback"] # enum
    except LookupError:
        foot = ""

    country = player_props["country_sentencecase"]["countryCode"]
    try:
        market_value = convert_market_value(player_props["transfer_value"]["value"]["fallback"])
    except LookupError:
        market_value = -1

    return {
        "id": id, "name": name, "positions": positions, "height": height, 
        "birth_date": birth_date, "foot": foot, 
        "country": country, "market_value": market_value
    }

class DB:
    def __init__(self, db_file):
        self.db_file = db_file
        self.connection = None
        self.cursor = None

    def __enter__(self):
        self.connection = sqlite3.connect(self.db_file)
        self.cursor = self.connection.cursor()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        if self.connection:
            self.connection.commit()
            self.cursor.close()
            self.connection.close()

    def create_player_table(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS players(id, name, positions, height, birth_date, foot, country, market_value)")

    def insert_player(self, info):
        values = info.values()
        self.cursor.execute(f"INSERT INTO players VALUES ({','.join(['?'] * len(values))})", tuple(values))

    def get_player(self, id):
        self.cursor.execute(f"SELECT * FROM players WHERE id=?", (id,))
        return self.cursor.fetchone()

@lru_cache(maxsize=None)
def team(id, tab=None, type=None, timezone=None):
    response = requests.get(f"{api_host}/teams",
        headers={"Cache-Control": "no-cache"},
        params={"id": id, "tab": tab or "overview", 
                "type": type or "league", 
                "timeZone": timezone or "America/Los_Angeles"
        }
    )
    response.raise_for_status()
    return response.json()

def team_transfers(id):
    try:
        transfers = team(id)["transfers"]["data"]
        return list(chain(*transfers.values()))
    except LookupError:
        return []

def get_team_transfers(id):
    path = f"{data_dir}/teams/transfers/{id}.json"
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
        
    transfers = team_transfers(id)
    if transfers:
        os.makedirs(os.path.split(path)[0], exist_ok=True)
        with open(path, "w") as f:
            json.dump(transfers, f)
    
        return transfers
    
def get_league_transfers(id):
    teams = league_teams(id)["teams"]
    transfers = {}
    for team in teams:
        transfers[team] = get_team_transfers(team)
    return transfers

@lru_cache(maxsize=None)
def match_details(id):
    response = requests.get(f"{api_host}/matchDetails?matchId={id}")
    response.raise_for_status()
    return response.json()

def get_match_player_info(id):
    details = match_details(id)["content"]
    [home, away] = details["lineup"]["lineup"]
    home_players = list(chain(*home["players"])) + home["bench"]
    away_players = list(chain(*away["players"])) + away["bench"]
    return [player for player in [*home_players, *away_players] if player.get("stats", [])]

def get_match_player_stats(id):
    players = get_match_player_info(id)
    stats = []
    for player in players:
        player_stats = [i["stats"] for i in player["stats"]]
        player_stats = [dict([(i["key"], i["value"]) for i in list(stats.values())]) for stats in player_stats]
        player_stats = {k: v for d in player_stats for k, v in d.items() if k}
        stats.append({
            "id": player["id"], 
            "name": player["name"]["fullName"],
            "position": player["position"],
            "role": player.get("role"),
            "stats": player_stats
        })
    return stats

def get_league_totw_info(league_id):
    try:
        round_ratings = []
        for data in read_totw_file(league_id):
            totw = data["players"]
            round_id = totw[0]["roundNumber"]
            round_ratings.append({
                "round": round_id,
                "ratings": [p["rating"] for p in totw],
                "match_ids": list(set(p["matchId"] for p in totw))
            })
        return round_ratings
    except FileNotFoundError:
        return []
    
def get_league_totw_match_details(league_id):
    for n, item in enumerate(get_league_totw_info(league_id), start=1):
        match_detail = []
        min_rating = min(item["ratings"])
        for match_id in item["match_ids"]:
            print(f"Fetching {match_id}.")
            info = get_match_player_stats(match_id)
            for player in info:
                if player["stats"].get("rating_title", -1) >= min_rating:
                    match_detail.append(player)
            with open(f"{data_dir}/match_stats/{match_id}.json", "w") as f:
                json.dump(match_detail, f)
        if n % 10 == 0:
            print("Pausing.")
            time.sleep(5)

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

if __name__ == "__main__":
    pass