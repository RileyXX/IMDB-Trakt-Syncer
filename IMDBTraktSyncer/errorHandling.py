import traceback
import requests
from requests.exceptions import ConnectionError, RequestException, Timeout, TooManyRedirects, SSLError, ProxyError
import time
import os
import inspect
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException, NoSuchElementException, TimeoutException, StaleElementReferenceException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import SessionNotCreatedException
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from IMDBTraktSyncer import verifyCredentials as VC
from IMDBTraktSyncer import errorLogger as EL

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
    
    # Set default headers if none are provided
    if headers is None:
        # Get credentials
        trakt_client_id, _, trakt_access_token, _, _, _ = VC.prompt_get_credentials()
        
        headers = {
            'Content-Type': 'application/json',
            'trakt-api-version': '2',
            'trakt-api-key': trakt_client_id,
            'Authorization': f'Bearer {trakt_access_token}'
        }
    
    retry_delay = 1  # Initial delay between retries (in seconds)
    retry_attempts = 0  # Count of retry attempts made
    connection_timeout = 20  # Timeout for requests (in seconds)
    total_wait_time = sum(retry_delay * (2 ** i) for i in range(max_retries))  # Total possible wait time

    # Retry loop to handle network errors or server overload scenarios
    while retry_attempts < max_retries:
        response = None
        try:
            # Send GET or POST request depending on whether a payload is provided
            if payload is None:
                if params:
                    # GET request with query parameters
                    response = requests.get(url, headers=headers, params=params, timeout=connection_timeout)
                else:
                    # GET request without query parameters
                    response = requests.get(url, headers=headers, timeout=connection_timeout)
            else:
                # POST request with JSON payload
                response = requests.post(url, headers=headers, json=payload, timeout=connection_timeout)

            # If request is successful, return the response
            if response.status_code in [200, 201, 204]:
                return response
            
            # Handle retryable server errors and rate limit exceeded
            elif response.status_code in [429, 500, 502, 503, 504, 520, 521, 522]:
                retry_attempts += 1  # Increment retry counter

                # Respect the 'Retry-After' header if provided, otherwise use default delay
                retry_after = int(response.headers.get('Retry-After', retry_delay))
                if response.status_code != 429:
                    remaining_time = total_wait_time - sum(retry_delay * (2 ** i) for i in range(retry_attempts))
                    print(f"   - Server returned {response.status_code}. Retrying after {retry_after}s... "
                          f"({retry_attempts}/{max_retries}) - Time remaining: {remaining_time}s")
                    EL.logger.warning(f"Server returned {response.status_code}. Retrying after {retry_after}s... "
                                      f"({retry_attempts}/{max_retries}) - Time remaining: {remaining_time}s")

                time.sleep(retry_after)  # Wait before retrying
                retry_delay *= 2  # Apply exponential backoff for retries
            
            else:
                # Handle non-retryable HTTP status codes
                status_message = get_trakt_message(response.status_code)
                error_message = f"Request failed with status code {response.status_code}: {status_message}"
                print(f"   - {error_message}")
                EL.logger.error(f"{error_message}. URL: {url}")
                return response  # Exit with failure for non-retryable errors

        # Handle Network errors (connection issues, timeouts, SSL, etc.)
        except (ConnectionError, Timeout, TooManyRedirects, SSLError, ProxyError) as network_error:
            retry_attempts += 1  # Increment retry counter
            remaining_time = total_wait_time - sum(retry_delay * (2 ** i) for i in range(retry_attempts))
            print(f"   - Network error: {network_error}. Retrying ({retry_attempts}/{max_retries})... "
                  f"Time remaining: {remaining_time}s")
            EL.logger.warning(f"Network error: {network_error}. Retrying ({retry_attempts}/{max_retries})... "
                              f"Time remaining: {remaining_time}s")
            
            time.sleep(retry_delay)  # Wait before retrying
            retry_delay *= 2  # Apply exponential backoff for retries

        # Handle general request-related exceptions (non-retryable)
        except requests.exceptions.RequestException as req_err:
            error_message = f"Request failed with exception: {req_err}"
            print(f"   - {error_message}")
            EL.logger.error(error_message, exc_info=True)
            return None  # Exit on non-retryable exceptions

    # If all retries are exhausted, log and return failure
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

def get_page_with_retries(url, driver, wait, total_wait_time=180, initial_wait_time=5):
    num_retries = total_wait_time // initial_wait_time
    wait_time = total_wait_time / num_retries
    max_retries = num_retries
    status_code = None
    total_time_spent = 0  # Track total time spent across retries

    for retry in range(max_retries):
        try:
            start_time = time.time()  # Track time taken for each retry attempt
            
            # Temporary solution to Chromium bug: Restart tab logic. See: https://issues.chromium.org/issues/386887881
            # Open a new tab and close any extras from previous iterations
            driver.execute_script("window.open();")
            new_tab = driver.window_handles[-1]
            driver.switch_to.window(new_tab)

            # Close all other tabs except the current new tab
            for handle in driver.window_handles[:-1]:
                driver.switch_to.window(handle)
                driver.close()
            driver.switch_to.window(new_tab)

            # Attempt to load the page using Selenium driver
            driver.get(url)

            # Wait until the status code becomes available
            wait.until(lambda driver: driver.execute_script(
                "return window.performance.getEntries().length > 0 && window.performance.getEntries()[0].responseStatus !== undefined"
            ))

            # Get the HTTP status code of the page using JavaScript
            status_code = driver.execute_script(
                "return window.performance.getEntries()[0].responseStatus;"
            )
            
            # Update resolved_url with the current URL after potential redirects
            resolved_url = driver.current_url

            # Handle status codes
            if status_code is None or status_code == 0:
                print(f"   - Unable to determine page load status. Status code returned 0 or None. Retrying...")
                elapsed_time = time.time() - start_time  # Time taken for this attempt
                total_time_spent += elapsed_time

                if total_time_spent >= total_wait_time:
                    print("   - Total wait time exceeded. Aborting.")
                    return False, None, url, driver, wait

                print(f"   - Remaining time for retries: {int(total_wait_time - total_time_spent)} seconds.")
                time.sleep(wait_time)
                continue

            elif status_code >= 400:
                raise PageLoadException(f'Failed to load page. Status code: {status_code}. URL: {url}')

            else:
                # Page loaded successfully
                return True, status_code, resolved_url, driver, wait

        except TimeoutException as e:
            frame = inspect.currentframe()
            lineno = frame.f_lineno
            filename = os.path.basename(inspect.getfile(frame))
            print(f"   - TimeoutException: {str(e).splitlines()[0]} URL: {url} (File: {filename}, Line: {lineno})")

            elapsed_time = time.time() - start_time
            total_time_spent += elapsed_time

            if total_time_spent >= total_wait_time:
                print("   - Total wait time exceeded. Aborting after timeout.")
                return False, None, url, driver, wait

            print(f"   - Retrying ({retry + 1}/{max_retries}) Time Remaining: {int(total_wait_time - total_time_spent)}s")
            time.sleep(wait_time)
            continue

        except WebDriverException as e:
            frame = inspect.currentframe()
            lineno = frame.f_lineno
            filename = os.path.basename(inspect.getfile(frame))
            print(f"   - Selenium WebDriver Error: {str(e).splitlines()[0]} URL: {url} (File: {filename}, Line: {lineno})")

            retryable_errors = [
                "net::ERR_NAME_NOT_RESOLVED",
                "net::ERR_DNS_TIMED_OUT",
                "net::ERR_DNS_PROBE_FINISHED_NXDOMAIN",
                "net::ERR_CONNECTION_RESET",
                "net::ERR_CONNECTION_CLOSED",
                "net::ERR_CONNECTION_REFUSED",
                "net::ERR_CONNECTION_TIMED_OUT",
                "net::ERR_SSL_PROTOCOL_ERROR",
                "net::ERR_CERT_COMMON_NAME_INVALID",
                "net::ERR_CERT_DATE_INVALID",
                "net::ERR_NETWORK_CHANGED"
            ]

            if any(error in str(e) for error in retryable_errors):
                elapsed_time = time.time() - start_time
                total_time_spent += elapsed_time

                if total_time_spent >= total_wait_time:
                    print("   - Total wait time exceeded. Aborting after WebDriver error.")
                    return False, None, url, driver, wait

                print(f"   - Retryable network error detected. Retrying... Time Remaining: {int(total_wait_time - total_time_spent)}s")
                time.sleep(wait_time)
                continue

            else:
                print("   - Non-retryable WebDriver error encountered. Aborting.")
                return False, None, url, driver, wait

        except PageLoadException as e:
            frame = inspect.currentframe()
            lineno = frame.f_lineno
            filename = os.path.basename(inspect.getfile(frame))
            print(f"   - PageLoadException: {str(e).splitlines()[0]} URL: {url} (File: {filename}, Line: {lineno})")

            retryable_error_codes = [408, 425, 429, 500, 502, 503, 504]

            if status_code in retryable_error_codes:
                elapsed_time = time.time() - start_time
                total_time_spent += elapsed_time

                if total_time_spent >= total_wait_time:
                    print("   - Total wait time exceeded. Aborting after page load exception.")
                    return False, None, url, driver, wait

                print(f"   - Retryable error detected. Retrying... Time Remaining: {int(total_wait_time - total_time_spent)}s")
                time.sleep(wait_time)
                continue

            else:
                print("   - Non-retryable error encountered. Aborting.")
                return False, None, url, driver, wait

    print("   - All retries failed. Unable to load page.")
    return False, None, url, driver, wait
    
def make_request_with_retries(url, method="GET", headers=None, params=None, payload=None, max_retries=5, timeout=(30, 300), stream=False):
    """
    Make an HTTP request with retry logic for handling server and connection errors.

    Args:
        url (str): The URL to request.
        method (str): HTTP method ("GET" or "POST"). Default is "GET".
        headers (dict): Optional headers for the request.
        params (dict): Optional query parameters for GET requests.
        payload (dict): Optional JSON payload for POST requests.
        max_retries (int): Maximum number of retries. Default is 5.
        timeout (tuple): Tuple of (connect timeout, read timeout). Default is (30, 300).
        stream (bool): Whether to stream the response. Default is False.

    Returns:
        requests.Response: The HTTP response object if successful.
        None: If the request fails after retries.
    """
    retry_delay = 1  # Initial delay between retries (seconds)
    retry_attempts = 0

    while retry_attempts < max_retries:
        try:
            # Make the HTTP request based on the method
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, params=params, timeout=timeout, stream=stream)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=payload, timeout=timeout, stream=stream)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            # Check for successful response
            if response.status_code in [200, 201, 204]:
                return response

            # Handle retryable HTTP status codes (rate limits or server errors)
            if response.status_code in [429, 500, 502, 503, 504]:
                retry_after = int(response.headers.get("Retry-After", retry_delay))
                print(f"Server error {response.status_code}. Retrying in {retry_after} seconds...")
                time.sleep(retry_after)
                retry_delay *= 2  # Exponential backoff
                retry_attempts += 1
            else:
                # Non-retryable errors
                print(f"Request failed with status code {response.status_code}: {response.text}")
                return None

        except (ConnectionError, Timeout, TooManyRedirects, SSLError, ProxyError) as network_err:
            # Handle network-related errors
            retry_attempts += 1
            print(f"Network error: {network_err}. Retrying in {retry_delay} seconds... (Attempt {retry_attempts}/{max_retries})")
            time.sleep(retry_delay)
            retry_delay *= 2  # Exponential backoff

        except RequestException as req_err:
            # Handle non-retryable exceptions
            print(f"Request exception: {req_err}. Exiting.")
            return None

    # If retries are exhausted, log the failure
    print(f"Max retries reached. Request to {url} failed.")
    return None
    
# Function to resolve IMDB_ID redirection using the driver
def resolve_imdb_id_with_driver(imdb_id, driver, wait):
    try:
        # Construct the IMDB URL
        url = f"https://www.imdb.com/title/{imdb_id}/"
        
        # Load URL
        success, status_code, resolved_url, driver, wait = get_page_with_retries(url, driver, wait)
        if not success:
            raise PageLoadException(f"Failed to load page. Status code: {status_code}. URL: {resolved_url}")
        
        # Extract the redirected IMDB_ID from the resolved URL
        final_imdb_id = resolved_url.split("/title/")[1].split("/")[0]
        return final_imdb_id, driver, wait

    except Exception as e:
        print(f"Error resolving IMDB_ID {imdb_id}: {e}")
        return imdb_id, driver, wait  # Return the original ID if an error occurs
    
# Function to resolve and update outdated IMDB_IDs from the trakt list based on matching Title and Type comparison
def update_outdated_imdb_ids_from_trakt(trakt_list, imdb_list, driver, wait):
    comparison_keys = ['Title', 'Type', 'IMDB_ID']  # Only compare Title and Type

    # Group items by (Title, Type)
    trakt_grouped = {}
    for item in trakt_list:
        if all(key in item for key in comparison_keys):
            key = (item['Title'], item['Type'])
            trakt_grouped.setdefault(key, set()).add(item['IMDB_ID'])

    imdb_grouped = {}
    for item in imdb_list:
        if all(key in item for key in comparison_keys):
            key = (item['Title'], item['Type'])
            imdb_grouped.setdefault(key, set()).add(item['IMDB_ID'])

    # Find conflicting items based on Title and Type where IMDB_IDs are different
    conflicting_items = {
        key for key in trakt_grouped.keys() & imdb_grouped.keys()
        if trakt_grouped[key] != imdb_grouped[key]
    }

    '''
    print(f"Initial Conflicting Items: {conflicting_items}")
    '''

    # Resolve conflicts by checking IMDB_ID redirection using the driver
    for key in conflicting_items:
        trakt_ids = trakt_grouped[key]
        imdb_ids = imdb_grouped[key]

        # Resolve IMDB_IDs using the driver only for trakt_list
        resolved_trakt_ids = set()
        for trakt_id in trakt_ids:
            resolved_id, driver, wait = resolve_imdb_id_with_driver(trakt_id, driver, wait)
            resolved_trakt_ids.add(resolved_id)

            # Directly update IMDB_ID in the original trakt_list
            for item in trakt_list:
                if item['IMDB_ID'] == trakt_id:
                    item['IMDB_ID'] = resolved_id

        # Skip resolving IMDB_IDs in imdb_list as they're already current
        resolved_imdb_ids = imdb_ids

        '''
        # If resolved trakt IDs match imdb IDs, the conflict is considered resolved
        if resolved_trakt_ids == resolved_imdb_ids:
            print(f"Resolved conflict for: {key}")
        else:
            print(f"Conflict not resolved for: {key}")
        '''

    return trakt_list, imdb_list, driver, wait
    
# Function to filter out items that share the same Title, Year, and Type
# AND have non-matching IMDB_ID values
def filter_out_mismatched_items(trakt_list, IMDB_list):
    # Define the keys to be used for comparison
    comparison_keys = ['Title', 'Year', 'Type', 'IMDB_ID']

    # Group items by (Title, Year, Type)
    trakt_grouped = {}
    for item in trakt_list:
        if all(key in item for key in comparison_keys):
            key = (item['Title'], item['Year'], item['Type'])
            trakt_grouped.setdefault(key, set()).add(item['IMDB_ID'])

    IMDB_grouped = {}
    for item in IMDB_list:
        if all(key in item for key in comparison_keys):
            key = (item['Title'], item['Year'], item['Type'])
            IMDB_grouped.setdefault(key, set()).add(item['IMDB_ID'])

    # Find conflicting items (same Title, Year, Type but different IMDB_IDs)
    conflicting_items = {
        key for key in trakt_grouped.keys() & IMDB_grouped.keys()  # Only consider shared keys
        if trakt_grouped[key] != IMDB_grouped[key]  # Check if IMDB_IDs differ
    }
    
    # Filter out conflicting items from both lists
    filtered_trakt_list = [
        item for item in trakt_list if (item['Title'], item['Year'], item['Type']) not in conflicting_items
    ]
    filtered_IMDB_list = [
        item for item in IMDB_list if (item['Title'], item['Year'], item['Type']) not in conflicting_items
    ]

    return filtered_trakt_list, filtered_IMDB_list
    
# Function to remove duplicates based on IMDB_ID
def remove_duplicates_by_imdb_id(watched_content):
    seen = set()
    unique_content = []
    for item in watched_content:
        if item['IMDB_ID'] not in seen:
            unique_content.append(item)
            seen.add(item['IMDB_ID'])
    return unique_content
    
# Function to remove items with Type 'show'
def remove_shows(watched_content):
    filtered_content = []
    for item in watched_content:
        if item['Type'] != 'show':
            filtered_content.append(item)
    return filtered_content

# Filter out setting review IMDB where the comment length is less than 600 characters
def filter_by_comment_length(lst, min_comment_length=None):
    result = []
    for item in lst:
        if min_comment_length is None or ('Comment' in item and len(item['Comment']) >= min_comment_length):
            result.append(item)
    return result
    

def sort_by_date_added(items, descending=False):
    """
    Sorts a list of items by the 'Date_Added' field.

    Args:
        items (list): A list of dictionaries or objects with a 'Date_Added' field.
        descending (bool): Whether to sort in descending order. Defaults to False (ascending).

    Returns:
        list: A sorted list of items by the 'Date_Added' field.
    """
    def parse_date(item):
        date_str = item.get('Date_Added')  # Safely get the Date_Added field
        if date_str:
            try:
                return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ")
            except ValueError:
                pass  # Invalid date format
        return datetime.min  # Use the earliest date as a fallback

    return sorted(items, key=parse_date, reverse=descending)
    
def check_and_update_watch_history(list):
    """
    Checks if the list has 10,000 or more items.
    If true, updates the sync_watch_history in credentials.txt to False
    and marks the watch history limit as reached.
    
    Args:
        list (list): List of the user's watch history.
    
    Returns:
        bool: True if the watch history limit has been reached, False otherwise.
    """
    # Define the file path for credentials.txt
    here = os.path.abspath(os.path.dirname(__file__))
    file_path = os.path.join(here, 'credentials.txt')
    
    # Load the credentials file
    credentials = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            credentials = json.load(file)
    except FileNotFoundError:
        print("Credentials file not found. A new file will be created if needed.", exc_info=True)
        return False  # Return False if the file doesn't exist

    # Check if list has 10,000 or more items
    if len(list) >= 9999:
        # Update sync_watch_history to False
        credentials['sync_watch_history'] = False
        
        # Mark that the watch history limit has been reached
        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(credentials, file, indent=4, separators=(', ', ': '))
            print("IMDB watch history has reached the 10,000 item limit. sync_watch_history value set to False. Watch history will no longer be synced.")
            return True  # Return True indicating limit reached and updated the credentials
        except Exception as e:
            print("Failed to write to credentials file.", exc_info=True)
            return False  # Return False if there was an error while updating the file

    # Return False if the limit hasn't been reached
    return False