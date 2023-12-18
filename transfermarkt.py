from shared import convert_price_string, convert_value

import glob
import json
import os
import time
import re
import statistics
from itertools import chain
from operator import itemgetter

import requests
from prettytable import PrettyTable


competition_ids = {
    'Albania': ['ALB1', 'ALB2'],
    'Algeria': ['ALG1'],
    'Argentina': ['AR1N', 'ARG2', 'ARG3'],
    'Armenia': ['ARM1', 'ARM2'],
    'Australia': ['AUS1', 'A2SW', 'A2VI'],
    'Austria': ['A1', 'A2'],
    'Azerbaijan': ['AZ1'],
    'Belgium': ['BE1', 'BE2'],
    'Belarus': ['WER1'],
    'Bolivia': ['BO1A'],
    'Brazil': ['BRA1', 'BRA2'],
    'Bosnia-Herzegovina': ['BOS1'],
    'Bulgaria': ['BU1', 'BU2'],
    'Chile': ['CLPD', 'CL2B'],
    'Colombia': ['COL1'],
    'Croatia': ['KR1'],
    'Cyprus': ['ZYP1'],
    'Czechia': ['TS1', 'TS2'],
    'Denmark': ['DK1', 'DK2', 'DK30'],
    'Ecuador': ['EL1S'],
    'Egypt': ['EGY1'],
    'England': ['GB2', 'GB3', 'GB4'],
    'Finland': ['FI1'],
    'France': ['FR1', 'FR2', 'FR3'],
    'Germany': ['L1', 'L2', 'L3'],
    'Ghana': ['GHPL'],
    'Greece': ['GR1'],
    'Georgia': ['GE1N'],
    'Guatemala': ['GU1A'],
    'Honduras': ['HO1A'],
    'Hungary': ['UNG1'],
    'Israel': ['ISR1'],
    'Iceland': ['IS1'],
    'Ireland': ['IR1'],
    'Italy': ['IT1', 'IT2'],
    'Japan': ['JAP1', 'JAP2', 'JAP3'],
    'Kazakhstan': ['KAS1'],
    'Latvia': ['LET1'],
    'Lithuania': ['LI1'],
    'Luxembourg': ['LUX1'],
    'Macedonia': ['MAZ1'],
    'Mexico': ['MEXA'],
    'Montenegro': ['MNE1'],
    'Moldova': ['MO1N'],
    'Morocco': ['MAR1'],
    'Netherlands': ['NL1', 'NL2'],
    'New Zealand': ['NZNL'],
    'Nigeria': ['NPFL'],
    'Northern Ireland': ['NIR1'],
    'Norway': ['NO1', 'NO2'],
    'Panama': ['PN1C'],
    'Paraguay': ['PR1C'],
    'Peru': ['TDeC'],
    'Poland': ['PL1', 'PL2'],
    'Portugal': ['PO1', 'PO2'],
    'Romania': ['RO1', 'RO2'],
    'Russia': ['RU1', 'RU2'],
    'Scotland': ['SC1', 'SC2'],
    'Serbia': ['SER1'],
    'Slovakia': ['SLO1'],
    'Slovenia': ['SL1'],
    'South Africa': ['SFA1'],
    'South Korea': ['RSK1', 'RSK2'],
    'Spain': ['ES1', 'ES2', 'E3G2', 'E3G1'],
    'Sweden': ['SE1', 'SE2', 'SE3N', 'SE3S'],
    'Switzerland': ['C1', 'C2'],
    'Tunisia': ['TUN1'],
    'Turkiye': ['TR1', 'TR2'],
    'Ukraine': ['UKR1'],
    'United States': ['MLS1', 'USL'],
    'Uruguay': ['URU1', 'URU2'],
    'Venezuela': ['VZ1L']
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
    'Right Midfield': 'RM',
    'Right Winger': 'RW',
    'Right-Back': 'RB',
    'Second Striker': 'SS'
}

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
    def __init__(self, id, name, season_id, clubs):
        self.id = id
        self.name = name
        self.season_id = season_id
        self.clubs = clubs

    @classmethod
    def load(cls, id, season_id):
        competition = None
        path = f'data/transfermarkt/competitions/{id}/{season_id}'
        if os.path.exists(path):
            with open(path) as f:
                competition = json.load(f)

        if not competition:
            competition = API().get_competition_clubs(id, season_id)
            os.makedirs(os.path.split(path)[0], exist_ok=True)
            with open(path, 'w') as f:
                json.dump(competition, f)

        id, name, season_id, clubs = itemgetter('id', 'name', 'seasonID', 'clubs')(competition)
        return cls(id, name, season_id, clubs)
    
    def save_all_players(self):
        for club in self.clubs:
            club_id, club_name = itemgetter('id', 'name')(club)
            path = f'data/transfermarkt/competitions/{self.id}/players/{self.season_id}/{club_id}'
            players = None
            if os.path.exists(path):
                with open(path) as f:
                    players = json.load(f)
            
            if not players:
                try:
                    print(f'Getting players for {club_id} ({club_name})')
                    players = API().get_club_players(club_id, self.season_id)
                    os.makedirs(os.path.split(path)[0], exist_ok=True)
                    with open(path, 'w') as f:
                        json.dump(players, f)

                except requests.exceptions.HTTPError:
                    print(f'Error fetching players for {club_id}')
                    continue

            yield players

    def get_all_players(self):
        paths = glob.glob(f'data/transfermarkt/competitions/{self.id}/players/{self.season_id}/*')
        for path in paths:
            with open(path) as f:
                players = json.load(f)

            club_id = players['id']
            club_name = [i['name'] for i in self.clubs if i['id'] == club_id][0]

            for player in players['players']:
                yield {'club': club_name, **player}

    def filter_players(self, **filters):
        age_min = filters.get('age_min', 0)
        age_max = filters.get('age_max', float('inf'))
        market_value_min = filters.get('market_value_min', 0)
        market_value_max = filters.get('market_value_max', float('inf'))

        assert isinstance(age_min, int), f'Invalid age_min: {age_min}'
        assert isinstance(age_max, (int, float)), f'Invalid age_max: {age_max}'
        assert age_min < age_max, f'age_min ({age_min}) should be less than age_max ({age_max})'

        assert isinstance(market_value_min, int), f'Invalid market_value_min: {market_value_min}'
        assert isinstance(market_value_max, (int, float)), f'Invalid market_value_max: {market_value_max}'
        assert market_value_min < market_value_max, f'market_value_min ({market_value_min}) should be less than market_value_max ({market_value_max})' 

        for i in self.get_all_players():
            age = int(i['age'])
            market_value = convert_price_string(i['marketValue'])
            if age and market_value and (age_min <= age <= age_max) and (market_value_min <= market_value <= market_value_max):
                yield i 

        





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


def get_competition_files():
    competitions = glob.glob(f'transfermarkt/competitions/*')
    for i in competitions:
        players = glob.glob(os.path.join(i, 'players/*'))
        for j in players:
            with open(j) as f:
                yield json.load(f)


def filter_files(age_min, age_max, price_min, price_max):
    files = get_competition_files()
    filter_count = {}
    for n, i in enumerate(files):
        for club in i:
            players = club.get('players', [])
            for player in players:
                age = int(player.get('age') or -1)
                market_value = convert_price_string(player.get('marketValue', '-'))
                if (age_min <= age <= age_max) and (price_min <= market_value <= price_max):
                    player = {'club': club['name'], **player}
                    if filter_count.get(n):
                        filter_count[n].append(player_row(player))
                    else:
                        filter_count[n] = [player_row(player)]
    return filter_count
        

def get_player_display_table():
    table = PrettyTable()
    fields = ['Name', 'Nationality', 'Position', 'Club', 'Age', 'Market Value']
    table.field_names = fields
    for i in fields:
        table.align[i] = 'l'
    
    return table


def partition_player_table(players):
    unmarked = [i for i in players if i[-1] == '-']
    marked = [i for i in players if i[-1] != '-']
    if marked:
        market_values = [convert_price_string(i[-1]) for i in marked]
        mn = statistics.mean(market_values)
        hmn = statistics.harmonic_mean(market_values)
        mx = max(market_values)
        mx_mn = statistics.mean([i for i in market_values if mn <= i <= mx])
        mn_hmn = statistics.mean([i for i in market_values if hmn <= i <= mn])
        hmn_0 = statistics.mean([i for i in market_values if 0 <= i <= hmn])

        tier1a = [i for i in marked if mx_mn <= convert_price_string(i[-1]) <= mx]
        tier1b = [i for i in marked if mn <= convert_price_string(i[-1]) <= mx_mn]
        tier2a = [i for i in marked if mn_hmn <= convert_price_string(i[-1]) <= mn]
        tier2b = [i for i in marked if hmn <= convert_price_string(i[-1]) <= mn_hmn]
        tier3a = [i for i in marked if hmn_0 <= convert_price_string(i[-1]) <= hmn]
        tier3b = [i for i in marked if 0 <= convert_price_string(i[-1]) <= hmn_0]

        print(f'\nTier 1A\n')
        t1a = get_player_display_table()
        t1a.add_rows(tier1a)
        print(t1a)

        print(f'\nTier 1B\n')
        t1b = get_player_display_table()
        t1b.add_rows(tier1b)
        print(t1b)

        print(f'\nTier 2A\n')
        t2a = get_player_display_table()
        t2a.add_rows(tier2a)
        print(t2a)


    #     print(f'\nTier 2B\n')
    #     t2b = get_player_display_table()
    #     t2b.add_rows(tier2b)
    #     print(t2b)

    #     print(f'\nTier 3A\n')
    #     t3a = get_player_display_table()
    #     t3a.add_rows(tier3a)
    #     print(t3a)

    #     print(f'\nTier 3B\n')
    #     t3b = get_player_display_table()
    #     t3b.add_rows(tier3b)
    #     print(t3b)

    # if unmarked:
    #     table = get_player_display_table()
    #     table.add_rows(unmarked)
    #     print('\nUnmarked\n')
    #     print(table)


def print_display_table(players):
    table = get_player_display_table()
    table.add_rows(players)
    print(table)

    market_values = [convert_price_string(i[-1]) for i in players]
    print(f'Mean MV: {convert_value(statistics.mean(market_values))}')
    print(f'Harmonic Mean MV: {convert_value(statistics.harmonic_mean(market_values))}')


def get_tables(age_min, age_max, price_min, price_max):
    files = filter_files(age_min, age_max, price_min, price_max)
    players = sorted(files.values(), key=lambda d: len(d))
    for i in players:
        yield sorted(i, key=lambda d: -convert_price_string(d[-1]))
