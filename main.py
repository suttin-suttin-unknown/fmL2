import configparser
import json
import os
import re
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from functools import lru_cache
from itertools import chain

import requests


config = configparser.ConfigParser()
config.read('config.ini')
api_host = config['api']['host']
default_timezone = 'America/Vancouver'


@lru_cache
def get_league(league_id):
    return requests.get(f'{api_host}/leagues', {'id': league_id}).json()


@lru_cache
def get_league_totw_links(league_id):
    league = get_league(league_id)
    seasons = []
    for item in league['stats']['seasonStatLinks']:
        response = requests.get(item['TotwRoundsLink']).json()
        seasons.append({'name': item['Name'], **response})
    return seasons


def save_league_totws(league_id):
    totw_links = get_league_totw_links(league_id)
    for item in totw_links:
        season_name = str(item['name']).replace('/', '_')
        season_name = season_name
        for row in item['rounds']:
            round_id = str(row['roundId']).replace('/', '_')
            path = os.path.join('data/leagues', str(league_id), 'totw/seasons', season_name, 'rounds', round_id)
            print(path)
            if not os.path.exists(path):
                response = requests.get(row['link']).json()
                os.makedirs(os.path.split(path)[0], exist_ok=True)
                with open(path, 'w') as f:
                    json.dump(response, f)


@lru_cache
def get_league_fixtures(league_id):
    league = get_league(league_id)
    totw_seasons = [item['Name'] for item in league['stats']['seasonStatLinks']]
    season_fixtures = []
    for season in totw_seasons:
        response = requests.get(f'{api_host}/fixtures', {'id': league_id, 'season': season}).json()
        season_fixtures.append({'name': season, 'fixtures': response})
    return season_fixtures


@lru_cache
def get_player(player_id):
    response = requests.get(f'{api_host}/playerData', {'id': player_id})
    return response.json()


@lru_cache
def get_match_details(match_id):
    response = requests.get(f'{api_host}/matchDetails', {'matchId': match_id})
    return response.json()


def get_match_player_stats(match_id):
    try:
        return get_match_details(match_id)['content']['lineup']['lineup']
    except:
        return []


def save_league_match_stats(league_id):
    season_fixtures = get_league_fixtures(league_id)
    count = 0
    for season in season_fixtures:
        season_name = season['name']
        fixtures = season['fixtures']

        for fixture in fixtures:
            match_id = fixture['id']
            if fixture['status']['finished']:
                path = os.path.join('data/leagues', str(league_id), 'stats/seasons', 
                                    season_name.replace('/', '_'), 'matches', match_id)

                if not os.path.exists(path):
                    print(path)
                    stats = get_match_player_stats(match_id)
                    os.makedirs(os.path.split(path)[0], exist_ok=True)
                    with open(path, 'w') as f:
                        json.dump(stats, f)
                    count += 1

                if count % 50 == 0:
                    print('Pausing.')
                    time.sleep(15)


def get_stat_series(player_id, *stat_names):
    career_statistics = get_player(player_id)['careerStatistics']
    for club in career_statistics:
        for season in club['seasons']:
            stats = season['stats'][0]
            start = int(stats['startTS'] / 1000)
            name = season['name']
            tournament = stats['tournamentName']
            stats = [stat[-1] for stat in stats['statsArr']]
            if stat_names:
                stats = [stat for stat in stats if stat['key'] in stat_names]
            stats = dict((stat['key'], stat['value']) for stat in stats)
            yield {'start': start, 'name': name, 'tournament': tournament, 'stats': stats}


def get_total_minutes(player_id):
    total = 0
    series = get_stat_series(player_id, 'minutes_played')
    for row in series:
        total += row['stats'].get('minutes_played', 0)
    return total


def get_total_starts(player_id):
    total = 0
    series = get_stat_series(player_id, 'matches_started')
    for row in series:
        total += row['stats'].get('matches_started', 0)
    return total


def get_age(player_id, full=False):
    player_props = get_player(player_id)['playerProps']
    age = [prop for prop in player_props if prop.get('title') == 'Age'][0]
    if not full:
        return age['value']['fallback']
    birth_date = datetime.fromtimestamp(int(age['dateOfBirth']['utcTime'] / 1000))
    d = relativedelta(datetime.now(), birth_date)
    return d.years, d.months, d.weeks, d.days


def get_total_dribbles_attempted(player_id):
    total = 0
    series = get_stat_series(player_id, 'dribbles_attempted')
    for row in series:
        total += row['stats'].get('dribbles_attempted', 0)
    return total


def get_total_dribbles_succeeded(player_id):
    total = 0
    series = get_stat_series(player_id, 'dribbles_succeeded')
    for row in series:
        total += row['stats'].get('dribbles_succeeded', 0)
    return total


def get_dribble_rate(player_id):
    return round(get_total_dribbles_succeeded(player_id) / get_total_dribbles_attempted(player_id), 3)


def get_dribble_rates(player_id):
    series = get_stat_series(player_id, 'dribbles_succeeded', 'dribbles_attempted')
    series = sorted(series, key=lambda r: -r['start'])
    rates = []
    for row in series:
        rate = None
        succeeded = row['stats'].get('dribbles_succeeded', 0)
        attempted = row['stats'].get('dribbles_attempted')
        if succeeded:
            rate = round(succeeded / attempted, 3)
        rates.append({'start': row['start'], 'name': row['name'], 'tournament': row['tournament'], 'dribble_rate': rate})
    return rates


def get_total_appearances(player_id):
    senior_appearances = get_player(player_id)['careerHistory']['careerData']['careerItems']['senior']
    total = 0
    for team in senior_appearances:
        if not team['hasUncertainData'] and team['appearances']:
            appearances = int(re.findall(r'\d+', team['appearances'])[0])
            total += appearances
    return total
