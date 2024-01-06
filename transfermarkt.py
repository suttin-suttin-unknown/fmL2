import codes
import utils

import glob
import json
import os
import statistics
import random
import time
from datetime import datetime
from itertools import chain

import requests
from unidecode import unidecode
from prettytable import PrettyTable
from pymongo import MongoClient

main_root = 'data'
main_wd = f'{main_root}/transfermarkt'


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


def get_competitions(ids):
    with get_client() as client:
        db = client['transfermarkt']
        table = db['competitions']
        return list(table.find({'id': {'$in': ids}}))


def get_competition(id):
    with get_client() as client:
        db = client['transfermarkt']
        table = db['competitions']
        return table.find_one({'id': id})


def save_competition(id):
    with get_client() as client:
        db = client['transfermarkt']
        table = db['competitions']
        result = table.find_one({'id': id})
        if not result:
            year = datetime.now().year
            response = API().get_competition_clubs(id, year)
            table.insert_one(response)


def get_clubs(ids):
    with get_client() as client:
        db = client['transfermarkt']
        table = db['clubs']
        return list(table.find({'id': {'$in': ids}}))


def get_competition_clubs(id):
    competition = get_competition(id)
    if competition:
        names = dict((i['id'], i['name']) for i in competition['clubs'])
        clubs = get_clubs(list(names.keys()))
        clubs = [{'name': names[i['id']], **i} for i in clubs]
        return clubs


def save_club(id, season):
    with get_client() as client:
        db = client['transfermarkt']
        table = db['clubs']
        result = table.find_one({'id': id})
        if not result:
            response = API().get_club_players(id, season)
            table.insert_one(response)


def get_players(ids):
    with get_client() as client:
        db = client['transfermarkt']
        table = db['players']
        return list(table.find({'id': {'$in': ids}}))
    

def save_players(players):
    ids = {player.id for player in players}
    ids = ids - {i['id'] for i in get_players(list(ids))}
    if len(ids) > 0:
        print(f'Saving {len(ids)} players.')
        players = [i.as_dict() for i in players if i.id in ids]
        if len(players) != 0:
            with get_client() as client:
                db = client['transfermarkt']
                table = db['players']
                table.insert_many(players)


class Player:
    def __init__(
            self, 
            id, 
            name,
            contract, 
            current_club, 
            date_of_birth, 
            foot, 
            height, 
            joined, 
            joined_on,
            market_value,
            nationality,
            position,
            signed_from,
            status,
            updated_at
        ):
        self.id = id
        self.name = name
        self.contract = contract
        self.current_club = current_club
        self.date_of_birth = date_of_birth
        self.foot = foot
        self.height = height
        self.joined = joined
        self.joined_on = joined_on
        self.market_value = market_value
        self.nationality = nationality
        self.position = position
        self.signed_from = signed_from
        self.status = status
        self.updated_at = updated_at

    @classmethod
    def from_competition(cls, id):
        clubs = get_competition_clubs(id)
        for club in clubs:
            players = club.get('players', [])
            for player in players:
                yield cls(
                    current_club=club['name'],
                    updated_at=club['updatedAt'],
                    id=player.get('id'),
                    name=player.get('name'),
                    contract=player.get('contract'), 
                    date_of_birth=player.get('dateOfBirth'), 
                    foot=player.get('foot'), 
                    height=player.get('height'), 
                    joined=player.get('joined'),
                    joined_on=player.get('joinedOn'),
                    market_value=player.get('marketValue'),
                    nationality=player.get('nationality'),
                    position=player.get('position'),
                    signed_from=player.get('signedFrom'),
                    status=player.get('status')
                )
    
    @property
    def age(self):
        if self.age_relative:
            return self.age_relative[0]

    @property
    def update_at_dt(self):
        return datetime.fromisoformat(self.updated_at)
    
    @property
    def date_of_birth_dt(self):
        return datetime.strptime(self.date_of_birth, '%b %d, %Y')
    
    @property
    def joined_on_dt(self):
        return datetime.strptime(self.joined_on, '%b %d, %Y')

    @property
    def name_decoded(self):
        if self.name:
            return unidecode(self.name)
    
    @property
    def age_relative(self):
        if self.date_of_birth:
            return utils.get_years_and_months(self.date_of_birth_dt, self.update_at_dt)

    @property
    def contract_number(self):
        if self.contract:
            try:
                return utils.convert_price_string(self.contract)
            except:
                return None
            
    @property
    def height_m(self):
        if self.height:
            try:
                height_m = self.height.strip('m')
                height_m = height_m.replace(',', '.')
                return float(height_m)
            except:
                return None
            
    @property
    def height_cm(self):
        if self.height_m:
            return self.height_m * 100
        
    @property
    def height_ft(self):
        if self.height_cm:
            height_ft = self.height_cm / 2.54
            height_ft /= 12
            return height_ft
        
    @property
    def height_ft_in(self):
        if self.height_ft:
            height_in = (self.height_ft % 1) * 12
            return int(self.height_ft), int(height_in)
        
    @property
    def joined_on_relative(self):
        if self.joined_on:
            return utils.get_years_and_months(self.joined_on_dt, self.update_at_dt)
        
    @property
    def market_value_number(self):
        if self.market_value:
            return utils.convert_price_string(self.market_value)

    @property
    def multinational(self):
        return len(self.nationality) > 1

    @property
    def nationalities(self):
        return dict((f'nationality{n}', i) for n, i in enumerate(self.nationality, start=1))
            
    def as_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'name_decoded': self.name_decoded,
            'age': self.age,
            'age_relative': self.age_relative,
            'contract': self.contract,
            'contract_number': self.contract_number,
            'current_club': self.current_club,
            'date_of_birth': self.date_of_birth,
            'foot': self.foot,
            'height': self.height,
            'height_m': self.height_m,
            'height_cm': self.height_cm,
            'height_ft': self.height_ft,
            'height_ft_in': self.height_ft_in,
            'joined': self.joined,
            'joined_on': self.joined_on,
            'joined_on_relative': self.joined_on_relative,
            'market_value': self.market_value,
            'market_value_number': self.market_value_number,
            'multinational': self.multinational,
            'position': self.position,
            'signed_from': self.signed_from,
            'status': self.status,
            'updated_at': self.updated_at,
            **self.nationalities
        }


def search_players(sort_by=('market_value_number', -1), **filters):
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
        query['current_club'] = {'$in': clubs}

    results = None
    if query:
        with get_client() as client:
            db = client['transfermarkt']
            table = db['players']
            results = table.find(query)
            if sort_by:
                results = results.sort(*sort_by)

            results = list(results)

    return results


def get_countries():
    with open('countries.json') as f:
        return json.load(f)


def search_by_country(country, tiers=1, **filters):
    countries = get_countries()
    country = [i for i in countries if i['name'] == country][0]
    competitions = country['competitions'][0:tiers]
    clubs = []
    for i in competitions:
        if isinstance(i, list):
            clubs.extend(i)
        else:
            clubs.append(i)
    clubs = list(chain(*[[j['name'] for j in get_competition(i)['clubs']] for i in clubs]))
    return search_players(**{'clubs': clubs, **filters})


def display_table(results):
    table = PrettyTable()
    field_names = ['Name', 'Age', 'Nat.', 'Pos.', 'Club', 'MV', 'Height', 'Foot']
    table.field_names = field_names

    positions = dict((v, k) for k, v in codes.positions.items())
    tm_names = dict((i['transfermarkt_name'], i['code']) for i in get_countries())

    for i in results:
        name = i['name']
        age = i['age']
        club = i['current_club']
        market_value = i['market_value']
        height = i['height']
        foot = i['foot']
        position = positions[i['position']]
        nationality1 = tm_names[i['nationality1']]
        if nationality2 := i.get('nationality2'):
            nationality = '/'.join([nationality1, tm_names[nationality2]])
        else:
            nationality = nationality1
        table.add_row([name, age, nationality, club, position, market_value, height, foot])

    for i in field_names:
        table.align[i] = 'l'

    return table