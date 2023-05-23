import requests
try:
    from IMDBTraktSyncer import errorHandling as EH
except ImportError:
    import errorHandling as EH

def authenticate(client_id, client_secret):
    CLIENT_ID = client_id
    CLIENT_SECRET = client_secret
    REDIRECT_URI = 'urn:ietf:wg:oauth:2.0:oob'

    # Set up the authorization endpoint URL
    auth_url = 'https://trakt.tv/oauth/authorize'

    # Construct the authorization URL with the necessary parameters
    params = {
        'response_type': 'code',
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        'state': 'mystate', # Optional - used for CSRF protection
    }
    auth_url += '?' + '&'.join([f'{key}={value}' for key, value in params.items()])

    # Print out the authorization URL and instruct the user to visit it
    print(f'\nPlease visit the following URL to authorize this application: \n{auth_url}\n')

    # After the user grants authorization, they will be redirected back to the redirect URI with a temporary authorization code.
    # Extract the authorization code from the URL and use it to request an access token from the Trakt API.
    authorization_code = input('Please enter the authorization code from the URL: ')

    # Set up the access token request
    headers = {
        'Content-Type': 'application/json'
    }
    data = {
        'code': authorization_code,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'redirect_uri': REDIRECT_URI,
        'grant_type': 'authorization_code'
    }

    # Make the request to get the access token
    response = EH.make_trakt_request('https://api.trakt.tv/oauth/token', payload=data)

    # Parse the JSON response from the API
    json_data = response.json()

    # Extract the access token from the response
    ACCESS_TOKEN = json_data['access_token']
    
    return ACCESS_TOKEN