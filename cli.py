import codes
from transfermarkt import Player


import json
import statistics
from operator import itemgetter

from prettytable import PrettyTable
import click


DEFAULT_PREFS = 'prefs/main.json'


default_keys = {
    'name': 'N',
    'age': 'A',
    'nationality': 'NT',
    'position': 'PS',
    'club': 'C',
    'marketValue': 'MV',
    'height': 'H',
    'foot': 'F' 
}


def abbreviate_number(num):
    if num >= 1_000_000_000:
        return f"{num / 1_000_000_000:.1f}b"
    elif num >= 1_000_000:
        return f"{num / 1_000_000:.1f}m"
    elif num >= 1_000:
        return f"{num / 1_000:.0f}k"
    else:
        return str(num)


def get_tm_names():
    with open('countries.json') as f:
        countries = json.load(f)
        return dict((i['transfermarkt_name'], i['code']) for i in countries)
    

@click.group
def cli():
    pass


@click.command
def get_country_stats():
    with open('countries.json') as f:
        countries = json.load(f)

    countries = [i for i in countries if i['competitions']]
    mvs = {}
    for country in countries:
        players = Player().from_country(country_code=country['code'])
        players = [i for i in players if i.get('market_value_number')]
        mv = [i['market_value_number'] for i in players]
        mvs[country['name']] = sum(mv)

    mvs = sorted(mvs.items(), key=lambda k: -k[-1])
    mvs = [(k, v) for k, v in mvs if v > 0]

    print(*[f'{k}: {abbreviate_number(v)}' for k, v in mvs], sep='\n')
    stats_table = PrettyTable()
    stats_table.field_names = ['Mean', 'H Mean']
    mv_mean = statistics.mean([v for k, v in mvs])
    mv_hmean = statistics.harmonic_mean([v for k, v in mvs])
    stats_table.add_row([abbreviate_number(mv_mean), abbreviate_number(mv_hmean)])
    print(stats_table)


@click.command
@click.option('--partition', '-p', default='position')
@click.option('--stats', '-s', default=True)
@click.option('--prefs', default=DEFAULT_PREFS)
@click.argument('country')
def get_players(country, prefs, stats):
    with open(prefs) as f:
        prefs = json.load(f)

    players = Player().from_country(country_name=country)
    players = sorted(players, key=lambda d: -d.get('market_value_number', 0))
    if max_age := prefs.get('max_age'):
        max_age = int(max_age)
        players = [i for i in players if i.get('age', 0) <= max_age]

    if positions := prefs.get('positions'):
        positions = positions.split(',')
        players = [i for i in players if i['position'] in itemgetter(*positions)(codes.positions)]

    if limit := prefs.get('limit'):
        limit = int(limit)
        players = players[0:limit]

    table = PrettyTable()
    table.field_names = list(default_keys.values())
    for i in players:
        row = []
        for k in default_keys.keys():
            row.append(i.get(k))
        table.add_row(row)

    for i in table.field_names:
        table.align[i] = 'l'

    print(table)

    if stats:
        mvs = [i.get('market_value_number', 0) for i in players]
        max_mv = abbreviate_number(max(mvs))
        min_mv = abbreviate_number(min(mvs))
        mean = abbreviate_number(statistics.mean(mvs))
        hmean = abbreviate_number(statistics.harmonic_mean(mvs))
        stats_table = PrettyTable()
        stats_table.field_names = ['Count', 'Max MV', 'Min MV', 'Mean', 'HMean']
        stats_table.add_row([len(players), f'€{max_mv}', f'€{min_mv}', f'€{mean}', f'€{hmean}'])
        print(stats_table)

def get_stats_table(players):
    mvs = [j for j in [i.get('market_value_number', 0) for i in players] if j > 0]
    max_mv = abbreviate_number(max(mvs))
    min_mv = abbreviate_number(min(mvs))
    mean = abbreviate_number(statistics.mean(mvs))
    hmean = abbreviate_number(statistics.harmonic_mean(mvs))
    stats_table = PrettyTable()
    stats_table.field_names = ['Count', 'Max MV', 'Min MV', 'Mean', 'HMean']
    stats_table.add_row([len(players), f'€{max_mv}', f'€{min_mv}', f'€{mean}', f'€{hmean}'])
    return stats_table

@click.command
@click.option('--prefs', '-p', default=DEFAULT_PREFS)
@click.option('--size', '-s', default=50)
@click.argument('country')
def sample_position(country, size, prefs):
    with open(prefs) as f:
        prefs = json.load(f)

    players = Player().from_country(country_name=country)
    players = sorted(players, key=lambda d: -d.get('market_value_number', 0))
    if max_age := prefs.get('max_age'):
        players = [i for i in players if i.get('age', 0) <= max_age]
    position_list = ['CB', 'LB', 'RB', 'DM', 'CM', 'AM', 'LW', 'RW', 'CF']
    for p_code in position_list:
        p = codes.positions[p_code]
        print(p)
        players_sample = [i for i in players if i['position'] == p]
        players_sample = players_sample[0:size]

        table = PrettyTable()
        table.field_names = list(default_keys.keys())
        for player in players_sample:
            table.add_row([player.get(f, '-') for f in table.field_names])
        
        for i in table.field_names:
            table.align[i] = 'l'
        print(table)

        stats_table = get_stats_table(players_sample)
        print(stats_table)


@click.command
@click.option('--max-age', '-ma')
@click.option('--limit', '-l')
@click.option('--country', '-c')
def get_foreigners(country, limit, max_age):
    players = Player().from_country(country_name=country)
    players = sorted(players, key=lambda d: -d.get('market_value_number', 0))
    if max_age:
        max_age = int(max_age)
        players = [i for i in players if i.get('age', 0) <= max_age]

    if limit:
        limit = int(limit)
        players = players[0:limit]
    
    foreigners = [i for i in players if i['nationality1'] != country and i.get('nationality2', '') != country]

    table = PrettyTable()
    table.field_names = list(default_keys.values())
    for i in foreigners:
        row = []
        for k in default_keys.keys():
            row.append(i.get(k))
        table.add_row(row)

    print(table)
    print(len(foreigners))


@click.command
@click.option('--prefs-file')
def partition_table(prefs_file):
    if not prefs_file:
        prefs_file = DEFAULT_PREFS
    
    prefs = {}
    with open(prefs_file) as f:
        prefs = json.load(f)

    print(prefs)

cli.add_command(get_country_stats)
cli.add_command(get_players)
cli.add_command(get_foreigners)
cli.add_command(partition_table)
cli.add_command(sample_position)

if __name__ == '__main__':
    cli()
