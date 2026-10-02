import datetime
import time
from datetime import timedelta, timezone

import requests

from IMDBTraktSyncer import errorHandling as EH


def _tokens(data):
    expiration_time = datetime.datetime.now(timezone.utc) + timedelta(
        seconds=max(0, int(data['expires_in']) - 120)
    )
    return data['access_token'], data['refresh_token'], expiration_time.isoformat()


def authenticate(client_id, client_secret, refresh_token=None):
    headers = {'Content-Type': 'application/json'}
    if refresh_token:
        response = EH.make_trakt_request(
            'https://auth.trakt.tv/oauth/token', headers=headers,
            payload={
                'refresh_token': refresh_token,
                'client_id': client_id,
                'client_secret': client_secret,
                'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
                'grant_type': 'refresh_token'
            }
        )
        if response is not None and response.status_code == 200:
            return _tokens(response.json())
        if response is None or response.status_code not in (400, 401):
            raise RuntimeError('Trakt token refresh failed. Please try again later.')
        print('Trakt session expired. Please authorize this application again.')

    response = EH.make_trakt_request(
        'https://api.trakt.tv/oauth/device/code', headers=headers,
        payload={'client_id': client_id}
    )
    if response is None or response.status_code != 200:
        status = response.status_code if response is not None else 'no response'
        raise RuntimeError(
            'Unable to start Trakt device authorization ({}). '
            'Check your Trakt application Client ID and try again.'.format(status)
        )
    device = response.json()
    deadline = time.monotonic() + int(device['expires_in'])
    interval = max(1, int(device['interval']))
    print('\nVisit this URL to authorize the application: {}'.format(device['verification_url']))
    print('Enter this code on the Trakt page: {}\n'.format(device['user_code']))
    print('Waiting for Trakt authorization. Press Ctrl+C to cancel.')
    payload = {
        'code': device['device_code'],
        'client_id': client_id,
        'client_secret': client_secret
    }
    terminal_errors = {
        404: 'The Trakt device code is invalid.',
        409: 'The Trakt device code has already been used.',
        410: 'The Trakt device code has expired.',
        418: 'Trakt authorization was denied.'
    }
    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        time.sleep(min(interval, max(0, remaining)))
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            # Poll directly: 400 means pending, and 429 changes the polling interval.
            response = requests.post(
                'https://api.trakt.tv/oauth/device/token', headers=headers,
                json=payload, timeout=min(20, remaining)
            )
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            continue
        if response.status_code == 200:
            print('Trakt authorization successful.')
            return _tokens(response.json())
        if response.status_code == 400:
            continue
        if response.status_code == 429:
            interval += 5
            try:
                interval = max(interval, int(response.headers.get('Retry-After', interval)))
            except ValueError:
                pass
            continue
        if response.status_code in terminal_errors:
            raise RuntimeError(terminal_errors[response.status_code] + ' Run the script again to retry.')
        if response.status_code >= 500:
            continue
        raise RuntimeError('Trakt device authorization failed (HTTP {}).'.format(response.status_code))
    raise RuntimeError('Trakt authorization timed out. Run the script again to get a new code.')
