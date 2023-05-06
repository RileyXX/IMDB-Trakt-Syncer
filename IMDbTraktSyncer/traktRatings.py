import os
import json
import subprocess
import requests

def getTraktRatings(trakt_client_id, trakt_access_token):
    #Get Trakt Ratings
    print('Getting Trakt Ratings')

    headers = {
        'Content-Type': 'application/json',
        'trakt-api-version': '2',
        'trakt-api-key': trakt_client_id,
        'Authorization': f'Bearer {trakt_access_token}'
    }

    response = requests.get('https://api.trakt.tv/users/me', headers=headers)
    json_data = json.loads(response.text)
    username = json_data['username']
    response = requests.get(f'https://api.trakt.tv/users/{username}/ratings', headers=headers)
    json_data = json.loads(response.text)

    movie_ratings = []
    show_ratings = []

    for item in json_data:
        if item['type'] == 'movie':
            movie = item['movie']
            movie_id = movie['ids']['imdb']
            movie_ratings.append({'Title': movie['title'], 'Year': movie['year'], 'Rating': item['rating'], 'ID': movie_id, 'Type': 'movie'})
        elif item['type'] == 'show':
            show = item['show']
            show_id = show['ids']['imdb']
            show_ratings.append({'Title': show['title'], 'Year': show['year'], 'Rating': item['rating'], 'ID': show_id, 'Type': 'show'})

    trakt_ratings = movie_ratings + show_ratings

    print('Getting Trakt Ratings Complete')
    
    return trakt_ratings