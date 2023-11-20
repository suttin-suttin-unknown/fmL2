import re
from functools import lru_cache
from datetime import datetime

import requests
from dateutil.relativedelta import relativedelta


api_host = 'https://www.fotmob.com/api'

@lru_cache
def get_player(player_id):
    response = requests.get(f'{api_host}/playerData', {'id': player_id})
    return response.json()


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


def get_height(player_id, cm=True):
    player_props = get_player(player_id)['playerProps']
    height = [prop for prop in player_props if prop.get('title') == 'Height'][0]
    height = int(height['value']['fallback'].split(' ')[0])
    if cm:
        return height
    return convert_height(height)


def convert_height(height):
    inches = height / 2.54
    return int(inches // 12), int(inches % 12) 
    

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