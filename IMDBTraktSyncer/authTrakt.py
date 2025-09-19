import sys
import datetime
from datetime import timedelta, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from IMDBTraktSyncer import errorHandling as EH
from IMDBTraktSyncer import errorLogger as EL

def authenticate(client_id, client_secret, refresh_token=None):

    redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'

    if refresh_token:
        # If a refresh token is provided, use it to get a new access token
        data = {
            'refresh_token': refresh_token,
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': redirect_uri,
            'grant_type': 'refresh_token'
        }
        headers = {
            'Content-Type': 'application/json',
        }
        
        # Use make_trakt_request for the POST request
        response = EH.make_trakt_request('https://api.trakt.tv/oauth/token', headers=headers, payload=data)

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
            return authenticate(client_id, client_secret)

    else:
        # Set up the authorization endpoint URL
        auth_url = 'https://trakt.tv/oauth/authorize'

        # Construct the authorization URL with the necessary parameters
        params = {
            'response_type': 'code',
            'client_id': client_id,
            'redirect_uri': redirect_uri,
        }
        auth_url += '?' + '&'.join([f'{key}={value}' for key, value in params.items()])
        
        # Print out the authorization URL and instruct the user to visit it
        print(f'\nPlease visit the following URL to authorize this application: \n{auth_url}\n')
        
        # After the user grants authorization, they will be redirected back to the redirect URI with a temporary authorization code.
        # Extract the authorization code from the URL and use it to request an access token from the Trakt API.
        authorization_code = input('Please enter the authorization code from the URL: ')
        if not authorization_code.strip():
            raise ValueError("Authorization code cannot be empty.")

        # Set up the access token request
        data = {
            'code': authorization_code,
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code'
        }
        headers = {
            'Content-Type': 'application/json',
        }
        
        # Use make_trakt_request for the POST request
        response = EH.make_trakt_request('https://api.trakt.tv/oauth/token', headers=headers, payload=data)
         
        if response:
            # Parse the JSON response from the API
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
            return authenticate(client_id, client_secret)

    return None