import requests
import os

here = os.path.abspath(os.path.dirname(__file__))
file_path = os.path.join(here, 'credentials.txt')

with open(file_path, "r") as f:
    lines = f.readlines()
values = {}
for line in lines:
    key, value = line.strip().split("=")
    values[key] = value
CLIENT_ID = values["trakt_client_id"]
CLIENT_SECRET = values["trakt_client_secret"]
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
response = requests.post('https://api.trakt.tv/oauth/token', headers=headers, json=data)

# Parse the JSON response from the API
json_data = response.json()

# Extract the access token from the response
ACCESS_TOKEN = json_data['access_token']

# Save the access token value to the credentials file
with open(file_path, "w") as f:
    for key, value in values.items():
        if key == "trakt_access_token":
            f.write(f"{key}={ACCESS_TOKEN}\n")
        else:
            f.write(f"{key}={value}\n")

# Print out a message indicating that the token has been saved
print(f'Trakt access token saved to credentials.txt')