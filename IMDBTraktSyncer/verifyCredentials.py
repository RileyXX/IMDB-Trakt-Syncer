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
        "imdb_username": "empty",
        "imdb_password": "empty",
        "last_trakt_token_refresh": "empty"
    }

    # Load existing file data
    if os.path.isfile(file_path) and os.path.getsize(file_path) > 0:
        # Read the credentials file
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                file_data = json.load(f)
            except json.decoder.JSONDecodeError:
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
        json.dump(file_data, f)

    # Return the credentials
    return values["trakt_client_id"], values["trakt_client_secret"], values["trakt_access_token"], values["trakt_refresh_token"], values["imdb_username"], values["imdb_password"]

def prompt_sync_ratings():
    # Define the file path
    here = os.path.abspath(os.path.dirname(__file__))
    file_path = os.path.join(here, 'credentials.txt')

    # Check if credentials file exists
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            credentials = json.load(file)
            sync_ratings_value = credentials.get('sync_ratings')
            if sync_ratings_value is not None:
                return sync_ratings_value
    except FileNotFoundError:
        error_message = "File not found error"
        EL.logger.error(error_message, exc_info=True)
        pass

    while True:
        # Prompt the user for input
        print("Do you want to sync ratings? (y/n)")
        user_input = input("Enter your choice: ")

        # Validate user input
        if user_input.lower() == 'y':
            sync_ratings_value = True
            break
        elif user_input.lower() == 'n':
            sync_ratings_value = False
            break
        else:
            # Invalid input, ask again
            print("Invalid input. Please enter 'y' or 'n'.")

    # Update the value in the JSON file
    credentials = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            credentials = json.load(file)
    except FileNotFoundError:
        error_message = "File not found error"
        EL.logger.error(error_message, exc_info=True)
        pass

    credentials['sync_ratings'] = sync_ratings_value

    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(credentials, file)

    # return true or false
    return sync_ratings_value

def prompt_sync_watchlist():
    # Define the file path
    here = os.path.abspath(os.path.dirname(__file__))
    file_path = os.path.join(here, 'credentials.txt')

    # Check if credentials file exists
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            credentials = json.load(file)
            sync_watchlist_value = credentials.get('sync_watchlist')
            if sync_watchlist_value is not None:
                return sync_watchlist_value
    except FileNotFoundError:
        error_message = "File not found error"
        EL.logger.error(error_message, exc_info=True)
        pass

    while True:
        # Prompt the user for input
        print("Do you want to sync watchlists? (y/n)")
        user_input = input("Enter your choice: ")

        # Validate user input
        if user_input.lower() == 'y':
            sync_watchlist_value = True
            break
        elif user_input.lower() == 'n':
            sync_watchlist_value = False
            break
        else:
            # Invalid input, ask again
            print("Invalid input. Please enter 'y' or 'n'.")

    # Update the value in the JSON file
    credentials = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            credentials = json.load(file)
    except FileNotFoundError:
        error_message = "File not found error"
        EL.logger.error(error_message, exc_info=True)
        pass

    credentials['sync_watchlist'] = sync_watchlist_value

    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(credentials, file)

    # return true or false
    return sync_watchlist_value

# Last run function, used to determine when the last time IMDB reviews were submitted    
def check_imdb_reviews_last_submitted():
    here = os.path.abspath(os.path.dirname(__file__))
    file_path = os.path.join(here, 'credentials.txt')
    
    # Load credentials from credentials.txt
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            credentials = json.load(file)
    else:
        credentials = {}

    imdb_reviews_last_submitted_date_str = credentials.get('imdb_reviews_last_submitted_date')

    # If imdb_reviews_last_submitted_date is not available or not in the correct format, consider it as 10 days ago
    imdb_reviews_last_submitted_date = datetime.datetime.strptime(imdb_reviews_last_submitted_date_str, '%Y-%m-%d %H:%M:%S') if imdb_reviews_last_submitted_date_str else datetime.datetime.now() - datetime.timedelta(hours=240)

    # Check if 240 hours have passed since the last run
    if datetime.datetime.now() - imdb_reviews_last_submitted_date >= datetime.timedelta(hours=240):
        # Update the imdb_reviews_last_submitted_date with the current time
        credentials['imdb_reviews_last_submitted_date'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Save updated credentials to credentials.txt
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(credentials, file)

        return True
    else:
        return False
        
def prompt_sync_reviews():
    # Define the file path
    here = os.path.abspath(os.path.dirname(__file__))
    file_path = os.path.join(here, 'credentials.txt')

    # Check if credentials file exists
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            credentials = json.load(file)
            sync_reviews_value = credentials.get('sync_reviews')
            if sync_reviews_value is not None:
                return sync_reviews_value
    except FileNotFoundError:
        error_message = "File not found error"
        EL.logger.error(error_message, exc_info=True)
        pass

    while True:
        # Prompt the user for input
        print("Please note: reviews synced to IMDB will use \"My Review\" as the title field.")
        print("Do you want to sync reviews? (y/n)")
        user_input = input("Enter your choice: ")

        # Validate user input
        if user_input.lower() == 'y':
            sync_reviews_value = True
            break
        elif user_input.lower() == 'n':
            sync_reviews_value = False
            break
        else:
            # Invalid input, ask again
            print("Invalid input. Please enter 'y' or 'n'.")

    # Update the value in the JSON file
    credentials = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            credentials = json.load(file)
    except FileNotFoundError:
        error_message = "File not found error"
        EL.logger.error(error_message, exc_info=True)
        pass

    credentials['sync_reviews'] = sync_reviews_value

    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(credentials, file)

    # return true or false
    return sync_reviews_value

def prompt_remove_watched_from_watchlists():
    # Define the file path
    here = os.path.abspath(os.path.dirname(__file__))
    file_path = os.path.join(here, 'credentials.txt')

    # Check if credentials file exists
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            credentials = json.load(file)
            remove_watched_from_watchlists_value = credentials.get('remove_watched_from_watchlists')
            if remove_watched_from_watchlists_value is not None:
                return remove_watched_from_watchlists_value
    except FileNotFoundError:
        error_message = "File not found error"
        EL.logger.error(error_message, exc_info=True)
        pass

    while True:
        # Prompt the user for input
        print("Movies and Episodes are removed from watchlists after 1 play.")
        print("Shows are removed when atleast 80% of the episodes are watched AND the series is marked as ended or cancelled.")
        print("Do you want to remove watched items watchlists? (y/n)")
        user_input = input("Enter your choice: ")

        # Validate user input
        if user_input.lower() == 'y':
            remove_watched_from_watchlists_value = True
            break
        elif user_input.lower() == 'n':
            remove_watched_from_watchlists_value = False
            break
        else:
            # Invalid input, ask again
            print("Invalid input. Please enter 'y' or 'n'.")

    # Update the value in the JSON file
    credentials = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            credentials = json.load(file)
    except FileNotFoundError:
        error_message = "File not found error"
        EL.logger.error(error_message, exc_info=True)
        pass

    credentials['remove_watched_from_watchlists'] = remove_watched_from_watchlists_value

    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(credentials, file)

    # return true or false
    return remove_watched_from_watchlists_value