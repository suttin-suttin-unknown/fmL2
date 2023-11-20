import api

import json
import os


def save_fixtures(league_id, season):
    path = os.path.join('data/fixtures', str(league_id), season.replace('/', '_'))
    if not os.path.exists(path):
        fixtures = []
        for fixture in api.get_fixtures(league_id, season):
            if fixture['status']['finished'] and fixture['status'].get('reason', {}).get('short', '') == 'FT':
                fixtures.append({'id': fixture['id'], 'utcTime': fixture['status']['utcTime']})
        os.makedirs(os.path.split(path)[0], exist_ok=True)
        with open(path, 'w') as f:
            json.dump(fixtures, f)
