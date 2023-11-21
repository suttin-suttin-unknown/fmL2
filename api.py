import functools

import requests
from cachetools import cached, TTLCache


def call_api(host, route, params={}):
    response = requests.get(f'{host}/{route}', params=params)
    response.raise_for_status()
    return response.json()


fotmob_api = functools.partial(call_api, host='https://www.fotmob.com/api')


def get_fixtures(league_id, season):
    return fotmob_api(route='fixtures', params={'id': league_id, 'season': season})


def get_all_leagues():
    return fotmob_api(route='allLeagues')


@cached(cache=TTLCache(maxsize=100, ttl=60 * 60))
def get_league(league_id):
    return fotmob_api(route='leagues', params={'id': league_id})


def get_totw_rounds(league_id, season):
    return fotmob_api(route='team-of-the-week/rounds', params={'leagueId': league_id, 'season': season})


def get_match_details(match_id):
    return fotmob_api(route='matchDetails', params={'matchId': match_id})


def get_team(team_id):
    return fotmob_api(route='teams', params={'id': team_id})


def get_player_data(player_id):
    return fotmob_api(route='playerData', params={'id': player_id})
