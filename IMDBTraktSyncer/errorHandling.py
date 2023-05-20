import traceback
import requests
try:
    from IMDBTraktSyncer import verifyCredentials as VC
except ImportError:
    import verifyCredentials as VC

def report_error(error_message):
    github_issue_url = "https://github.com/RileyXX/IMDB-Trakt-Syncer/issues/new?template=bug_report.yml"
    traceback_info = traceback.format_exc()

    print("\n--- ERROR ---")
    print(error_message)
    print("Please submit the error to GitHub with the following information:")
    print("-" * 50)
    print(traceback_info)
    print("-" * 50)
    print(f"Submit the error here: {github_issue_url}")
    print("-" * 50)

def make_trakt_request(url, headers=None, params=None, payload=None, max_retries=3):
    if headers is None:
        headers = {
            'Content-Type': 'application/json',
            'trakt-api-version': '2',
            'trakt-api-key': VC.trakt_client_id,
            'Authorization': f'Bearer {VC.trakt_access_token}'
        }

    retry_delay = 5  # seconds between retries
    retry_attempts = 0

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
                error_message = get_trakt_message(response.status_code)
                print(f"Request failed with status code {response.status_code}: {error_message}")
                return None

        except requests.exceptions.RequestException as e:
            print(f"Request failed with exception: {e}")
            return None

    print("Max retry attempts reached with Trakt API, request failed.")
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

    return error_messages.get(status_code, "Unknown error")