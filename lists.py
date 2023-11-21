import api

import json
import os
import time
from itertools import chain
from operator import itemgetter


import requests


def save_fixtures(league_id):
    for season in api.get_league(league_id)['allAvailableSeasons']:
        path = os.path.join('data/fixtures', str(league_id), season.replace('/', '_'))
        if not os.path.exists(path):
            print(f'Saving {path}')
            fixtures = api.get_fixtures(league_id, season)
            os.makedirs(os.path.split(path)[0], exist_ok=True)
            with open(path, 'w') as f:
                json.dump(fixtures, f)


# def save_totws(league_id):
#     for link in api.get_league(league_id)['stats'].get('seasonStatLinks', []):
#         season = link['Name']
#         rounds = api.get_totw_rounds(league_id, season).get('rounds', [])
#         rounds = [itemgetter('roundId', 'link')(r) for r in rounds]
#         for (round_id, link) in rounds:
#             path = os.path.join('data/totw', str(league_id), season.replace('/', '_'), round_id.replace('/', '_'))
#             if not os.path.exists(path):
#                 print(f'Saving {path}')
#                 totw = requests.get(link).json()
#                 os.makedirs(os.path.split(path)[0], exist_ok=True)
#                 with open(path, 'w') as f:
#                     json.dump(totw, f)

def save_totw_info(league_id):
    path = f'data/totw/{league_id}/info'
    if not os.path.exists(path):
        league = api.get_league(league_id)
        if league['stats'] and league['overview']['hasTotw']:
            path = f'data/totw/{league_id}/info'


def save_leagues():
    path = f'data/leagues.json'
    if not os.path.exists(path):
        leagues = api.get_all_leagues()
        leagues = list(chain(*(itemgetter('international', 'countries')(leagues))))
        countries = dict([itemgetter('ccode', 'name')(league) for league in leagues])
        leagues_ids = list(chain(*[[league['id'] for league in league['leagues']] for league in leagues]))
        league_list = []
        for i, league_id in enumerate(leagues_ids):
            print(f'Fetching league {league_id}')
            league = api.get_league(league_id)
            if league:
                ccode = league['details']['country']
                league_list.append({
                    'id': league_id,
                    'name': league['details']['name'],
                    'ccode': ccode,
                    'country': countries[ccode],
                    'hasTotw': league['overview']['hasTotw']
                })
            if (i + 1) % 50 == 0:
                print('Paused.')
                time.sleep(10)
        with open(path, 'w') as f:
            json.dump(league_list, f)
        
