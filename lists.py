from record import League
from utils import get_data_root_dir

import json
from operator import itemgetter

import requests
import os

def get_totw_info(league_id):
    path = f"{get_data_root_dir()}/league/{league_id}/totw/info.json"
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    
    info = {}
    links = League.from_api(league_id).totw_links
    if links:
        for (season, link) in links:
            response = requests.get(link).json()
            info[season] = []
            for r in response["rounds"]:
                if r["isCompleted"]:
                    info[season].append(itemgetter(*["roundId", "link"])(r))
            info[season] = dict(info[season])

        os.makedirs(os.path.split(path)[0], exist_ok=True)
        with open(path, "w") as f:
            json.dump(info, f)

    return info


def save_totw(league_id):
    info = get_totw_info(league_id)
    for season in info:
        base = f"{get_data_root_dir()}/league/{league_id}/totw/seasons/{season.replace('/', '_')}"
        os.makedirs(base, exist_ok=True)
        rounds = info[season]
        for r in rounds:
            path = f"{base}/{r}.json"
            if not os.path.exists(path):
                url = rounds[r]
                response = requests.get(url).json()
                if response and "errorMessage" not in response:
                    print(f"Saving {season} {r} ({path})")
                    with open(path, "w") as f:
                        json.dump(response, f)


def save_league_player_stats(league_id):
    links = League.from_api(league_id).player_stat_links
    if links:
        for (stat, link) in links:
            print(f"Saving {stat}.")
            response = requests.get(link).json()
            if response:
                path = f"{get_data_root_dir()}/league/{league_id}/stats/{stat}.json"
                os.makedirs(os.path.split(path)[0], exist_ok=True)
                with open(path, "w") as f:
                    json.dump(response["TopLists"][0]["StatList"], f)



# def get_league_stat_info(league_id):
#     links = League.from_api(league_id).player_stat_links
#     if links:
#         for (stat, link) in links:
#             response = requests.get(link).json()
