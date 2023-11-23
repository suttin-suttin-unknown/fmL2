import json
import os
from itertools import chain

import requests


API_HOST = 'https://www.fotmob.com/api'
DATA_ROOT = 'data_copy'


def save_api_json(route, params={}):
    path = os.path.join(DATA_ROOT, route, *[str(v).replace('/', '_') for v in params.values()])
    if not os.path.exists(path):
        url = os.path.join(API_HOST, route)
        response = requests.get(url, params=params).json()
        if response:
            os.makedirs(os.path.split(path)[0], exist_ok=True)
            with open(path, 'w') as f:
                json.dump(response, f)


def save_league(league_id):
    save_api_json('leagues', params={'id': league_id})


def save_fixtures(league_id, season):
    save_league(league_id)
    league = {}
    with open(f'{DATA_ROOT}/leagues/{league_id}') as f:
        league = json.load(f)
    
    available_seasons = league.get('allAvailableSeasons', [])
    if season in available_seasons:
        save_api_json('fixtures', params={'id': league_id, 'season': season})


def save_totw_rounds(league_id, season):
    save_league(league_id)
    league = {}
    with open(f'{DATA_ROOT}/leagues/{league_id}') as f:
        league = json.load(f)

    stat_links = league.get('stats', {}).get('seasonStatLinks', [])
    available_seasons = [i['Name'] for i in stat_links]
    if season in available_seasons:
        save_api_json('team-of-the-week/rounds', params={'leagueId': league_id, 'season': season})


def save_totw(league_id, season, round_id):
    save_totw_rounds(league_id, season)
    totw_rounds = {}
    path = os.path.join(DATA_ROOT, 'team-of-the-week/rounds', str(league_id), season.replace('/', '_'))
    with open(path) as f:
        totw_rounds = json.load(f)

    totw_rounds = [i['roundId'] for i in totw_rounds.get('rounds', [])]
    if str(round_id) in totw_rounds:
        save_api_json('team-of-the-week/team', params={'leagueId': league_id, 'season': season, 'roundId': round_id})

