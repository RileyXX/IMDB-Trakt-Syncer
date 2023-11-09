import requests
import time
try:
    from IMDBTraktSyncer import errorLogger as EL
except ImportError:
    import errorLogger as EL

def make_trakt_request(url, headers=None, params=None, payload=None, max_retries=5):
    retry_delay = 1  # seconds between retries
    retry_attempts = 0
    
    if headers is None:
        headers = {
            'Content-Type': 'application/json',
        }

    while retry_attempts < max_retries:
        response = None
        try:
            if payload is None:
                if params:
                    response = requests.get(url, headers=headers, params=params)
                else:
                    response = requests.get(url, headers=headers)
            else:
                response = requests.post(url, headers=headers, json=payload)

            if response.status_code in [200, 201, 204]:
                return response  # Request succeeded, return response
            elif response.status_code in [429, 500, 502, 503, 504, 520, 521, 522]:
                # Server overloaded or rate limit exceeded, retry after delay
                retry_attempts += 1
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff for retries
            else:
                # Handle other status codes as needed
                status_message = get_trakt_message(response.status_code)
                error_message = f"Request failed with status code {response.status_code}: {status_message}"
                print(f"   - {error_message}")
                EL.logger.error(f"{error_message}. URL: {url}")
                return None

        except requests.exceptions.RequestException as e:
            error_message = f"Request failed with exception: {e}"
            print(f"   - {error_message}")
            EL.logger.error(error_message, exc_info=True)
            return None

    error_message = "Max retry attempts reached with Trakt API, request failed."
    print(f"   - {error_message}")
    EL.logger.error(error_message)
    return None

def get_trakt_message(status_code):
    error_messages = {
        200: "Success",
        201: "Success - new resource created (POST)",
        204: "Success - no content to return (DELETE)",
        400: "Bad Request - request couldn't be parsed",
        401: "Unauthorized - OAuth must be provided",
        403: "Forbidden - invalid API key or unapproved app",
        404: "Not Found - method exists, but no record found",
        405: "Method Not Found - method doesn't exist",
        409: "Conflict - resource already created",
        412: "Precondition Failed - use application/json content type",
        420: "Account Limit Exceeded - list count, item count, etc",
        422: "Unprocessable Entity - validation errors",
        423: "Locked User Account - have the user contact support",
        426: "VIP Only - user must upgrade to VIP",
        429: "Rate Limit Exceeded",
        500: "Server Error - please open a support ticket",
        502: "Service Unavailable - server overloaded (try again in 30s)",
        503: "Service Unavailable - server overloaded (try again in 30s)",
        504: "Service Unavailable - server overloaded (try again in 30s)",
        520: "Service Unavailable - Cloudflare error",
        521: "Service Unavailable - Cloudflare error",
        522: "Service Unavailable - Cloudflare error"
    }

    return error_messages.get(status_code, "Unknown status code")

import requests

def authenticate(client_id, client_secret, refresh_token=None):
    CLIENT_ID = client_id
    CLIENT_SECRET = client_secret

    REDIRECT_URI = 'urn:ietf:wg:oauth:2.0:oob'

    if refresh_token:
        # If a refresh token is provided, use it to get a new access token
        data = {
            'refresh_token': refresh_token,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'redirect_uri': REDIRECT_URI,
            'grant_type': 'refresh_token'
        }

        # Use make_trakt_request for the POST request
        response = make_trakt_request('https://api.trakt.tv/oauth/token', payload=data)

        if response:
            json_data = response.json()
            ACCESS_TOKEN = json_data['access_token']
            REFRESH_TOKEN = json_data['refresh_token']
            return ACCESS_TOKEN, REFRESH_TOKEN
        else:
            # empty response, invalid refresh token, prompt user to re-authenticate
            return authenticate(CLIENT_ID, CLIENT_SECRET)

    else:
        # Set up the authorization endpoint URL
        auth_url = 'https://trakt.tv/oauth/authorize'

        # Construct the authorization URL with the necessary parameters
        params = {
            'response_type': 'code',
            'client_id': CLIENT_ID,
            'redirect_uri': REDIRECT_URI,
        }
        auth_url += '?' + '&'.join([f'{key}={value}' for key, value in params.items()])

        # Print out the authorization URL and instruct the user to visit it
        print(f'\nPlease visit the following URL to authorize this application: \n{auth_url}\n')

        # After the user grants authorization, they will be redirected back to the redirect URI with a temporary authorization code.
        # Extract the authorization code from the URL and use it to request an access token from the Trakt API.
        authorization_code = input('Please enter the authorization code from the URL: ')

        # Set up the access token request
        data = {
            'code': authorization_code,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'redirect_uri': REDIRECT_URI,
            'grant_type': 'authorization_code'
        }

        # Use make_trakt_request for the POST request
        response = make_trakt_request('https://api.trakt.tv/oauth/token', payload=data)

        if response:
            # Parse the JSON response from the API
            json_data = response.json()

            # Extract the access token from the response
            ACCESS_TOKEN = json_data['access_token']

            # Extract the refresh token from the response
            REFRESH_TOKEN = json_data['refresh_token']

            return ACCESS_TOKEN, REFRESH_TOKEN

    return None
