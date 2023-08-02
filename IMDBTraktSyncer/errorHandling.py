import traceback
import requests
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import SessionNotCreatedException
try:
    from IMDBTraktSyncer import verifyCredentials as VC
    from IMDBTraktSyncer import errorLogger as EL
except ImportError:
    import verifyCredentials as VC
    import errorLogger as EL

class PageLoadException(Exception):
    pass

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

def make_trakt_request(url, headers=None, params=None, payload=None, max_retries=5):
    if headers is None:
        headers = {
            'Content-Type': 'application/json',
            'trakt-api-version': '2',
            'trakt-api-key': VC.trakt_client_id,
            'Authorization': f'Bearer {VC.trakt_access_token}'
        }

    retry_delay = 1  # seconds between retries
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

    return error_messages.get(status_code, "Unknown error")

# Function to get page with retries and adjusted wait time
def get_page_with_retries(url, driver, wait, total_wait_time=180, initial_wait_time=5):
    num_retries = total_wait_time // initial_wait_time
    wait_time = total_wait_time / num_retries
    max_retries = num_retries
    status_code = None

    for retry in range(max_retries):
        try:
            driver.get(url)
            
            # Wait until the status code becomes available
            wait.until(lambda driver: driver.execute_script(
                "return window.performance.getEntries().length > 0 && window.performance.getEntries()[0].responseStatus !== undefined"
            ))
            
            # Get the HTTP status code of the page using JavaScript
            status_code = driver.execute_script(
                "return window.performance.getEntries()[0].responseStatus;"
            )
            
            # Check for any error codes
            if status_code is None:
                return True, status_code, url  # Unable to determine page loaded status
            elif status_code >= 400:
                raise PageLoadException(f'Failed to load page. Status code: {status_code}. URL: {url}')
            else:
                return True, status_code, url  # Page loaded successfully

        except (PageLoadException) as e:
            print(f"   - Error: {str(e)}")
            retryable_error_codes = [408, 425, 429, 500, 502, 503, 504]
            if retry + 1 < max_retries and status_code in retryable_error_codes:
                seconds_left = int((max_retries - retry) * wait_time)
                print(f"   - Retrying ({retry + 1}/{max_retries}) {seconds_left} seconds remaining...")
                time.sleep(wait_time)
            else:
                error_message = f"Max retries reached or not retrying: {e}"
                EL.logger.error(error_message, exc_info=True)
                # Max retries reached or not retrying
                return False, status_code, url

    # All retries failed and page was not loaded successfully, return False
    return False, None, url