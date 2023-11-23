import json
import os
from itertools import chain
from operator import itemgetter

import requests


HOST = 'https://www.fotmob.com/api'
ALL_LEAGUES = 'allLeagues'


def get_url(url, params={}):
    return requests.get(url, params=params).json()

    
def get_file(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
        

def save_file(path, data):
    os.makedirs(os.path.split(path)[0], exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f)


def get_all_leagues():
    path = f'data/{ALL_LEAGUES}'
    all_leagues = get_file(path)
    if not all_leagues:
        all_leagues = get_url(f'{HOST}/{ALL_LEAGUES}')
        save_file(path, all_leagues)
    all_leagues = list(chain(*(itemgetter('international', 'countries')(all_leagues))))
    return all_leagues