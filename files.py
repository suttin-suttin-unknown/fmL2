import api

import json
import os
from itertools import chain
from operator import itemgetter


import requests


def get_all_leagues():
    path = f'data/all_leagues'
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    
    all_leagues = api.get_all_leagues()
    all_leagues = list(chain(*(itemgetter('international', 'countries')(all_leagues))))
    with open(path, 'w') as f:
        json.dump(all_leagues, f)

    return all_leagues


def get_fixtures(league_id, season):
    path = os.path.join('data/fixtures', str(league_id), season.replace('/', '_'))
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
        
    fixtures = api.get_fixtures(league_id, season)
    os.makedirs(os.path.split(path)[0], exist_ok=True)
    with open(path, 'w') as f:
        json.dump(fixtures, f)

    return fixtures


def get_totw_info(league_id):
    path = f'data/totw/{league_id}/info'
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
        
    league = api.get_league(league_id)
    totw_info = []
    try:
        stat_links = league['stats']['seasonStatLinks']
        stat_links = [itemgetter('Name', 'TotwRoundsLink')(item) for item in stat_links]
    except LookupError:
        stat_links = []

    for (season, link) in stat_links:
        response = requests.get(link).json()
        totw_info.append({'season': season, **response})

    os.makedirs(os.path.split(path)[0], exist_ok=True)
    with open(path, 'w') as f:
        json.dump(totw_info, f)

    return totw_info


def get_totw(league_id, season, round_id):
    path = os.path.join('data/totw', str(league_id), season.replace('/', '_'), round_id.replace('/', '_'))
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)

    info = get_totw_info(league_id)
    totw = []
    try:
        rounds = [item['rounds'] for item in info if item['season'] == season][0]
        link = [item['link'] for item in rounds if item['roundId'] == round_id][0]
        totw = requests.get(link).json()
    except IndexError:
        pass

    if totw:
        os.makedirs(os.path.split(path)[0], exist_ok=True)
        with open(path, 'w') as f:
            json.dump(totw, f)
    
    return totw

    
def get_league_seasons(league_id):
    seasons = []
    leagues = get_all_leagues()
    c_i, l_i = -1, -1
    found = False
    for i, country in enumerate(leagues):
        for j, league in enumerate(country['leagues']):
            if league['id'] == league_id:
                found = True
                c_i, l_i = i, j
                break

    if found:
        seasons = leagues[c_i]['leagues'][l_i].get('seasons', [])

    if not seasons:
        league = api.get_league(league_id)
        seasons = league['allAvailableSeasons']
        leagues[c_i]['leagues'][l_i]['seasons'] = seasons

        path = f'data/all_leagues'
        with open(path, 'w') as f:
            json.dump(leagues, f)

    return seasons  


def get_fixtures(league_id, season):
    path = os.path.join('data/fixtures', str(league_id), season.replace('/', '_'))
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
        
    fixtures = []
    available_seasons = get_league_seasons(league_id)
    if available_seasons and season in available_seasons:
        fixtures = api.get_fixtures(league_id, season)

    if fixtures:
        os.makedirs(os.path.split(path)[0], exist_ok=True)
        with open(path, 'w') as f:
            json.dump(fixtures, f)

    return fixtures


