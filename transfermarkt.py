import codes
import shared

import json
import statistics
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
            return self.find(competitions[0])


class Club(Record):
    def __init__(self):
        super().__init__(name='clubs')

    def from_country(self, tier=None, country_name=None, country_code=None):
        comps = Competition().from_country(tier=tier, country_name=country_name, country_code=country_code)
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
        for i in clubs:
            print(i)
            club = i['club']
            club_id = i['club_id']
            players.extend([{'club': club, 'club_id': club_id, **j} for j in i['players']])
        return players
            

default_header = ['Name', 'Age', 'Nat.', 'Pos.', 'Club', 'MV', 'Height', 'Foot']


class Table:
    def __init__(self, header=default_header, age_relative=True, country_code=True, position_code=True, height_us=True):
        self.header = header
        self.age_relative = age_relative
        self.country_code = country_code
        self.position_code = position_code
        self.height_us = height_us
        self._results = []

    def format_age(self, result):
        age = None
        if self.age_relative:
            years, months = result['age_relative']
            age = str(years)
            if months != 0:
                age = ' - '.join([age, f'{months} months'])
        else:
            age = str(result['age_relative'][0])

        return age

    def format_nationality(self, result):
        n1, n2 = result['nationality1'], result.get('nationality2')
        if self.country_code:
            tm_codes = dict(itemgetter('transfermarkt_name', 'code')(i) for i in get_countries())
            n1 = tm_codes[n1]
            if n2:
                n2 = tm_codes[n2]
        return n1 if not n2 else '/'.join([n1, n2])
    
    def format_position(self, result):
        position = result['position']
        if self.position_code:
            position_codes = dict((v, k) for k, v in codes.positions.items())
            position = position_codes[position]
        return position
    
    def format_height(self, result):
        height = result['height']
        if self.height_us:
            height_ft_in = '{}\'{}\"'.format(*result['height_ft_in'])
            height = f'{height} ({height_ft_in})'
        return height

    def format_row(self, result):
        name = result['name']
        age = self.format_age(result) or '-'
        nationality = self.format_nationality(result) or '-'
        position = self.format_position(r) or '-'
        club = self.get('club', '-')
        market_value = self.get('marketValue', '-')
        height = self.format_height(result) or '-'
        foot = result.get('foot', '-')
        return [name, age, nationality, position, club, market_value, height, foot] 

    def display(self): 
        if self._results:
            table = PrettyTable()
            field_names = self.header
            table.field_names = field_names

            for r in self._results:
                table.add_row(self.format_row(r))

            for i in field_names:
                table.align[i] = 'l'

            return table







# class Player:
#     def __init__(
#             self, 
#             id, 
#             name,
#             contract, 
#             club,
#             club_id,
#             date_of_birth, 
#             foot, 
#             height, 
#             joined, 
#             joined_on,
#             market_value,
#             nationality,
#             position,
#             signed_from,
#             status,
#             updated_at
#         ):
#         self.id = id
#         self.name = name
#         self.contract = contract
#         self.club = club
#         self.club_id = club_id
#         self.date_of_birth = date_of_birth
#         self.foot = foot
#         self.height = height
#         self.joined = joined
#         self.joined_on = joined_on
#         self.market_value = market_value
#         self.nationality = nationality
#         self.position = position
#         self.signed_from = signed_from
#         self.status = status
#         self.updated_at = updated_at

#     @classmethod
#     def from_competition(cls, id):
#         clubs = get_competition_clubs(id)
#         for club in clubs:
#             players = club.get('players', [])
#             for player in players:
#                 yield cls(
#                     club=club['name'],
#                     club_id=club['id'],
#                     updated_at=club['updatedAt'],
#                     id=player.get('id'),
#                     name=player.get('name'),
#                     contract=player.get('contract'), 
#                     date_of_birth=player.get('dateOfBirth'), 
#                     foot=player.get('foot'), 
#                     height=player.get('height'), 
#                     joined=player.get('joined'),
#                     joined_on=player.get('joinedOn'),
#                     market_value=player.get('marketValue'),
#                     nationality=player.get('nationality'),
#                     position=player.get('position'),
#                     signed_from=player.get('signedFrom'),
#                     status=player.get('status')
#                 )
    
#     @property
#     def age(self):
#         if self.age_relative:
#             return self.age_relative[0]

#     @property
#     def update_at_dt(self):
#         return datetime.fromisoformat(self.updated_at)
    
#     @property
#     def date_of_birth_dt(self):
#         return datetime.strptime(self.date_of_birth, '%b %d, %Y')
    
#     @property
#     def joined_on_dt(self):
#         return datetime.strptime(self.joined_on, '%b %d, %Y')

#     @property
#     def name_decoded(self):
#         if self.name:
#             return unidecode(self.name)
    
#     @property
#     def age_relative(self):
#         if self.date_of_birth:
#             return utils.get_years_and_months(self.date_of_birth_dt, self.update_at_dt)

#     @property
#     def contract_number(self):
#         if self.contract:
#             try:
#                 return utils.convert_price_string(self.contract)
#             except:
#                 return None
            
#     @property
#     def height_m(self):
#         if self.height:
#             try:
#                 height_m = self.height.strip('m')
#                 height_m = height_m.replace(',', '.')
#                 return float(height_m)
#             except:
#                 return None
            
#     @property
#     def height_cm(self):
#         if self.height_m:
#             return self.height_m * 100
        
#     @property
#     def height_ft(self):
#         if self.height_cm:
#             height_ft = self.height_cm / 2.54
#             height_ft /= 12
#             return height_ft
        
#     @property
#     def height_ft_in(self):
#         if self.height_ft:
#             height_in = (self.height_ft % 1) * 12
#             return int(self.height_ft), int(height_in)
        
#     @property
#     def joined_on_relative(self):
#         if self.joined_on:
#             return utils.get_years_and_months(self.joined_on_dt, self.update_at_dt)
        
#     @property
#     def market_value_number(self):
#         if self.market_value:
#             return utils.convert_price_string(self.market_value)

#     @property
#     def multinational(self):
#         return len(self.nationality) > 1

#     @property
#     def nationalities(self):
#         return dict((f'nationality{n}', i) for n, i in enumerate(self.nationality, start=1))
            
#     def as_dict(self):
#         return {
#             'id': self.id,
#             'name': self.name,
#             'name_decoded': self.name_decoded,
#             'age': self.age,
#             'age_relative': self.age_relative,
#             'contract': self.contract,
#             'contract_number': self.contract_number,
#             'club': self.club,
#             'club_id': self.club_id,
#             'date_of_birth': self.date_of_birth,
#             'foot': self.foot,
#             'height': self.height,
#             'height_m': self.height_m,
#             'height_cm': self.height_cm,
#             'height_ft': self.height_ft,
#             'height_ft_in': self.height_ft_in,
#             'joined': self.joined,
#             'joined_on': self.joined_on,
#             'joined_on_relative': self.joined_on_relative,
#             'market_value': self.market_value,
#             'market_value_number': self.market_value_number,
#             'multinational': self.multinational,
#             'position': self.position,
#             'signed_from': self.signed_from,
#             'status': self.status,
#             'updated_at': self.updated_at,
#             **self.nationalities
#         }


def search_players(sort_by=('market_value_number', -1), limit=None, **filters):
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
        query['club'] = {'$in': clubs}

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


def get_countries():
    with open('countries.json') as f:
        return json.load(f)


def group_by_age(results):
    ages = sorted({i['age'] for i in results})
    for age in ages:
        yield sorted([i for i in results if i['age'] == age], key=lambda d: d['age_relative'])


def group_by_club(results):
    clubs = {i['club'] for i in results}
    for club in clubs:
        yield [i for i in results if i['club'] == club]


def group_by_market_value_stats(results):
    w_mv = [i for i in results if i['market_value_number']]
    wo_mv = [i for i in results if not i['market_value_number']]
    market_values = [i['market_value_number'] for i in w_mv]
    mv_max = max(market_values)
    mv_mean = statistics.mean(market_values)
    mv_h_mean = statistics.harmonic_mean(market_values)
    mv_min = min(market_values)
    yield [i for i in w_mv if mv_mean < i['market_value_number'] <= mv_max]
    yield [i for i in w_mv if mv_h_mean < i['market_value_number'] <= mv_mean]
    yield [i for i in w_mv if mv_min < i['market_value_number'] <= mv_h_mean]
    yield [i for i in w_mv if 0 < i['market_value_number'] <= mv_min]

    if wo_mv:
        yield wo_mv


def group_by_positions(results):
    goalkeepers = itemgetter(*['GK'])(codes.positions)
    defenders = itemgetter(*['LB', 'CB', 'RB', 'D', 'SW'])(codes.positions)
    midfielders = itemgetter(*['LM', 'RM', 'CM', 'AM', 'DM', 'M'])(codes.positions)
    forwards = itemgetter(*['LW', 'ST', 'CF', 'RW', 'SS'])(codes.positions)
    yield [i for i in results if i['position'] in goalkeepers]
    yield [i for i in results if i['position'] in defenders]
    yield [i for i in results if i['position'] in midfielders]
    yield [i for i in results if i['position'] in forwards]



