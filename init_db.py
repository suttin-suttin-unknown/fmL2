from transfermarkt import API, Club, Competition
import random
import time
import requests

def save_countries(countries):
    for country in countries:
        competitions = Competition().from_country(country)
        for competition in competitions:
            season = competition['seasonID']
            clubs = competition.get('clubs', [])
            names = dict(i.values() for i in clubs)
            ids = list(names.keys())
            unsaved = Club().find(*ids)
            unsaved = [i['id'] for i in unsaved]
            ids = set(ids) - set(unsaved)
            if len(ids) != 0:
                api = API()
                for id in ids:
                    try:
                        response = api.get_club_players(id, season)
                        Club().save(response)
                        print(f'Saving for {id} ({names[id]})')
                        time.sleep(random.random() + 1)
                    except requests.exceptions.HTTPError as err:
                        status = int(err.response.status_code)
                        if status == 404:
                            print(f'Skipping for {id}')
                            continue


if __name__ == '__main__':
    countries = [
        'England',
        'Spain',
        'Italy',
        'Germany',
        'France',
        'Brazil',
        'Portugal',
        'Netherlands',
        'Turkey',
        'United States',
        'Russia',
        'Belgium',
        'Mexico',
        'Argentina',
        'Greece',
        'Austria',
        'Japan',
        'Switzerland',
        'Scotland',
        'Denmark',
        'Poland',
        'Ukraine',
        'Serbia',
        'Czech Republic',
        'Colombia',
        'Norway',
        'Sweden',
        'Croatia',
        'Romania',
        'Chile',
        'Korea Republic',
        'Bulgaria',
        'Peru',
        'Hungary',
        'Uruguay',
        'Israel',
        'South Africa',
        'Cyprus',
        'Egypt',
        'Islamic Republic of Iran',
        'China',
        'Ecuador',
        'Bolivia',
        'Morocco',
        'Paraguay',
        'Indonesia',
        'Slovakia',
        'Thailand',
        'Australia',
        'Tunisia',
        'Bosnia-Herzegovina',
        'Venezuela',
        'Uzbekistan',
        'Algeria',
        'Slovenia',
        'India',
        'Azerbaijan',
        'Kazakhstan',
        'New Zealand',
        'Belarus',
        'Albania',
        'Malaysia',
        'Latvia',
        'Costa Rica',
        'Malta',
        'Armenia',
        'North Macedonia',
        'Georgia',
        'Vietnam',
        'Lithuania',
        'Finland',
        'Moldova',
        'Iceland',
        'Guatemala',
        'Kosovo',
        'Hong Kong, China',
        'Northern Ireland',
        'Honduras',
        'Ghana',
        'Panama',
        'El Salvador',
        'Luxembourg',
        'Andorra',
        'Republic Of Ireland',
        'Montenegro',
        'Tajikistan',
        'Bangladesh',
        'Kyrgyz Republic',
        'Estonia',
        'Canada',
        'Oman',
        'Fiji',
        'Wales',
        'Cambodia',
        'Gibraltar',
        'Faroe Islands',
        'San Marino',
        'Philippines',
        'Chinese Taipei',
        'Laos',
        'Angola',
        'Myanmar',
        'Nicaragua',
        'Nigeria',
        'Jamaica',
        'Mozambique'
    ]
    save_countries(countries)
    
                    

                





    
    