if __name__ == '__main__':
    from transfermarkt import *

    # Read countries file
    countries = None
    with open('countries.json') as f:
        countries = json.load(f)

    # organize ids by tiers (Y = youth)
    competition_info = []
    for country in countries:
        for n, c in enumerate(country['competitions'], start=1):
            if isinstance(c, list):
                competition_info.extend([(str(n), i) for i in c])
            else:
                competition_info.append((str(n), c))
            
        for c in country['youth_competitions']:
            competition_info.append(('Y', c))

    competition_info = sorted(competition_info, key=lambda c: c[0])
    ids = [i[-1] for i in competition_info]
    saved = [i['id'] for i in get_competitions(ids)]

    status_table = dict((i, i in saved) for i in ids)
    pending = [i for i, s in status_table.items() if not s]

    # backfill competitions
    while len(pending) != 0:
        for i in ids:
            try:
                if not status_table[i]:
                    print(f'Fetching competition {i}')
                    save_competition(i)
                    pause = random.random() * 10
                    time.sleep(pause)
                    status_table[i] = True
            except requests.exceptions.HTTPError as e:
                status_code = int(e.response.status_code)
                if status_code == 504:
                    print('Server timeout. Pausing.')
                    time.sleep(20)
                    break

        pending = [i for i, s in status_table.items() if not s]

    all_competitions = get_competitions(ids)
    club_ids = list(chain(*[[j['id'] for j in i['clubs']] for i in all_competitions]))
    saved_clubs = get_clubs(club_ids)
    saved_club_ids = [i['id'] for i in saved_clubs]
    club_status_table = dict((i, i in saved_club_ids) for i in club_ids)
    unsaved_clubs = [k for k, j in club_status_table.items() if not j]

    while len(unsaved_clubs) != 0:
        for comp in all_competitions:
            clubs = comp['clubs']
            season = comp['seasonID']
            for club in clubs:
                club_id = club['id']
                club_name = club['name']
                try:
                    if not club_status_table[club_id]:
                        print(f'Fetching club {club_id} ({club_name})')
                        save_club(club_id, season)
                        club_status_table[club_id] = True
                        time.sleep(random.random() + 1)
                except requests.exceptions.HTTPError as e:
                    status_code = int(e.response.status_code)
                    if status_code == 504:
                        print('Server timeout. Pausing.')
                        time.sleep((random.random() * 30) + 30)
                        break

                    if status_code == 500:
                        print('Possible rate limit. Sleeping for 15 minutes.')
                        time.sleep(15 * 60)
                        break

            unsaved_clubs = [k for k, j in club_status_table.items() if not j]
