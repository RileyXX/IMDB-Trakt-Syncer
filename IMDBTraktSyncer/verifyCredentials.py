import os
import json
import sys
import datetime
from datetime import timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from IMDBTraktSyncer import authTrakt
from IMDBTraktSyncer import errorLogger as EL

def print_directory(main_directory):
    print(f"Your settings are saved at:\n{main_directory}")

def prompt_get_credentials():
    # Define the file path
    here = os.path.abspath(os.path.dirname(__file__))
    file_path = os.path.join(here, 'credentials.txt')

    # Default values for missing credentials
    default_values = {
        "trakt_client_id": "empty",
        "trakt_client_secret": "empty",
        "trakt_access_token": "empty",
        "trakt_refresh_token": "empty",
        "last_trakt_token_refresh": "empty",
        "imdb_username": "empty",
        "imdb_password": "empty"
    }

    # Load existing file data
    if os.path.isfile(file_path) and os.path.getsize(file_path) > 0:
        # Read the credentials file
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                file_data = json.load(f)
            except json.decoder.JSONDecodeError as e:
                print(f"JSON Decode Error: {e}")
                file_data = {}  # Handle invalid JSON
    else:
        file_data = {}

    # Update only the keys related to default values
    values = {key: file_data.get(key, default_value) for key, default_value in default_values.items()}
    
    # Prompt user for missing credentials, excluding tokens
    for key, value in values.items():
        if value == "empty" and key not in ["trakt_access_token", "trakt_refresh_token", "last_trakt_token_refresh"]:
            if key == "imdb_username":
                prompt_message = f"Please enter a value for {key} (email or phone number): "
            elif key == "trakt_client_id":
                print("\n")
                print("***** TRAKT API SETUP *****")
                print("Follow the instructions to setup your Trakt API application:")
                print("  1. Login to Trakt and navigate to your API apps page: https://trakt.tv/oauth/applications")
                print("  2. Create a new API application named 'IMDBTraktSyncer'.")
                print("  3. Use 'urn:ietf:wg:oauth:2.0:oob' as the Redirect URI.")
                print("\n")
                prompt_message = "Please enter your Trakt Client ID: "
            else:
                prompt_message = f"Please enter a value for {key}: "
            values[key] = input(prompt_message).strip()

    # Handle token refresh if necessary
    last_trakt_token_refresh = values.get("last_trakt_token_refresh", "empty")
    should_refresh = True
    if last_trakt_token_refresh != "empty":
        try:
            last_trakt_token_refresh_time = datetime.datetime.fromisoformat(last_trakt_token_refresh)
            if datetime.datetime.now() - last_trakt_token_refresh_time < timedelta(days=7):
                should_refresh = False
        except ValueError:
            pass  # Invalid date format, treat as refresh needed

    if should_refresh:
        trakt_access_token = None
        trakt_refresh_token = None
        client_id = values["trakt_client_id"]
        client_secret = values["trakt_client_secret"]

        if "trakt_refresh_token" in values and values["trakt_refresh_token"] != "empty":
            trakt_access_token = values["trakt_refresh_token"]
            trakt_access_token, trakt_refresh_token = authTrakt.authenticate(client_id, client_secret, trakt_access_token)
        else:
            trakt_access_token, trakt_refresh_token = authTrakt.authenticate(client_id, client_secret)

        # Update tokens and last refresh time
        values["trakt_access_token"] = trakt_access_token
        values["trakt_refresh_token"] = trakt_refresh_token
        values["last_trakt_token_refresh"] = datetime.datetime.now().isoformat()

    # Merge updated credentials back into the file data
    file_data.update(values)

    # Save updated credentials back to the file
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(file_data, f, indent=4, separators=(', ', ': '))

    # Return the credentials
    return values["trakt_client_id"], values["trakt_client_secret"], values["trakt_access_token"], values["trakt_refresh_token"], values["imdb_username"], values["imdb_password"]

def prompt_sync_ratings():
    """
    Prompts the user to enable or disable syncing of ratings and updates the credentials file accordingly.
    """
    # Define the file path
    here = os.path.abspath(os.path.dirname(__file__))
    file_path = os.path.join(here, 'credentials.txt')

    # Initialize credentials dictionary
    credentials = {}

    # Load existing credentials if the file exists
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            credentials = json.load(file)
    except FileNotFoundError:
        # Log the error if the file is missing, continue with an empty credentials dictionary
        logging.error("Credentials file not found.", exc_info=True)

    # Check if the sync_ratings value is already set and valid
    sync_ratings_value = credentials.get('sync_ratings')
    if sync_ratings_value is not None and sync_ratings_value != "empty":
        return sync_ratings_value

    # Prompt the user until a valid input is received
    while True:
        user_input = input("Do you want to sync ratings? (y/n): ").strip().lower()
        if user_input == 'y':
            sync_ratings_value = True
            break
        elif user_input == 'n':
            sync_ratings_value = False
            break
        else:
            print("Invalid input. Please enter 'y' or 'n'.")

    # Update the sync_ratings value and write back to the file
    credentials['sync_ratings'] = sync_ratings_value
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(credentials, file, indent=4, separators=(', ', ': '))
    except IOError as e:
        # Log any errors during file write operation
        logging.error("Failed to write to credentials file.", exc_info=True)

    return sync_ratings_value

def prompt_sync_watchlist():
    """
    Prompts the user to sync their watchlist if not already configured in credentials.txt.
    Reads and writes to the credentials file only when necessary.
    """
    # Define the file path
    here = os.path.abspath(os.path.dirname(__file__))
    file_path = os.path.join(here, 'credentials.txt')

    # Load credentials file if it exists
    credentials = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            credentials = json.load(file)
    except FileNotFoundError:
        logging.error("Credentials file not found. A new file will be created if needed.", exc_info=True)

    # Check existing sync_watchlist value
    sync_watchlist_value = credentials.get('sync_watchlist')
    if sync_watchlist_value not in [None, "empty"]:
        return sync_watchlist_value

    # Prompt the user for input until valid
    while True:
        user_input = input("Do you want to sync watchlists? (y/n): ").strip().lower()
        if user_input == 'y':
            sync_watchlist_value = True
            break
        elif user_input == 'n':
            sync_watchlist_value = False
            break
        else:
            print("Invalid input. Please enter 'y' or 'n'.")

    # Update and save the credentials only if the file will change
    credentials['sync_watchlist'] = sync_watchlist_value
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(credentials, file, indent=4, separators=(', ', ': '))
    except Exception as e:
        logging.error("Failed to write to credentials file.", exc_info=True)
        raise

    return sync_watchlist_value
    
def prompt_sync_watch_history():
    """
    Prompts the user to sync their watch history
    if not already configured in credentials.txt. Reads and writes to the
    credentials file only when necessary.
    """
    # Define the file path
    here = os.path.abspath(os.path.dirname(__file__))
    file_path = os.path.join(here, 'credentials.txt')

    # Load credentials file if it exists
    credentials = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            credentials = json.load(file)
    except FileNotFoundError:
        logging.error("Credentials file not found. A new file will be created if needed.", exc_info=True)

    # Check existing sync_watch_history value
    sync_watch_history_value = credentials.get('sync_watch_history')
    if sync_watch_history_value not in [None, "empty"]:
        return sync_watch_history_value

    # Prompt the user for input until valid
    while True:
        print("Trakt watch history is synced using IMDB Check-ins.")
        print("See FAQ: https://help.imdb.com/article/imdb/track-movies-tv/check-ins-faq/GG59ELYW45FMC7J3")
        user_input = input("Do you want to sync your watch history? (y/n): ").strip().lower()
        if user_input == 'y':
            sync_watch_history_value = True
            break
        elif user_input == 'n':
            sync_watch_history_value = False
            break
        else:
            print("Invalid input. Please enter 'y' or 'n'.")

    # Update and save the credentials only if the file will change
    credentials['sync_watch_history'] = sync_watch_history_value
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(credentials, file, indent=4, separators=(', ', ': '))
    except Exception as e:
        logging.error("Failed to write to credentials file.", exc_info=True)
        raise

    return sync_watch_history_value
    
def prompt_mark_rated_as_watched():
    """
    Prompts the user to mark rated movies, shows, and episodes as watched
    if not already configured in credentials.txt. Reads and writes to the
    credentials file only when necessary.
    """
    # Define the file path
    here = os.path.abspath(os.path.dirname(__file__))
    file_path = os.path.join(here, 'credentials.txt')

    # Load credentials file if it exists
    credentials = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            credentials = json.load(file)
    except FileNotFoundError:
        logging.error("Credentials file not found. A new file will be created if needed.", exc_info=True)

    # Check existing mark_rated_as_watched value
    mark_rated_as_watched_value = credentials.get('mark_rated_as_watched')
    if mark_rated_as_watched_value not in [None, "empty"]:
        return mark_rated_as_watched_value

    # Prompt the user for input until valid
    while True:
        user_input = input("Do you want to mark rated movies and episodes as watched? (y/n): ").strip().lower()
        if user_input == 'y':
            mark_rated_as_watched_value = True
            break
        elif user_input == 'n':
            mark_rated_as_watched_value = False
            break
        else:
            print("Invalid input. Please enter 'y' or 'n'.")

    # Update and save the credentials only if the file will change
    credentials['mark_rated_as_watched'] = mark_rated_as_watched_value
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(credentials, file, indent=4, separators=(', ', ': '))
    except Exception as e:
        logging.error("Failed to write to credentials file.", exc_info=True)
        raise

    return mark_rated_as_watched_value

def check_imdb_reviews_last_submitted():
    """
    Check if 240 hours (10 days) have passed since the last IMDb reviews submission.
    If the condition is met, update the timestamp and save it.

    Returns:
        bool: True if 240 hours have passed, otherwise False.
    """
    # Define file path
    file_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'credentials.txt')

    # Initialize default credentials
    credentials = {}

    # Load credentials if the file exists
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            try:
                credentials = json.load(file)
            except json.JSONDecodeError:
                pass  # Handle the case where the file is not a valid JSON

    # Retrieve last submission date or default to 10 days ago
    last_submitted_str = credentials.get('imdb_reviews_last_submitted_date')
    last_submitted_date = None
    if last_submitted_str:
        try:
            last_submitted_date = datetime.datetime.strptime(last_submitted_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            pass  # Handle invalid date format

    # Default to 10 days ago if no valid date is found
    if not last_submitted_date:
        last_submitted_date = datetime.datetime.now() - datetime.timedelta(hours=240)

    # Check if 240 hours have passed
    if datetime.datetime.now() - last_submitted_date >= datetime.timedelta(hours=240):
        # Update the timestamp
        credentials['imdb_reviews_last_submitted_date'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Save updated credentials to file
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(credentials, file, indent=4, separators=(', ', ': '))

        return True

    return False
        
def prompt_sync_reviews():
    """
    Handles the synchronization preference for reviews by reading and updating a credentials file.
    Returns:
        bool: True if user wants to sync reviews, False otherwise.
    """
    # Define the file path
    file_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'credentials.txt')

    # Attempt to read the sync_reviews value from the credentials file
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            credentials = json.load(file)
            sync_reviews_value = credentials.get('sync_reviews')

            # Return the value if it exists and is not "empty"
            if sync_reviews_value is not None and sync_reviews_value != "empty":
                return sync_reviews_value
    except FileNotFoundError:
        # Log the error but continue to prompt the user
        EL.error("Credentials file not found", exc_info=True)
        credentials = {}

    # Prompt the user for input until a valid response is given
    while True:
        print("Please note: reviews synced to IMDB will use 'My Review' as the title field.")
        user_input = input("Do you want to sync reviews? (y/n): ").strip().lower()

        if user_input == 'y':
            sync_reviews_value = True
            break
        elif user_input == 'n':
            sync_reviews_value = False
            break
        else:
            print("Invalid input. Please enter 'y' or 'n'.")

    # Update the sync_reviews value in the credentials file
    credentials['sync_reviews'] = sync_reviews_value

    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(credentials, file, indent=4, separators=(', ', ': '))
    except Exception as e:
        EL.error("Failed to write to credentials file", exc_info=True)

    return sync_reviews_value

def prompt_remove_watched_from_watchlists():
    """
    Prompts the user to decide if watched items should be removed from watchlists.
    Reads and updates the decision in a credentials file to avoid repeated prompting.
    """
    # Define the file path for credentials
    here = os.path.abspath(os.path.dirname(__file__))
    file_path = os.path.join(here, 'credentials.txt')

    # Attempt to read the existing configuration
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            credentials = json.load(file)
            remove_watched_from_watchlists_value = credentials.get('remove_watched_from_watchlists')
            if remove_watched_from_watchlists_value is not None and remove_watched_from_watchlists_value != "empty":
                return remove_watched_from_watchlists_value  # Return the stored value if it exists
    except FileNotFoundError:
        # Log the error if the file is missing but continue execution
        EL.logger.error("Credentials file not found.", exc_info=True)
        credentials = {}

    # Prompt the user for input until a valid choice is made
    while True:
        print("Movies and Episodes are removed from watchlists after 1 play.")
        print("Shows are removed when at least 80% of the episodes are watched AND the series is marked as ended or cancelled.")
        print("Do you want to remove watched items from watchlists? (y/n)")
        user_input = input("Enter your choice: ").strip().lower()

        if user_input == 'y':
            remove_watched_from_watchlists_value = True
            break
        elif user_input == 'n':
            remove_watched_from_watchlists_value = False
            break
        else:
            print("Invalid input. Please enter 'y' or 'n'.")

    # Save the user's choice to the credentials file
    credentials['remove_watched_from_watchlists'] = remove_watched_from_watchlists_value
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(credentials, file, indent=4, separators=(', ', ': '))
    except Exception as e:
        EL.logger.error("Failed to write to credentials file.", exc_info=True)
        raise e

    return remove_watched_from_watchlists_value