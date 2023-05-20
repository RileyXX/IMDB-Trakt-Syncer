import json
import requests
import time
try:
    from IMDBTraktSyncer import errorHandling
except:
    import errorHandling

def getTraktData():
    # Process Trakt Ratings and Comments
    print('Processing Trakt Ratings and Comments')

    response = errorHandling.make_trakt_request('https://api.trakt.tv/users/me')
    json_data = json.loads(response.text)
    username = json_data['username']

    # Get Trakt Ratings
    response = errorHandling.make_trakt_request(f'https://api.trakt.tv/users/{username}/ratings')
    json_data = json.loads(response.text)

    movie_ratings = []
    show_ratings = []
    episode_ratings = []

    for item in json_data:
        if item['type'] == 'movie':
            movie = item['movie']
            movie_id = movie['ids']['imdb']
            movie_ratings.append({'Title': movie['title'], 'Year': movie['year'], 'Rating': item['rating'], 'ID': movie_id, 'Type': 'movie'})
        elif item['type'] == 'show':
            show = item['show']
            show_id = show['ids']['imdb']
            show_ratings.append({'Title': show['title'], 'Year': show['year'], 'Rating': item['rating'], 'ID': show_id, 'Type': 'show'})
        elif item['type'] == 'episode':
            show = item['show']
            show_title = show['title']
            episode = item['episode']
            episode_id = episode['ids']['imdb']
            episode_title = f'{show_title}: {episode["title"]}'
            episode_ratings.append({'Title': episode_title, 'Year': episode.get('year'), 'Rating': item['rating'], 'ID': episode_id, 'Type': 'episode'})

    trakt_ratings = movie_ratings + show_ratings + episode_ratings

    # Get Trakt Comments
    response = errorHandling.make_trakt_request(f'https://api.trakt.tv/users/{username}/comments')
    json_data = json.loads(response.text)
    total_pages = response.headers.get('X-Pagination-Page-Count')
    trakt_comments = []

    for page in range(1, int(total_pages) + 1):
        response = errorHandling.make_trakt_request(f'https://api.trakt.tv/users/{username}/comments', params={'page': page})
        json_data = json.loads(response.text)

        for comment in json_data:
            comment_type = comment['type']
            spoiler = comment.get('spoiler', False)
            if comment_type == 'movie':
                show_movie_or_episode_title = comment['movie']['title']
                show_movie_or_episode_year = comment['movie'].get('year')
                show_movie_or_episode_imdb_id = comment['movie']['ids']['imdb']
            elif comment_type == 'episode':
                show_movie_or_episode_title = f"{comment['show']['title']}: {comment['episode']['title']}"
                show_movie_or_episode_year = comment['show'].get('year')
                show_movie_or_episode_imdb_id = comment['episode']['ids']['imdb']
            elif comment_type == 'show':
                show_movie_or_episode_title = comment['show']['title']
                show_movie_or_episode_year = comment['show'].get('year')
                show_movie_or_episode_imdb_id = comment['show']['ids']['imdb']
            elif comment_type == 'season':
                show_movie_or_episode_title = f"{comment['show']['title']}: Season {comment['season']['number']}"
                show_movie_or_episode_year = None
                show_movie_or_episode_imdb_id = None
            else:
                show_movie_or_episode_title = None
                show_movie_or_episode_year = None
                show_movie_or_episode_imdb_id = None

            comment_info = comment['comment']
            trakt_comment_id = comment_info.get('id')
            trakt_comment = comment_info.get('comment')

            trakt_comments.append({
                'Title': show_movie_or_episode_title,
                'Year': show_movie_or_episode_year,
                'ID': show_movie_or_episode_imdb_id,
                'TraktCommentID': trakt_comment_id,
                'Comment': trakt_comment,
                'Spoiler': spoiler,
                'Type': comment_type
            })

    print('Processing Trakt Ratings and Comments Complete')

    return trakt_ratings, trakt_comments