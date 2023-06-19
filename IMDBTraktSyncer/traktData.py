import json
import requests
import time
import urllib.parse
import datetime
try:
    from IMDBTraktSyncer import errorHandling as EH
    from IMDBTraktSyncer import errorLogger as EL
except ImportError:
    import errorHandling as EH
    import errorLogger as EL

def getTraktData():
    # Process Trakt Ratings and Comments
    print('Processing Trakt Data')

    response = EH.make_trakt_request('https://api.trakt.tv/users/me')
    json_data = json.loads(response.text)
    username_slug = json_data['ids']['slug']
    encoded_username = urllib.parse.quote(username_slug)
    
    # Get Trakt Watchlist Items
    response = EH.make_trakt_request(f'https://api.trakt.tv/users/{encoded_username}/watchlist?sort=added,asc')
    json_data = json.loads(response.text)

    trakt_watchlist = []

    for item in json_data:
        if item['type'] == 'movie':
            movie = item.get('movie')
            imdb_movie_id = movie.get('ids', {}).get('imdb')
            trakt_movie_id = movie.get('ids', {}).get('trakt')
            trakt_watchlist.append({'Title': movie.get('title'), 'Year': movie.get('year'), 'IMDB_ID': imdb_movie_id, 'TraktID': trakt_movie_id, 'Type': 'movie'})
        elif item['type'] == 'show':
            show = item.get('show')
            imdb_show_id = show.get('ids', {}).get('imdb')
            trakt_show_id = show.get('ids', {}).get('trakt')
            trakt_watchlist.append({'Title': show.get('title'), 'Year': show.get('year'), 'IMDB_ID': imdb_show_id, 'TraktID': trakt_show_id, 'Type': 'show'})
        elif item['type'] == 'episode':
            show = item.get('show')
            show_title = show.get('title')
            episode = item.get('episode')
            imdb_episode_id = episode.get('ids', {}).get('imdb')
            trakt_episode_id = episode.get('ids', {}).get('trakt')
            episode_title = f'{show_title}: {episode.get("title")}'
            trakt_watchlist.append({'Title': episode_title, 'Year': episode.get('year'), 'IMDB_ID': imdb_episode_id, 'TraktID': trakt_episode_id, 'Type': 'episode'})
    
    # Get Trakt Ratings
    response = EH.make_trakt_request(f'https://api.trakt.tv/users/{encoded_username}/ratings?sort=newest')
    json_data = json.loads(response.text)

    movie_ratings = []
    show_ratings = []
    episode_ratings = []

    for item in json_data:
        if item['type'] == 'movie':
            movie = item.get('movie')
            movie_id = movie.get('ids', {}).get('imdb')
            movie_ratings.append({'Title': movie.get('title'), 'Year': movie.get('year'), 'Rating': item.get('rating'), 'IMDB_ID': movie_id, 'Type': 'movie'})
        elif item['type'] == 'show':
            show = item.get('show')
            show_id = show.get('ids', {}).get('imdb')
            show_ratings.append({'Title': show.get('title'), 'Year': show.get('year'), 'Rating': item.get('rating'), 'IMDB_ID': show_id, 'Type': 'show'})
        elif item['type'] == 'episode':
            show = item.get('show')
            show_title = show.get('title')
            episode = item.get('episode')
            episode_id = episode.get('ids', {}).get('imdb')
            episode_title = f'{show_title}: {episode.get("title")}'
            episode_ratings.append({'Title': episode_title, 'Year': episode.get('year'), 'Rating': item.get('rating'), 'IMDB_ID': episode_id, 'Type': 'episode'})

    trakt_ratings = movie_ratings + show_ratings + episode_ratings

    # Get Trakt Comments
    response = EH.make_trakt_request(f'https://api.trakt.tv/users/{encoded_username}/comments?sort=newest')
    json_data = json.loads(response.text)
    total_pages = response.headers.get('X-Pagination-Page-Count')
    trakt_comments = []

    for page in range(1, int(total_pages) + 1):
        response = EH.make_trakt_request(f'https://api.trakt.tv/users/{encoded_username}/comments', params={'page': page})
        json_data = json.loads(response.text)

        for comment in json_data:
            comment_type = comment['type']
            spoiler = comment.get('spoiler', False)

            if comment_type == 'movie':
                movie = comment.get('movie')
                show_movie_or_episode_title = movie.get('title')
                show_movie_or_episode_year = movie.get('year')
                show_movie_or_episode_imdb_id = movie.get('ids', {}).get('imdb')
            elif comment_type == 'episode':
                show = comment.get('show')
                episode = comment.get('episode')
                show_movie_or_episode_title = f"{show.get('title')}: {episode.get('title')}"
                show_movie_or_episode_year = show.get('year')
                show_movie_or_episode_imdb_id = episode.get('ids', {}).get('imdb')
            elif comment_type == 'show':
                show = comment.get('show')
                show_movie_or_episode_title = show.get('title')
                show_movie_or_episode_year = show.get('year')
                show_movie_or_episode_imdb_id = show.get('ids', {}).get('imdb')
            elif comment_type == 'season':
                show = comment.get('show')
                season = comment.get('season')
                show_movie_or_episode_title = f"{show.get('title')}: Season {season.get('number')}"
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
                'IMDB_ID': show_movie_or_episode_imdb_id,
                'TraktCommentID': trakt_comment_id,
                'Comment': trakt_comment,
                'Spoiler': spoiler,
                'Type': comment_type
            })

    # Filter out duplicate comments for the same item based on ID
    filtered_comments = []
    seen = set()
    for item in trakt_comments:
        if item['IMDB_ID'] not in seen:
            seen.add(item['IMDB_ID'])
            filtered_comments.append(item)
    trakt_comments = filtered_comments
            
    # Get Trakt Watch History
    response = EH.make_trakt_request(f'https://api.trakt.tv/users/{encoded_username}/history?limit=100')
    json_data = json.loads(response.text)
    total_pages = response.headers.get('X-Pagination-Page-Count')

    watched_movies = []
    watched_shows = []
    watched_episodes = []
    seen_ids = set()

    for page in range(1, int(total_pages) + 1):
        response = EH.make_trakt_request(f'https://api.trakt.tv/users/{encoded_username}/history?extended=full', params={'page': page, 'limit': 100})
        json_data = json.loads(response.text)

        for item in json_data:
            if item['type'] == 'movie':
                movie = item.get('movie')
                imdb_movie_id = movie.get('ids', {}).get('imdb')
                trakt_movie_id = movie.get('ids', {}).get('trakt')
                if trakt_movie_id and trakt_movie_id not in seen_ids:
                    watched_movies.append({'Title': movie.get('title'), 'Year': movie.get('year'), 'IMDB_ID': imdb_movie_id, 'TraktID': trakt_movie_id, 'Type': 'movie'})
                    seen_ids.add(trakt_movie_id)
            elif item['type'] == 'episode':
                show = item.get('show')
                imdb_show_id = show.get('ids', {}).get('imdb')
                trakt_show_id = show.get('ids', {}).get('trakt')
                show_status = show.get('status')
                aired_episodes = show.get('aired_episodes')
                
                if trakt_show_id and trakt_show_id not in seen_ids:
                    watched_shows.append({'Title': show.get('title'), 'Year': show.get('year'), 'IMDB_ID': imdb_show_id, 'TraktID': trakt_show_id, 'ShowStatus': show_status, 'AiredEpisodes': aired_episodes, 'Type': 'show'})
                    seen_ids.add(trakt_show_id)

                show_title = show.get('title')
                episode = item.get('episode')
                season_number = episode.get('season')
                episode_number = episode.get('number')
                imdb_episode_id = episode.get('ids', {}).get('imdb')
                trakt_episode_id = episode.get('ids', {}).get('trakt')
                episode_title = f'{show_title}: {episode.get("title")}'
                episode_year = datetime.datetime.strptime(episode.get('first_aired'), "%Y-%m-%dT%H:%M:%S.%fZ").year if episode.get('first_aired') else None
                if trakt_episode_id and trakt_episode_id not in seen_ids:
                    watched_episodes.append({'Title': episode_title, 'Year': episode_year, 'IMDB_ID': imdb_episode_id, 'TraktID': trakt_episode_id, 'TraktShowID': trakt_show_id, 'SeasonNumber': season_number, 'EpisodeNumber': episode_number, 'Type': 'episode'})
                    seen_ids.add(trakt_episode_id)

    # Filter watched_shows for completed shows where 80% or more of the show has been watched AND where the show's status is "ended" or "cancelled"
    filtered_watched_shows = []
    for show in watched_shows:
        trakt_show_id = show['TraktID']
        show_status = show['ShowStatus']
        aired_episodes = show['AiredEpisodes']
        episode_numbers = {episode['EpisodeNumber'] for episode in watched_episodes if episode['Type'] == 'episode' and episode['TraktShowID'] == trakt_show_id}
        unique_watched_episode_count = len(episode_numbers)

        if (show_status == 'ended' or show_status == 'cancelled') and unique_watched_episode_count >= 0.8 * int(aired_episodes):
            filtered_watched_shows.append(show)

    # Update watched_shows with the filtered results
    watched_shows = filtered_watched_shows

    watched_content = watched_movies + watched_shows + watched_episodes
    
    print('Processing Trakt Data Complete')

    return trakt_watchlist, trakt_ratings, trakt_comments, watched_content
