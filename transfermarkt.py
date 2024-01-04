import codes
import shared

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
    

def save_club(id, season):
    with get_client() as client:
        db = client['transfermarkt']
        table = db['clubs']
        result = table.find_one({'id': id})
        if not result:
            response = API().get_club_players(id, season)
            table.insert_one(response)
        




