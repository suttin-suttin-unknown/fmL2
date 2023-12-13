import json
import os
from itertools import chain
from operator import itemgetter

import requests
from pymongo import MongoClient

leagues_file = 'leagues.json'


def get_db():
    client = MongoClient('localhost', 27017)
    return client['fotmob']


class API:
    def __init__(self):
        self.host = 'https://www.fotmob.com/api'

    def get_all_leagues(self):
        response = requests.get(f'{self.host}/allLeagues')
        response.raise_for_status()
        return response.json()

    def get_league(self, league_id):
        response = requests.get(f'{self.host}/leagues', params={'id': league_id})
        response.raise_for_status()
        return response.json()
    
    def get_fixtures(self, league_id, season):
        response = requests.get(f'{self.host}/fixtures', params={'id': league_id, 'season': season})
        response.raise_for_status()
        return response.json()
    
    def get_player(self, player_id):
        response = requests.get(f'{self.host}/playerData', params={'id': player_id})
        response.raise_for_status()
        return response.json()


def get_all_leagues():
    if os.path.exists(leagues_file):
        with open(leagues_file) as f:
            return json.load(f)
        
    leagues = API().get_all_leagues()
    leagues = list(chain(*itemgetter('international', 'countries')(leagues)))
    with open(leagues_file, 'w') as f:
        json.dump(leagues, f, indent=4)
    
    return leagues
    

def get_league(league_id):
    ids = list(chain(*[[j['id'] for j in i['leagues']] for i in get_all_leagues()]))
    if league_id in ids:
        table = get_db()['leagues']
        league = table.find_one({'id': league_id})
        if not league:
            league = API().get_league(league_id)
            seasons = league['allAvailableSeasons']
            stats = league['stats'] or {}
            stat_links = stats.get('seasonStatLinks', [])
            league = {'id': league_id, 'seasons': seasons, 'stat_links': stat_links}
            table.insert_one(league)
        return league
    

def get_totw_rounds(league_id, season):
    league = get_league(league_id)
    if league:
        table = get_db()['totw_rounds']
        query = {'league_id': league_id, 'season': season}
        totw_rounds = table.find_one(query)
        if not totw_rounds:
            totw_info = [i for i in league['stat_links'] if i['Name'] == season]
            if len(totw_info) == 1:
                url = totw_info[0]['TotwRoundsLink']
                response = requests.get(url)
                response.raise_for_status()
                totw_rounds = response.json()
                totw_rounds = {**query, 'rounds': totw_rounds['rounds']}
                table.insert_one(totw_rounds)
        return totw_rounds
    

def get_totw_teams(league_id, season):
    totw_rounds = get_totw_rounds(league_id, season)['rounds']
    table = get_db()['totw_team']
    query = {'league_id': league_id, 'season': season}
    totw_teams = table.find(query)
    missing_rounds = {i['roundId'] for i in totw_rounds} - {i['round_id'] for i in totw_teams}
    if len(missing_rounds) > 0:
        teams = []
        for i in totw_rounds:
            round_id, link = itemgetter('roundId', 'link')(i)
            if round_id in missing_rounds:
                print(f'Fetching team from {link}')
                team = requests.get(link).json()
                teams.append({**query, 'round_id': round_id, 'players': team['players']})
        table.insert_many(teams)
    return list(table.find(query))


def get_totw_players(league_id, season):
    teams = get_totw_teams(league_id, season)
    players = list(chain(*[[j for j in i['players']] for i in teams]))
    return players
    