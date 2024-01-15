import codes
import shared

import json
import random
import re
import statistics
import time
from collections import defaultdict
from datetime import datetime
from operator import itemgetter
from itertools import chain

import requests
from unidecode import unidecode
from prettytable import PrettyTable
from pymongo import MongoClient


DB_NAME = 'transfermarkt'


def get_client():
    return MongoClient('localhost', 27017)


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


class Record:
    def __init__(self, name):
        self.name = name

    def find(self, id):
        with get_client() as client:
            table = client[DB_NAME][self.name]
            return table.find_one({'id': id})
        
    def find_many(self, ids):
        with get_client() as client:
            table = client[DB_NAME][self.name]
            return list(table.find({'id': {'$in': ids}}))
        
    def save(self, record):
        with get_client() as client:
            table = client[DB_NAME][self.name]
            table.insert_one(record)

    def save_many(self, records):
        with get_client() as client:
            table = client[DB_NAME][self.name]
            table.insert_many(records)
                

class Competition(Record):
    def __init__(self):
        super().__init__(name='competitions')

    def from_country(self, tier=None, country_name=None, country_code=None):
        countries = None
        with open('countries.json') as f:
            countries = json.load(f)
        
        if country_name:
            country = [i for i in countries if i['name'] == country_name][0]
        elif country_code:
            country = [i for i in countries if i['code'] == country_code][0]

        competitions = []
        if not tier:
            for c in country['competitions'] + country['youth_competitions']:
                if isinstance(c, list):
                    competitions.extend(c)
                if isinstance(c, str):
                    competitions.append(c)

        if tier:
            if tier == 'y':
                competitions.extend(country['youth_competitions'])
            else:
                tc = country['competitions'][tier - 1]
                if isinstance(tc, list):
                    competitions.extend(tc)
                if isinstance(tc, str):
                    competitions.append(tc)

        if len(competitions) > 1:
            return self.find_many(competitions)
        if len(competitions) == 1:
            return [self.find(competitions[0])]


class Club(Record):
    def __init__(self):
        super().__init__(name='clubs')

    def from_country(self, tier=None, country_name=None, country_code=None):
        comps = Competition().from_country(tier=tier, country_name=country_name, country_code=country_code)
        if comps:
            clubs = list(chain(*[i['clubs'] for i in comps]))
            clubs_ids = [i['id'] for i in clubs]
            result = list(self.find_many(clubs_ids))
            result = dict((i['id'], i) for i in result)
            return [{'club': i['name'], 'club_id': i['id'], **result[i['id']]} for i in clubs]
        

class Player(Record):
    def __init__(self):
        super().__init__(name='players')

    def from_country(self, tier=None, country_name=None, country_code=None):
        clubs = Club().from_country(tier=tier, country_name=country_name, country_code=country_code)
        players = []
        if clubs:
            for i in clubs:
                club = i['club']
                club_id = i['club_id']
                updated_at = i['updatedAt']
                players.extend([{'club': club, 'club_id': club_id, 'updated_at': updated_at, **j} for j in i.get('players', [])])
        return [self.format_row(i) for i in players]

    def format_row(self, row):
        formatted = dict((k, v) for k, v in row.items())
        updated_at = datetime.fromisoformat(formatted['updated_at'])
        name_decoded = unidecode(formatted['name'])
        formatted['name_decoded'] = name_decoded
        names = name_decoded.split(' ')
        formatted['last_name'] = names[-1]
        formatted['first_name'] = names[0]

        if club := formatted.get('club'):
            formatted['club_decoded'] = unidecode(club)

        if market_value := formatted.get('marketValue'):
            formatted['market_value_number'] = shared.convert_price_string(market_value)

        if nationality := formatted.get('nationality'):
            formatted['nationality1'] = nationality[0]
            if len(nationality) > 1:
                formatted['nationality2'] = nationality[1]   

        if joined_on := formatted.get('joinedOn'):
            joined_on = datetime.strptime(joined_on, '%b %d, %Y')
            joined_on_relative = shared.get_years_and_months(joined_on, updated_at)
            formatted['joined_on_relative'] = joined_on_relative

        if date_of_birth := formatted.get('dateOfBirth'):
            date_of_birth = datetime.strptime(date_of_birth, '%b %d, %Y')
            age_relative = shared.get_years_and_months(date_of_birth, updated_at)
            formatted['age_relative'] = age_relative
            formatted['age'] = age_relative[0]

        if height := formatted.get('height'):
            height_m = re.search(r'(\d+,\d+)m', height)
            if height_m:
                height_m = height_m.group(1).replace(',', '.')
                height_m = float(height_m)
                height_cm = height_m * 100
                height_ft = height_cm / 2.54
                height_ft /= 12
                height_in = (height_ft % 1) * 12
                formatted['height_us'] = [int(height_ft), int(height_in)]

        return formatted

    def save_country(self, country_name=None, country_code=None):
        players = self.from_country(country_name=country_name, country_code=country_code)
        ids = {i['id'] for i in players}
        result = self.find_many(list(ids))
        ids = ids - {i['id'] for i in result}
        if len(ids) != 0:
            print(f'Saving {len(ids)} players.')
            players = [i for i in players if i['id'] in ids]
            self.save_many(players)


def save_all_countries():
    with open('countries.json') as f:
        countries = json.load(f)

    for i in countries:
        name = i['name']
        Player().save_country(country_name=name)

    


def search_players(sort_by=('market_value_number', -1), limit=None, group_by=None, **filters):
    query = {}
    
    age_max = filters.get('age_max')
    age_min = filters.get('age_min')
    if age_max or age_min:
        query['age'] = {}

        if age_max:
            query['age']['$lte'] = age_max
        if age_min:
            query['age']['$gte'] = age_min

    mv_max = filters.get('mv_max')
    mv_min = filters.get('mv_min')
    if mv_max or mv_min:
        query['market_value_number'] = {}

        if mv_max:
            query['market_value_number']['$lte'] = mv_max
        if mv_min:
            query['market_value_number']['$gte'] = mv_min

    positions = filters.get('positions')
    if positions:
        query['position'] = {'$in': [codes.positions[i] for i in positions]}

    clubs = filters.get('clubs')
    if clubs:
        query['club_id'] = {'$in': clubs}

    results = None
    if query:
        with get_client() as client:
            db = client[DB_NAME]
            table = db['players']
            results = table.find(query)
            if sort_by:
                results = results.sort(*sort_by)

            if limit:
                results = results.limit(limit)

            results = list(results)

    return results

def search_by_name(name):
    name = unidecode(name)
    with get_client() as client:
        db = client[DB_NAME]
        table = db['players']
        return list(table.find({'name_decoded': name}))
    


# if __name__ == '__main__':
#     g = display_table(search_players(mv_max=2500000, age_max=28, limit=50, positions=['GK']), group_by='age')
#     d = display_table(search_players(mv_max=2500000, age_max=24, limit=300, positions=['CB', 'RB', 'LB', 'SW', 'D']), group_by='age')
#     m = display_table(search_players(mv_max=2500000, age_max=23, limit=300, positions=['CM', 'AM', 'DM', 'LM', 'RM', 'M']), group_by='age')
#     f = display_table(search_players(mv_max=2500000, age_max=23, limit=300, positions=['CF', 'ST', 'SS', 'LW', 'RW']), group_by='age')