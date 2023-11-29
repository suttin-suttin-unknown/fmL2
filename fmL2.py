import glob
import json
import os
import re
import time
from itertools import chain
from operator import itemgetter

import requests


DATA_ROOT = 'data'

# hosts
FOTMOB_API_HOST = 'https://www.fotmob.com/api'
TRANSFERMARKT_API_HOST = 'https://transfermarkt-api.vercel.app'

# routes
FOTMOB_ALL_LEAGUES_ROUTE = 'allLeagues'
FOTMOB_LEAGUES_ROUTE = 'leagues'
FOTMOB_FIXTURES_ROUTE = 'fixtures'
FOTMOB_MATCH_DETAILS_ROUTE = 'matchDetails'
FOTMOB_TOTW_ROUNDS_ROUTE = 'team-of-the-week/rounds'
FOTMOB_TOTW_TEAM_ROUTE = 'team-of-the-week/team'


def get_or_raise(url, params={}):
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()


def get_document(path):
    document = None
    if os.path.exists(path):
        with open(path) as f:
            document = json.load(f)
    return document


def save_document(path, document, force=False):
    if not os.path.exists(path) or force:
        os.makedirs(os.path.split(path)[0], exist_ok=True)
        with open(path, 'w') as f:
            json.dump(document, f)


def get_fotmob_all_leagues():
    path = f'{DATA_ROOT}/fotmob/{FOTMOB_ALL_LEAGUES_ROUTE}'
    all_leagues = get_document(path)
    if not all_leagues:
        url = f'{FOTMOB_API_HOST}/{FOTMOB_ALL_LEAGUES_ROUTE}'
        all_leagues = get_or_raise(url)
        save_document(path, all_leagues)
    return all_leagues


def get_fotmob_league_ids():
    leagues = get_fotmob_all_leagues()
    leagues = list(chain(*itemgetter('international', 'countries')(leagues)))
    leagues = list(chain(*[country['leagues'] for country in leagues]))
    league_ids = [i['id'] for i in leagues]
    return league_ids


def get_fotmob_league(league_id):
    league = {}
    league_ids = get_fotmob_league_ids()
    if league_id in league_ids:
        path = f'{DATA_ROOT}/fotmob/{FOTMOB_LEAGUES_ROUTE}/{league_id}'
        league = get_document(path)
        if not league:
            url = f'{FOTMOB_API_HOST}/{FOTMOB_LEAGUES_ROUTE}'
            league = get_or_raise(url, params={'id': league_id})
            save_document(path, league)
    return league


def get_fotmob_fixtures(league_id, season):
    fixtures = []
    league = get_fotmob_league(league_id)
    seasons = league.get('allAvailableSeasons', [])
    if season in seasons:
        path = os.path.join(f'{DATA_ROOT}/fotmob/{FOTMOB_FIXTURES_ROUTE}', str(league_id), season.replace('/', '_'))
        fixtures = get_document(path)
        if not fixtures:
            url = f'{FOTMOB_API_HOST}/{FOTMOB_FIXTURES_ROUTE}'
            fixtures = get_or_raise(url, params={'id': league_id, 'season': season})
            save_document(path, fixtures)
    return fixtures


def get_all_fotmob_fixtures(league_id):
    all_fixtures = []
    league = get_fotmob_league(league_id)
    seasons = league.get('allAvailableSeasons', [])
    for season in seasons:
        path = os.path.join(f'{DATA_ROOT}/fotmob/{FOTMOB_FIXTURES_ROUTE}', str(league_id), season.replace('/', '_'))
        fixtures = get_document(path)
        if not fixtures:
            url = f'{FOTMOB_API_HOST}/{FOTMOB_FIXTURES_ROUTE}'
            fixtures = get_or_raise(url, params={'id': league_id, 'season': season})
            print(f'Saving {path}')
            save_document(path, fixtures)
        all_fixtures.append(fixtures)
    return all_fixtures


def get_all_fotmob_fixture_ids(league_id):
    all_fixtures = get_all_fotmob_fixtures(league_id)
    all_fixtures = list(chain(*all_fixtures))
    fixture_ids = [i['id'] for i in all_fixtures]
    return fixture_ids


def save_all_fotmob_league_matches(league_id):
    fixture_ids = get_all_fotmob_fixture_ids(league_id)
    saved_ids = {os.path.split(i)[-1] for i in glob.glob(f'{DATA_ROOT}/fotmob/{FOTMOB_MATCH_DETAILS_ROUTE}/{league_id}/*')}
    unsaved_ids = set(fixture_ids) - saved_ids
    num_ids = len(unsaved_ids)
    for n, i in enumerate(unsaved_ids):
        path = f'{DATA_ROOT}/fotmob/{FOTMOB_MATCH_DETAILS_ROUTE}/{league_id}/{i}'
        match_details = get_document(path)
        if not match_details:
            url = f'{FOTMOB_API_HOST}/{FOTMOB_MATCH_DETAILS_ROUTE}'
            match_details = get_or_raise(url, params={'matchId': i})
            print(f'({n + 1}/{num_ids}) Saving {path}')
            save_document(path, match_details)
        
        if (n + 1) % 100 == 0:
            print('Pausing.')
            time.sleep(15)


def save_fotmob_totw_rounds(league_id):
    league = get_fotmob_league(league_id)
    totw_seasons = [i['Name'] for i in league.get('stats', {}).get('seasonStatLinks', []) if i.get('TotwRoundsLink')]
    for season in totw_seasons:
        path = os.path.join(f'{DATA_ROOT}/fotmob/{FOTMOB_TOTW_ROUNDS_ROUTE}', str(league_id), season.replace('/', '_'))
        totw_rounds = get_document(path)
        if not totw_rounds:
            url = f'{FOTMOB_API_HOST}/{FOTMOB_TOTW_ROUNDS_ROUTE}'
            totw_rounds = get_or_raise(url, params={'leagueId': league_id, 'season': season})
            print(f'Saving {path}')
            save_document(path, totw_rounds)


def save_fotmob_totws(league_id):
    save_fotmob_totw_rounds(league_id)
    league = get_fotmob_league(league_id)
    totw_seasons = [i['Name'] for i in league.get('stats', {}).get('seasonStatLinks', []) if i.get('TotwRoundsLink')]
    for season in totw_seasons:
        path = os.path.join(f'{DATA_ROOT}/fotmob/{FOTMOB_TOTW_ROUNDS_ROUTE}', str(league_id), season.replace('/', '_'))
        totw_rounds = get_document(path)
        round_ids = [i['roundId'] for i in totw_rounds['rounds']]
        for round_id in round_ids:
            path = os.path.join(f'{DATA_ROOT}/fotmob/{FOTMOB_TOTW_TEAM_ROUTE}/{league_id}', season.replace('/', '_'), re.sub(r'[ /]', '_', round_id))
            if not os.path.exists(path):
                url = f'{FOTMOB_API_HOST}/{FOTMOB_TOTW_TEAM_ROUTE}'
                totw = get_or_raise(url, params={'leagueId': league_id, 'season': season, 'roundId': round_id})
                print(f'Saving {path}')
                save_document(path, totw)
