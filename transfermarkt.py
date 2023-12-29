import codes
from shared import convert_price_string

import glob
import json
import os
import statistics
from datetime import datetime
from itertools import chain
from operator import itemgetter

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


class Competition:
    def __init__(self, id, season):
        self.id = id
        self.season = season

    def get_clubs(self):
        path = f'{main_wd}/competitions/{self.id}/clubs/{self.season}'
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
            
        clubs = API().get_competition_clubs(self.id, self.season)
        os.makedirs(os.path.split(path)[0], exist_ok=True)
        with open(path, 'w') as f:
            json.dump(clubs, f)

        return clubs
    
    def get_players(self, update=False):
        clubs = self.get_clubs()
        for c in clubs['clubs']:
            id = c['id']
            name = c['name']
            club = Club(id, self.season)
            players = club.get_players(update=update)
            for player in players.get('players', []):
                yield Player(**{'club': name, **player})



class Club:
    def __init__(self, id, season):
        self.id = id
        self.season = season

    def get_players(self, update=False):
        path = f'{main_wd}/clubs/{self.id}/players/{self.season}'
        if os.path.exists(path) and not update:
            with open(path) as f:
                return json.load(f)
            
        players = API().get_club_players(self.id, self.season)
        os.makedirs(os.path.split(path)[0], exist_ok=True)
        with open(path, 'w') as f:
            json.dump(players, f)

        return players


class Player:
    def __init__(self, **club_entry):
        self.id = club_entry.get('id')
        self.name = club_entry.get('name')
        self.club = club_entry.get('club')
        self.contract = club_entry.get('contract')
        self.date_of_birth = club_entry.get('dateOfBirth')
        self.foot = club_entry.get('foot')
        self.height = club_entry.get('height')
        self.joined = club_entry.get('joined')
        self.joined_on = club_entry.get('joinedOn')
        self.market_value = club_entry.get('marketValue')
        self.nationality = club_entry.get('nationality')
        self.position = club_entry.get('position')
        self.signed_from = club_entry.get('signedFrom')
        self.status = club_entry.get('status')

    @property
    def name_decoded(self):
        return unidecode(self.name)
    
    @property
    def name_parts(self):
        return dict((f'name{n + 1}', i) for n, i in enumerate(self.name_decoded.split(' ')))
    
    @property
    def nationalities(self):
        if len(self.nationality) > 1:
            return dict((f'nationality{n + 1}', i) for n, i in enumerate(self.nationality))
    
    @property
    def market_value_number(self):
        if self.market_value:
            return convert_price_string(self.market_value)
    
    @property
    def age_relative(self):
        if self.date_of_birth:
            dob = datetime.strptime(self.date_of_birth, '%b %d, %Y')
            now = datetime.now()
            years = now.year - dob.year
            months = now.month - dob.month
            if now.day < dob.day:
                months -= 1
            months = (months + 12) % 12
            return years, months
    
    @property
    def height_cm(self):
        if self.height:
            try:
                hcm = self.height.strip('m')
                hcm = float(str(hcm).replace(',', '.'))
                hcm *= 100
                return hcm
            except ValueError:
                return None
    
    @property
    def height_ft(self):
        if self.height_cm:
            hft = self.height_cm / 2.54
            hft /= 12
            return hft
    
    @property
    def height_ft_in(self):
        if self.height_ft:
            hin = (self.height_ft % 1) * 12
            return int(self.height_ft), int(hin)
    
    def as_dict(self):
        info = {
            'id': self.id,
            'name': self.name,
            'club': self.club,
            'contract': self.contract,
            'date_of_birth': self.date_of_birth,
            'foot': self.foot,
            'height': self.height,
            'joined': self.joined,
            'joined_on': self.joined_on,
            'market_value': self.market_value,
            'nationality': '/'.join(self.nationality),
            'position': self.position,
            'signed_from': self.signed_from,
            'status': self.status
        }

        if self.age_relative:
            info['age'] = self.age_relative[0]

        if self.name != self.name_decoded:
            info['name_decoded'] = self.name_decoded

        if self.name_parts:
            info = {**self.name_parts, **info}

        if self.nationalities:
            info = {**self.nationalities, **info}

        if self.market_value_number:
            info['market_value_number'] = self.market_value_number

        if self.age_relative:
            info['age_relative'] = self.age_relative

        if self.height_cm:
            info['height_cm'] = self.height_cm

        if self.height_ft:
            info['height_ft'] = self.height_ft

        if self.height_ft_in:
            info['height_ft_in'] = self.height_ft_in

        return info

       
def save_competition_players_to_db(competition_id, season_id, log=False):
    clubs = get_competition_clubs(competition_id, season_id)['clubs']
    clubs = dict((club['id'], club['name']) for club in clubs)
    players = get_all_club_players(competition_id, season_id, log=log)
    players = list(chain(*[[{'club': clubs[i['id']], **j} for j in i.get('players', [])] for i in players]))
    players = [Player(**i).as_dict() for i in players]
    with get_client() as client:
        db = client['transfermarkt']
        table = db['players']
        player_ids = [i['id'] for i in players]
        result = table.find({'id': {'$in': player_ids}})
        player_ids = set(player_ids)
        result_ids = {i['id'] for i in list(result)}
        if len(player_ids) != len(result_ids):
            missing_players = player_ids - result_ids
            print(f'Saving {len(missing_players)} players')
            players = [i for i in players if i['id'] in missing_players]
            table.insert_many(players)


def get_club_names_for_country(country, tier=1):
    code = codes.competition_ids[country][tier - 1]
    path = glob.glob(f'{main_wd}/competitions/{code}/clubs/*')[0]
    season = os.path.split(path)[-1]
    clubs = get_competition_clubs(code, season)
    return [i['name'] for i in clubs['clubs']]


def get_all_clubs_for_country(country):
    country_codes = codes.competition_ids[country]
    leagues = []
    for i in range(len(country_codes)):
        leagues.extend(get_club_names_for_country(country, i))
    return leagues
    

def search(sort_by=('market_value_number', -1), limit=None, **filters):
    query = {}

    # age
    age_max = filters.get('age_max')
    age_min = filters.get('age_min')
    if age_max or age_min:
        query['age'] = {}
        if age_max:
            query['age']['$lte'] = age_max
        if age_min:
            query['age']['$gte'] = age_min

    # mv
    mv_max = filters.get('mv_max')
    mv_min = filters.get('mv_min')
    if mv_max or mv_min:
        query['market_value_number'] = {}
        if mv_max:
            query['market_value_number']['$lte'] = mv_max
        if mv_min:
            query['market_value_number']['$gte'] = mv_min

    # foot
    foot = filters.get('foot')
    if foot:
        query['foot'] = {'$in': foot}

    #positions
    positions = filters.get('positions')
    if positions:
        codes = dict((v, k) for k, v in codes.positions.items())
        positions = [codes[i] for i in positions]
        query['position'] = {'$in': positions}

    # clubs
    clubs = filters.get('clubs')
    if clubs:
        query['club'] = {'$in': clubs}


    with get_client() as client:
        db = client['transfermarkt']
        table = db['players']
        result = table.find(query)

        if limit:
            result = result.limit(limit)

        if sort_by:
            result = result.sort(*sort_by)

        return list(result)




def partition_by_age(results):
    key = 'date_of_birth'
    marked = [i for i in results if i.get(key)]
    unmarked = [i for i in results if not i.get(key)]
    partitions = sorted({datetime.strptime(i[key], '%b %d, %Y').year for i in results}, reverse=True)
    for p in partitions:
        yield [i for i in marked if datetime.strptime(i[key], '%b %d, %Y').year == p]

    if unmarked:
        yield unmarked


def partition_by_market_value(results):
    key = 'market_value_number'
    marked = [i for i in results if i.get(key)]
    unmarked = [i for i in results if not i.get(key)]
    values = [i[key] for i in marked]
    partitions = [max(values), statistics.mean(values), statistics.harmonic_mean(values), min(values), 0]
    for n in range(len(partitions) - 1):
        p_l = partitions[n]
        p_r = partitions[n + 1]
        yield [i for i in marked if p_r < i[key] <= p_l]

    if unmarked:
        yield unmarked


def partition_by_club(results):
    key = 'club'
    marked = [i for i in results if i.get(key)]
    unmarked = [i for i in results if not i.get(key)]
    partitions = sorted({i[key] for i in marked})
    for p in partitions:
        yield [i for i in marked if i[key] == p]

    if unmarked:
        yield unmarked

def partition_by_nationality(results):
    key = 'nationality'
    marked = [i for i in results if i.get(key)]
    unmarked = [i for i in results if not i.get(key)]
    partitions = sorted({i[key] for i in marked})
    for p in partitions:
        yield [i for i in marked if i[key] == p]
    
    if unmarked:
        yield unmarked


field_name_values = {
    'name': 'Name',
    'age': 'Age',
    'nationality': 'Nat.',
    'club': 'Club',
    'position': 'Pos.',
    'market_value': 'MV',
    'height': 'Height',
    'joined': 'joined',
    'foot': 'foot'
}

foot_codes = {
    'B': 'both',
    'L': 'left',
    'R': 'right'
}

default_keys = ['name', 'age', 'position', 'nationality', 'club', 'market_value', 'height', 'foot']



def display_table(results, keys=default_keys, include_loan=False):    
    table = PrettyTable()
    field_names = [field_name_values[k] for k in keys] 
    table.field_names = field_names

    for r in results:
        if 'position' in keys:
            r['position'] = codes.positions[r['position']]

        if 'height' in keys:
            if height_ft_in := r.get('height_ft_in'):
                feet, inches = height_ft_in
                height_str = r['height']
                height_str = f'{height_str} ({feet}\'{inches}\")'
                r['height'] = height_str

        if 'age' in keys:
            if age_relative := r.get('age_relative'):
                years, months = age_relative
                age_str = years
                if months != 0:
                    age_str = f'{age_str} ({months})'
                r['age'] = age_str

        if 'club' in keys:
            if include_loan:
                if r['joined'] and str(r['joined']).startswith('On loan'):
                    joined_str = r['joined'].split('until')
                    club = r['club']
                    r['club'] = f'{club} ({joined_str[0].strip()})'

        table.add_row([r.get(k) or '-' for k in keys])

    for i in field_names:
        table.align[i] = 'l'

    return table
