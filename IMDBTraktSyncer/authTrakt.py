import datetime
import sys
import time
from datetime import timedelta, timezone
from pathlib import Path
import requests
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from IMDBTraktSyncer import errorHandling as EH
from IMDBTraktSyncer import errorLogger as EL

TRAKT_DEVICE_CODE_URL = 'https://auth.trakt.tv/oauth/device/code'
TRAKT_DEVICE_TOKEN_URL = 'https://auth.trakt.tv/oauth/device/token'
TRAKT_TOKEN_URL = 'https://auth.trakt.tv/oauth/token'

def _authorize_with_device_code(client_id):
    response = requests.post(
        TRAKT_DEVICE_CODE_URL,
        json={'client_id': client_id},
        timeout=20
    )
    response.raise_for_status()
    device_data = response.json()

    device_code = device_data['device_code']
    user_code = device_data['user_code']
    verification_url = device_data['verification_url']
    expires_in = int(device_data['expires_in'])
    interval = int(device_data['interval'])
    if expires_in <= 0 or interval <= 0:
        raise ValueError("Trakt returned an invalid device authorization lifetime or polling interval.")

    print(
        f"\nVisit {verification_url} and enter this code to authorize the application:\n"
        f"{user_code}\n"
        "This terminal will wait for authorization."
    )

    deadline = time.monotonic() + expires_in
    while True:
        remaining_time = deadline - time.monotonic()
        if remaining_time <= 0:
            raise TimeoutError("Trakt device authorization expired. Restart the script to try again.")

        time.sleep(min(interval, remaining_time))
        if time.monotonic() >= deadline:
            raise TimeoutError("Trakt device authorization expired. Restart the script to try again.")

        response = requests.post(
            TRAKT_DEVICE_TOKEN_URL,
            json={'code': device_code, 'client_id': client_id},
            timeout=20
        )
        if response.status_code == 200:
            return response.json()
        if response.status_code == 400:
            continue
        if response.status_code == 429:
            interval += 5
            continue

        error_messages = {
            404: "The device code is invalid.",
            409: "The device code has already been used.",
            410: "The device code expired.",
            418: "Authorization was denied.",
        }
        if response.status_code in error_messages:
            raise RuntimeError(f"Trakt authorization failed: {error_messages[response.status_code]}")
        response.raise_for_status()
        raise RuntimeError(f"Unexpected Trakt device authorization response: {response.status_code}")

def authenticate(client_id, refresh_token=None):

    if refresh_token:
        # If a refresh token is provided, use it to get a new access token
        data = {
            'refresh_token': refresh_token,
            'client_id': client_id,
            'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
            'grant_type': 'refresh_token'
        }
        headers = {
            'Content-Type': 'application/json',
        }
        
        # Use make_trakt_request for the POST request
        response = EH.make_trakt_request(TRAKT_TOKEN_URL, headers=headers, payload=data)

        if response:
            json_data = response.json()
            access_token = json_data['access_token']
            refresh_token = json_data['refresh_token']
            expires_in = json_data['expires_in']
            
            # Calculate the exact expiration time and subtract 120 seconds buffer
            expiration_time = datetime.datetime.now(timezone.utc) + timedelta(seconds=expires_in - 120)
            expiration_time = expiration_time.replace(tzinfo=timezone.utc).isoformat()
            
            return access_token, refresh_token, expiration_time
        else:
            # empty response, invalid refresh token, prompt user to re-authenticate
            return authenticate(client_id)

    else:
        json_data = _authorize_with_device_code(client_id)

        access_token = json_data['access_token']
        refresh_token = json_data['refresh_token']
        expires_in = json_data['expires_in']

        expiration_time = datetime.datetime.now(timezone.utc) + timedelta(seconds=expires_in - 120)
        expiration_time = expiration_time.replace(tzinfo=timezone.utc).isoformat()

        return access_token, refresh_token, expiration_time

    return None