import json
import urllib.parse
import datetime
import sys
import os
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from IMDBTraktSyncer import errorHandling as EH
from IMDBTraktSyncer import errorLogger as EL

def remove_slashes(string):
    string = string.replace('/', '') if string is not None else None
    return string

def get_trakt_encoded_username():
    # Process Trakt Ratings and Comments
    response = EH.make_trakt_request('https://api.trakt.tv/users/me')
    json_data = json.loads(response.text)
    username_slug = json_data['ids']['slug']
    encoded_username = urllib.parse.quote(username_slug)
    return encoded_username
    
def get_trakt_watchlist(encoded_username):
    # Get all pages of Trakt Watchlist Items
    url = f'https://api.trakt.tv/users/{encoded_username}/watchlist?sort=added,asc'
    response = EH.make_trakt_request(url, params={'page': 1, 'limit': 100})
    json_data = json.loads(response.text)
    total_pages = int(response.headers.get('X-Pagination-Page-Count', 1))

    trakt_watchlist = []

    for page in range(1, total_pages + 1):
        if page > 1:
            response = EH.make_trakt_request(url, params={'page': page, 'limit': 100})
            json_data = json.loads(response.text)

        for item in json_data:
            if item['type'] == 'movie':
                movie = item.get('movie')
                imdb_movie_id = movie.get('ids', {}).get('imdb')
                imdb_movie_id = remove_slashes(imdb_movie_id)
                trakt_movie_id = movie.get('ids', {}).get('trakt')
                trakt_watchlist.append({'Title': movie.get('title'), 'Year': movie.get('year'), 'IMDB_ID': imdb_movie_id, 'TraktID': trakt_movie_id, 'Date_Added': item.get('listed_at'), 'Type': 'movie'})
            elif item['type'] == 'show':
                show = item.get('show')
                imdb_show_id = show.get('ids', {}).get('imdb')
                imdb_show_id = remove_slashes(imdb_show_id)
                trakt_show_id = show.get('ids', {}).get('trakt')
                trakt_watchlist.append({'Title': show.get('title'), 'Year': show.get('year'), 'IMDB_ID': imdb_show_id, 'TraktID': trakt_show_id, 'Date_Added': item.get('listed_at'), 'Type': 'show'})
            elif item['type'] == 'episode':
                show = item.get('show')
                show_title = show.get('title')
                episode = item.get('episode')
                imdb_episode_id = episode.get('ids', {}).get('imdb')
                imdb_episode_id = remove_slashes(imdb_episode_id)
                trakt_episode_id = episode.get('ids', {}).get('trakt')
                episode_title = f'{show_title}: {episode.get("title")}'
                trakt_watchlist.append({'Title': episode_title, 'Year': episode.get('year'), 'IMDB_ID': imdb_episode_id, 'TraktID': trakt_episode_id, 'Date_Added': item.get('listed_at'), 'Type': 'episode'})
    
    return trakt_watchlist

def get_trakt_ratings(encoded_username):  
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
            movie_id = remove_slashes(movie_id)
            movie_ratings.append({'Title': movie.get('title'), 'Year': movie.get('year'), 'Rating': item.get('rating'), 'IMDB_ID': movie_id, 'Date_Added': item.get('rated_at'), 'WatchedAt': item.get('rated_at'), 'Type': 'movie'})
        elif item['type'] == 'show':
            show = item.get('show')
            show_id = show.get('ids', {}).get('imdb')
            show_id = remove_slashes(show_id)
            show_ratings.append({'Title': show.get('title'), 'Year': show.get('year'), 'Rating': item.get('rating'), 'IMDB_ID': show_id, 'Date_Added': item.get('rated_at'), 'WatchedAt': item.get('rated_at'), 'Type': 'show'})
        elif item['type'] == 'episode':
            show = item.get('show')
            show_title = show.get('title')
            episode = item.get('episode')
            episode_id = episode.get('ids', {}).get('imdb')
            episode_id = remove_slashes(episode_id)
            episode_title = f'{show_title}: {episode.get("title")}'
            episode_ratings.append({'Title': episode_title, 'Year': episode.get('year'), 'Rating': item.get('rating'), 'IMDB_ID': episode_id, 'Date_Added': item.get('rated_at'), 'WatchedAt': item.get('rated_at'), 'Type': 'episode'})

    trakt_ratings = movie_ratings + show_ratings + episode_ratings
    
    return trakt_ratings

def get_trakt_comments(encoded_username):  
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
                show_movie_or_episode_imdb_id = remove_slashes(show_movie_or_episode_imdb_id)
            elif comment_type == 'episode':
                show = comment.get('show')
                episode = comment.get('episode')
                show_movie_or_episode_title = f"{show.get('title')}: {episode.get('title')}"
                show_movie_or_episode_year = show.get('year')
                show_movie_or_episode_imdb_id = episode.get('ids', {}).get('imdb')
                show_movie_or_episode_imdb_id = remove_slashes(show_movie_or_episode_imdb_id)
            elif comment_type == 'show':
                show = comment.get('show')
                show_movie_or_episode_title = show.get('title')
                show_movie_or_episode_year = show.get('year')
                show_movie_or_episode_imdb_id = show.get('ids', {}).get('imdb')
                show_movie_or_episode_imdb_id = remove_slashes(show_movie_or_episode_imdb_id)
            elif comment_type == 'season':
                show = comment.get('show')
                season = comment.get('season')
                show_movie_or_episode_title = f"{show.get('title')}: Season {season.get('number')}"
                show_movie_or_episode_year = None
                show_movie_or_episode_imdb_id = None
            else:
                # Generic fallback for unknown types
                # Find the first dict that has title/year/ids
                for key, value in comment.items():
                    if isinstance(value, dict) and "title" in value:
                        show_movie_or_episode_title = value.get("title")
                        show_movie_or_episode_year = value.get("year")
                        show_movie_or_episode_imdb_id = remove_slashes(value.get("ids", {}).get("imdb"))
                        break

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
    
    return trakt_comments
    
def get_trakt_watch_history(encoded_username):  
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
                imdb_movie_id = remove_slashes(imdb_movie_id)
                trakt_movie_id = movie.get('ids', {}).get('trakt')
                if trakt_movie_id and trakt_movie_id not in seen_ids:
                    watched_movies.append({'Title': movie.get('title'), 'Year': movie.get('year'), 'IMDB_ID': imdb_movie_id, 'TraktID': trakt_movie_id, 'Date_Added': item.get('watched_at'), 'WatchedAt': item.get('watched_at'), 'Type': 'movie'})
                    seen_ids.add(trakt_movie_id)
            elif item['type'] == 'episode':
                show = item.get('show')
                imdb_show_id = show.get('ids', {}).get('imdb')
                imdb_show_id = remove_slashes(imdb_show_id)
                trakt_show_id = show.get('ids', {}).get('trakt')
                show_status = show.get('status')
                aired_episodes = show.get('aired_episodes')
                
                if trakt_show_id and trakt_show_id not in seen_ids:
                    watched_shows.append({'Title': show.get('title'), 'Year': show.get('year'), 'IMDB_ID': imdb_show_id, 'TraktID': trakt_show_id, 'Date_Added': item.get('watched_at'), 'WatchedAt': item.get('watched_at'), 'ShowStatus': show_status, 'AiredEpisodes': aired_episodes, 'Type': 'show'})
                    seen_ids.add(trakt_show_id)

                show_title = show.get('title')
                episode = item.get('episode')
                season_number = episode.get('season')
                episode_number = episode.get('number')
                imdb_episode_id = episode.get('ids', {}).get('imdb')
                imdb_episode_id = remove_slashes(imdb_episode_id)
                trakt_episode_id = episode.get('ids', {}).get('trakt')
                episode_title = f'{show_title}: {episode.get("title")}'
                episode_year = datetime.datetime.strptime(episode.get('first_aired'), "%Y-%m-%dT%H:%M:%S.%fZ").year if episode.get('first_aired') else None
                watched_at = item.get('watched_at')
                if trakt_episode_id and trakt_episode_id not in seen_ids:
                    watched_episodes.append({'Title': episode_title, 'Year': episode_year, 'IMDB_ID': imdb_episode_id, 'TraktID': trakt_episode_id, 'TraktShowID': trakt_show_id, 'SeasonNumber': season_number, 'EpisodeNumber': episode_number, 'Date_Added': watched_at, 'WatchedAt': watched_at, 'Type': 'episode'})
                    seen_ids.add(trakt_episode_id)

    # Filter watched_shows for completed shows where 80% or more of the show has been watched AND where the show's status is "ended" or "cancelled"
    filtered_watched_shows = []
    for show in watched_shows:
        trakt_show_id = show['TraktID']
        show_status = show['ShowStatus']
        aired_episodes = show['AiredEpisodes']
        episode_numbers = [episode['EpisodeNumber'] for episode in watched_episodes if episode['Type'] == 'episode' and episode['TraktShowID'] == trakt_show_id]
        unique_watched_episode_count = len(episode_numbers)
        
        if (show_status.lower() in ['ended', 'cancelled', 'canceled']) and (unique_watched_episode_count >= 0.8 * int(aired_episodes)):
            filtered_watched_shows.append(show)

    # Update watched_shows with the filtered results
    watched_shows = filtered_watched_shows

    trakt_watch_history = watched_movies + watched_shows + watched_episodes
    
    return trakt_watch_history

TRAKT_CACHE_SCHEMA_VERSION = 1

def _empty_trakt_cache(username):
    return {
        "schema_version": TRAKT_CACHE_SCHEMA_VERSION,
        "username": username,
        "datasets": {}
    }

def _load_trakt_cache(cache_file, username):
    if not os.path.exists(cache_file):
        return _empty_trakt_cache(username)

    try:
        with open(cache_file, "r", encoding="utf-8") as file:
            cache = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            f"Could not read Trakt cache '{cache_file}'. Use --update-trakt-cache to rebuild it."
        ) from exc

    if (
        not isinstance(cache, dict)
        or cache.get("schema_version") != TRAKT_CACHE_SCHEMA_VERSION
        or not isinstance(cache.get("datasets"), dict)
    ):
        raise ValueError(
            f"Trakt cache '{cache_file}' has an unsupported format. "
            "Use --update-trakt-cache to rebuild it."
        )

    if cache.get("username") != username:
        print("Trakt account changed; creating a separate cache for the current account.")
        return _empty_trakt_cache(username)

    return cache

def _save_trakt_cache(cache_file, cache):
    cache_directory = os.path.dirname(os.path.abspath(cache_file))
    temporary_file = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=cache_directory,
            prefix=".trakt-cache-",
            suffix=".tmp",
            delete=False
        ) as file:
            json.dump(cache, file, ensure_ascii=False, indent=2)
            file.write("\n")
            temporary_file = file.name

        if os.name != "nt":
            os.chmod(temporary_file, 0o600)
        os.replace(temporary_file, cache_file)
        temporary_file = None
    except OSError as exc:
        raise RuntimeError(f"Could not write Trakt cache '{cache_file}'.") from exc
    finally:
        if temporary_file and os.path.exists(temporary_file):
            os.remove(temporary_file)

def get_cached_trakt_data(encoded_username, cache_file, enabled_datasets, update_cache=False):
    username = urllib.parse.unquote(encoded_username)
    fetchers = {
        "watchlist": get_trakt_watchlist,
        "ratings": get_trakt_ratings,
        "comments": get_trakt_comments,
        "watch_history": get_trakt_watch_history
    }

    for dataset_name in enabled_datasets:
        if dataset_name not in fetchers:
            raise ValueError(f"Unknown Trakt dataset requested: {dataset_name}")

    cache = _empty_trakt_cache(username) if update_cache else _load_trakt_cache(cache_file, username)
    results = {dataset_name: [] for dataset_name in fetchers}
    cache_updated = False

    for dataset_name, enabled in enabled_datasets.items():
        if not enabled:
            continue

        cache_entry = cache["datasets"].get(dataset_name)
        if cache_entry is not None and not update_cache:
            if not isinstance(cache_entry, dict) or not isinstance(cache_entry.get("items"), list):
                raise ValueError(
                    f"Trakt cache dataset '{dataset_name}' is invalid. "
                    "Use --update-trakt-cache to rebuild it."
                )
            print(f"Using cached Trakt {dataset_name} ({len(cache_entry['items'])} items).")
        else:
            action = "Refreshing" if update_cache else "Fetching"
            print(f"{action} Trakt {dataset_name}...")
            items = fetchers[dataset_name](encoded_username)
            if not isinstance(items, list):
                raise TypeError(f"Trakt returned invalid {dataset_name} data; expected a list.")
            cache_entry = {
                "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "items": items
            }
            cache["datasets"][dataset_name] = cache_entry
            cache_updated = True

        results[dataset_name] = cache_entry["items"]

    if cache_updated:
        _save_trakt_cache(cache_file, cache)
        print(f"Updated Trakt cache: {cache_file}")

    return results