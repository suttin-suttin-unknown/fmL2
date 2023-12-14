from shared import convert_price_string

import json
import os
import time
import re
from operator import itemgetter

import requests
from prettytable import PrettyTable

class API:
    def __init__(self):
        self.host = 'https://transfermarkt-api.vercel.app'

    def search_player(self, player_name):
        response = requests.get(f'{self.host}/players/search/{player_name}')
        response.raise_for_status()
        return response.json()

    def get_player(self, player_id):
        response = requests.get(f'{self.host}/players/{player_id}/profile')
        response.raise_for_status()
        return response.json()
    
    def get_player_stats(self, player_id):
        response = requests.get(f'{self.host}/players/{player_id}/stats')
        response.raise_for_status()
        return response.json()
    
    def get_competition_clubs(self, competition_id, season_id):
        response = requests.get(f'{self.host}/competitions/{competition_id}/clubs', params={'season_id': season_id})
        response.raise_for_status()
        return response.json()
    
    def get_club_players(self, club_id, season_id):
        response = requests.get(f'{self.host}/clubs/{club_id}/players', params={'season_id': season_id})
        response.raise_for_status()
        return response.json()
    

def get_players_for_competition(competition_id, season_id):
    path = f'transfermarkt/competitions/{competition_id}/players/{season_id}'
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
        
    api = API()
    clubs = api.get_competition_clubs(competition_id, season_id)['clubs']
    competition_players = []
    for i in clubs:
        club_id, name = itemgetter('id', 'name')(i)
        print(f'Getting players for {club_id} ({name})')
        players = api.get_club_players(club_id, season_id)
        if players:
            competition_players.append({'club_id': club_id, 'name': name, **players})
        time.sleep(2)

    os.makedirs(os.path.split(path)[0], exist_ok=True)
    with open(path, 'w') as f:
        json.dump(competition_players, f)

    return competition_players


def filter_players(players, age):
    for i in players:
        club_name = i['name']
        for j in i['players']:
            if int(j['age']) <= age:
                yield {'club': club_name, **j}


def player_row(r):
    name = r.get('name', '-')
    nationality = '/'.join(r.get('nationality', []))
    position = r.get('position', '-')
    position = re.sub('-', ' ', position)
    if position == 'Goalkeeper':
        position = 'GK'
    else:
        position = ''.join([i[0] for i in position.split()])
    age = r.get('age', '-')
    club = r.get('club', '-')
    market_value = r.get('marketValue', '-')
    return [name, nationality, position, club, age, market_value]


def display_players_table(results):
    table = PrettyTable()
    fields = ['Name', 'Nationality', 'Position', 'Club', 'Age', 'Market Value']
    table.field_names = fields
    for i in fields:
        table.align[i] = 'l'

    for r in sorted(results, key=lambda d: (int(d['age']), -convert_price_string(d.get('marketValue', '-')))):
        table.add_row(player_row(r))
    
    print(table)
