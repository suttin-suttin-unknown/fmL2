from shared import convert_price_string, convert_value

import csv
import glob
import json
import os
import time
from datetime import datetime
from itertools import chain
from operator import itemgetter

import requests
from unidecode import unidecode
from prettytable import PrettyTable
from pymongo import MongoClient

main_root = 'data'
main_wd = f'{main_root}/transfermarkt'

test_root = 'data2'
test_wd = f'{test_root}/transfermarkt'

competition_ids = {
    'Albania': ['ALB1', 'ALB2'],
    'Algeria': ['ALG1'],
    'Andorra': ['AND1', 'AND2'],
    'Angola': ['AN1L'],
    'Argentina': ['AR1N', 'ARG2', 'ARG3'],
    'Armenia': ['ARM1', 'ARM2'],
    'Australia': ['AUS1', 'A2SW', 'A2VI'],
    'Austria': ['A1', 'A2'],
    'Azerbaijan': ['AZ1'],
    'Bangladesh': ['BGD1'],
    'Belgium': ['BE1', 'BE2'],
    'Belarus': ['WER1'],
    'Bolivia': ['BO1A'],
    'Brazil': ['BRA1', 'BRA2'],
    'Bosnia-Herzegovina': ['BOS1'],
    'Bulgaria': ['BU1', 'BU2'],
    'Canada': ['CDN1'],
    'Cambodia': ['KHM1'],
    'Chile': ['CLPD', 'CL2B'],
    'China': ['CSL'],
    'Colombia': ['COL1'],
    'Costa Rica': ['CRPD'],
    'Croatia': ['KR1'],
    'Cyprus': ['ZYP1'],
    'Czech Republic': ['TS1', 'TS2'],
    'Denmark': ['DK1', 'DK2'],
    'Ecuador': ['EL1S'],
    'Egypt': ['EGY1'],
    'El Salvador': ['SL1A'],
    'England': ['GB1', 'GB2', 'GB3', 'GB4'],
    'Faroe Islands': ['FARO'],
    'Fiji': ['FIJ1'],
    'Finland': ['FI1'],
    'France': ['FR1', 'FR2', 'FR3'],
    'Germany': ['L1', 'L2', 'L3'],
    'Ghana': ['GHPL'],
    'Gibraltar': ['GI1'],
    'Greece': ['GR1', 'GRS2'],
    'Georgia': ['GE1N'],
    'Guatemala': ['GU1A'],
    'Honduras': ['HO1A'],
    'Hong Kong': ['HGKG'],
    'Hungary': ['UNG1'],
    'Iceland': ['IS1'],
    'India': ['IND1'],
    'Indonesia': ['IN1L'],
    'Iran': ['IRN1'],
    'Ireland': ['IR1', 'IR2'],
    'Israel': ['ISR1', 'ISR2'],
    'Italy': ['IT1', 'IT2'],
    'Jamaica': ['JPL1'],
    'Japan': ['JAP1', 'JAP2', 'JAP3'],
    'Kazakhstan': ['KAS1'],
    'Kosovo': ['KO1'],
    'Kyrgyzstan': ['KG1L'],
    'Laos': ['LAO1'],
    'Latvia': ['LET1'],
    'Lithuania': ['LI1'],
    'Luxembourg': ['LUX1'],
    'Macedonia': ['MAZ1'],
    'Malaysia': ['MYS1'],
    'Malta': ['MAL1'],
    'Mexico': ['MEXA', 'MEX2'],
    'Montenegro': ['MNE1'],
    'Moldova': ['MO1N'],
    'Morocco': ['MAR1'],
    'Mozambique': ['MO1L'],
    'Myanmar': ['MYA1'],
    'Netherlands': ['NL1', 'NL2'],
    'New Zealand': ['NZNL'],
    'Nicaragua': ['NC1A'],
    'Nigeria': ['NPFL'],
    'Northern Ireland': ['NIR1'],
    'Norway': ['NO1', 'NO2'],
    'Oman': ['OM1L'],
    'Panama': ['PN1C'],
    'Paraguay': ['PR1C'],
    'Peru': ['TDeC'],
    'Poland': ['PL1', 'PL2', 'PL2L'],
    'Portugal': ['PO1', 'PO2', 'PT3A'],
    'Romania': ['RO1', 'RO2'],
    'Russia': ['RU1', 'RU2'],
    'San Marino': ['SMR1'],
    'Saudi Arabia': ['SA1'],
    'Scotland': ['SC1', 'SC2'],
    'Serbia': ['SER1'],
    'Singapore': ['SIN1'],
    'Slovakia': ['SLO1', 'SK2'],
    'Slovenia': ['SL1'],
    'South Africa': ['SFA1'],
    'South Korea': ['RSK1', 'RSK2'],
    'Spain': ['ES1', 'ES2', 'E3G2', 'E3G1'],
    'Sweden': ['SE1', 'SE2', 'SE3N', 'SE3S'],
    'Switzerland': ['C1', 'C2'],
    'Taiwan': ['TFPL'],
    'Tajikistan': ['TAD1'],
    'Thailand': ['THA1'],
    'Tunisia': ['TUN1'],
    'Turkey': ['TR1', 'TR2'],
    'UAE': ['UAE1'],
    'Ukraine': ['UKR1', 'UKR2'],
    'United States': ['MLS1', 'USL', 'USC3'],
    'Uruguay': ['URU1', 'URU2'],
    'Uzbekistan': ['UZ1'],
    'Venezuela': ['VZ1L', 'VN2C'],
    'Vietnam': ['VIE1'],
    'Wales': ['WAL1']
}

position_codes = {
    'Attacking Midfield': 'AM',
    'Central Midfield': 'CM',
    'Centre-Back': 'CB',
    'Centre-Forward': 'CF',
    'Defensive Midfield': 'DM',
    'Goalkeeper': 'GK',
    'Left Midfield': 'LM',
    'Left Winger': 'LW',
    'Left-Back': 'LB',
    'Mittelfeld': 'M',
    'Right Midfield': 'RM',
    'Right Winger': 'RW',
    'Right-Back': 'RB',
    'Second Striker': 'SS',
    'Striker': 'ST'
}

subregion_codes = {
    'C-EU': 'Central Europe',
    'E-EU': 'Eastern Europe',
    'N-EU': 'Northern Europe',
    'S-EU': 'Southern Europe',
    'SE-EU': 'Southeast Europe',
    'W-EU': 'Western Europe'
}

def get_client():
    return MongoClient('localhost', 27017)


# def get_db():
#     client = MongoClient('localhost', 27017)
#     return client['transfermarkt']


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


def get_competition_clubs(competition_id, season_id):
    path = f'{main_wd}/competitions/{competition_id}/clubs/{season_id}'
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
        
    clubs = API().get_competition_clubs(competition_id, season_id)
    os.makedirs(os.path.split(path)[0], exist_ok=True)
    with open(path, 'w') as f:
        json.dump(clubs, f)

    return clubs


def get_club_players(club_id, season_id, update=False):
    path = f'{main_wd}/clubs/{club_id}/players/{season_id}'
    if os.path.exists(path) and not update:
        with open(path) as f:
            return json.load(f)
        
    players = API().get_club_players(club_id, season_id)
    os.makedirs(os.path.split(path)[0], exist_ok=True)
    with open(path, 'w') as f:
        json.dump(players, f)

    return players


def get_all_club_players(competition_id, season_id, update=False, log=False):
    clubs = get_competition_clubs(competition_id, season_id)['clubs']
    for club in clubs:
        id, name = itemgetter('id', 'name')(club)
        if log:
            print(f'Getting players for {id} ({name})')
        yield get_club_players(club['id'], season_id, update=update)


class Player:
    def __init__(self, **club_entry):
        self.id = club_entry.get('id')
        self.name = club_entry.get('name')
        self.age = club_entry.get('age')
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


def search(**filters):
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

    with get_client() as client:
        db = client['transfermarkt']
        table = db['players']
        result = table.find(query)
        return list(result)


# def backfill_db():
#     paths = [i for i in glob.glob(f'data/transfermarkt/competitions/*')]
#     paths = list(chain(*[glob.glob(f'{i}/clubs/*') for i in paths]))
#     print(paths)
#     for path in paths:
#         _, _, _, c_id, _, s_id = path.split('/')
#         save_competition_players_to_db(c_id, s_id, log=True)
#         time.sleep(5)

field_name_values = {
    'name': 'Name',
    'age': 'Age',
    'nationality': 'Nat.',
    'club': 'Club',
    'position': 'Pos.',
    'market_value': 'MV',
    'height': 'Height',
    'joined': 'joined'
}

foot_codes = {
    'B': 'both',
    'L': 'left',
    'R': 'right'
}

default_keys = ['name', 'age', 'nationality', 'club', 'position', 'market_value', 'height']

def display_table(results, limit=None, keys=default_keys, sort='market_value_number', order=-1):    
    table = PrettyTable()
    field_names = [field_name_values[k] for k in keys] 
    table.field_names = field_names

    if sort:
        results = sorted(results, key=lambda d: order * d[sort])

    if limit:
        results = results[0:limit]

    for r in results:
        if 'position' in keys:
            r['position'] = position_codes[r['position']]

        if 'height' in keys:
            height_ft_in = r['height_ft_in']
            feet, inches = height_ft_in
            height_str = r['height']
            height_str = f'{height_str} ({feet}\'{inches}\")'
            r['height'] = height_str

        if 'age' in keys:
            years, months = r['age_relative']
            age_str = years
            if months != 0:
                age_str = f'{age_str} ({months} months)'
            r['age'] = age_str

        if 'club' in keys:
            if r['joined'] and str(r['joined']).startswith('On loan'):
                joined_str = r['joined'].split('until')
                club = r['club']
                r['club'] = f'{club} ({joined_str[0].strip()})'
        
        table.add_row(itemgetter(*keys)(r))

    for i in field_names:
        table.align[i] = 'l'

    return table

# country_codes = {
#     'France': 'FR',
#     'Algeria': 'DZ'
#     ''
# }

def country_to_emoji(country_code):
    # Base Unicode point for regional indicator symbols
    base = ord('🇦')
    
    # Calculate the Unicode points for the country code
    flag = ''.join(chr(base + ord(letter) - ord('A')) for letter in country_code.upper())
    
    return flag


if __name__ == '__main__':
    q_both = search(mv_max=25000000, age_max=22, foot=['both'])
    table = display_table(q_both, limit=20)