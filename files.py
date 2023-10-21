from record import League, Player, Team
from utils import get_data_root_dir

import glob
import json
from itertools import chain
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
            path = f"{base}/{r.replace('/', '_').replace(' ', '_').lower()}.json"
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


def save_league_transfers(league_id):
    team_ids = League.from_api(league_id).team_ids
    if team_ids:
        for i in team_ids:
            team = Team.from_api(i)
            if team:
                print(f"Saving {i} transfers.")
                base = f"{get_data_root_dir()}/teams/{i}/transfers"
                os.makedirs(base, exist_ok=True)
                transfers_in = team.transfers_in
                if transfers_in:
                    with open(f"{base}/transfers_in.json", "w") as f:
                        json.dump(transfers_in, f)
                
                transfers_out = team.transfers_out
                if transfers_out:
                    with open(f"{base}/transfers_out.json", "w") as f:
                        json.dump(transfers_out, f)

                contract_extensions = team.contract_extensions
                if contract_extensions:
                    with open(f"{base}/contract_extensions.json", "w") as f:
                        json.dump(contract_extensions, f)


def get_league_totw_data(league_id):
    paths = glob.glob(f"{get_data_root_dir()}/league/{league_id}/totw/seasons/*")
    paths = list(chain(*[glob.glob(f"{path}/*") for path in paths]))
    for path in paths:
        with open(path, "r") as f:
            yield json.load(f)

def get_totw_occurences(player_id):
    for totw in get_league_totw_data(Player.from_api(player_id).league_id):
        occurence = [_ for _ in totw["players"] if _["participantId"] == player_id]
        if occurence:
            yield occurence

def get_totw_for_season(league_id, season):
    paths = glob.glob(f"{get_data_root_dir()}/league/{league_id}/totw/seasons/*")
    for path in paths:
        if path.split("/")[-1].split("_"):
            pass

