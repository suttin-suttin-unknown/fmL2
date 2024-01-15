import transfermarkt

import json
from collections import defaultdict

from prettytable import PrettyTable
import click


def get_tm_names():
    with open('countries.json') as f:
        countries = json.load(f)
        return dict((i['transfermarkt_name'], i['code']) for i in countries)


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


def get_player_table(rows):
    all_keys = list(default_keys.keys())
    table = PrettyTable()
    field_names = [default_keys[i] for i in all_keys]
    table.field_names = field_names

    table.add_rows(rows)

    for i in field_names:
        table.align[i] = 'l'

    return table

def display_table(results, sort_by=None, group_by=None, **preferences):
    if sort_by:
        results = sorted(results, key=lambda d: d[sort_by])

    #rows = [dict((k, i.get(k)) for k in default_keys) for i in results]
    rows = [dict((k, v) for k, v in i.items()) for i in results]
    if group_by:
        groups = {i[group_by] for i in results}
        grouped = defaultdict(list)
        for i in groups:
            grouped[i] = [j for j in results if j[group_by] == i]

        for i in grouped:
            ig = [[j.get(k) for k in default_keys] for j in grouped[i]]
            yield get_player_table(ig)
    else:
        yield get_player_table(rows)


@click.group
def cli():
    pass


@click.command()
@click.option('--age-range', '-ar')
@click.option('--mv-range', '-mr')
@click.option('--positions', '-p')
@click.option('--limit', '-l')
@click.option('--group-by', '-g')
def list_search(age_range, mv_range, positions, limit, group_by):
    prefs = {}
    if age_range:
        age_min, age_max = age_range.split(',')
        if age_min:
            prefs['age_min'] = int(age_min)

        if age_max:
            prefs['age_max'] = int(age_max)

    if mv_range:
        mv_min, mv_max = mv_range.split(',')
        if mv_min:
            prefs['mv_min'] = int(mv_min)

        if mv_max:
            prefs['mv_max'] = int(mv_max)
        

    if positions:
        positions = positions.split(',')
        prefs['positions'] = positions

    results = transfermarkt.search_players(limit=int(limit), **prefs)
    if group_by:
        table = display_table(results, group_by=group_by)
    else:
        table = display_table(results)

    click.echo(next(table))

    for st in table:
        inp = input()
        if inp.lower() == 'quit':
            break
        click.echo(st)


@click.command
@click.option('--name', '-n')
def search_by_name(name):
    table = None
    if name:
        table = display_table(transfermarkt.search_by_name(name))

    if table:
        click.echo(next(table))


cli.add_command(list_search)
cli.add_command(search_by_name)


if __name__ == '__main__':
    cli()
