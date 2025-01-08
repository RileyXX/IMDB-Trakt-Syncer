import traceback
import requests
from requests.exceptions import ConnectionError, RequestException, Timeout, TooManyRedirects, SSLError, ProxyError
import time
import os
import inspect
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
                if response:
                    status_message = get_trakt_message(response.status_code)
                    error_message = f"Request failed with status code {response.status_code}: {status_message}"
                    print(f"   - {error_message}")
                    EL.logger.error(f"{error_message}. URL: {url}")
                else:
                    # Handle case where response is None
                    error_message = "Request failed with an unknown error: Response object is None."
                    print(f"   - {error_message}")
                    EL.logger.error(f"{error_message}. URL: {url}")
                    
                    # Instead of returning None, treat this as a retryable error
                    retry_attempts += 1
                    remaining_time = total_wait_time - sum(retry_delay * (2 ** i) for i in range(retry_attempts))
                    print(f"   - Retrying due to network error or no response. ({retry_attempts}/{max_retries})... "
                          f"Time remaining: {remaining_time}s")
                    EL.logger.warning(f"Retrying due to network error or no response. ({retry_attempts}/{max_retries})... "
                                      f"Time remaining: {remaining_time}s")
                    
                    time.sleep(retry_delay)  # Wait before retrying
                    retry_delay *= 2  # Apply exponential backoff for retries

                    continue  # Continue to retry

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
    was_retry = False  # Flag to track if a retry occurred
    total_time_spent = 0  # Track total time spent across retries

    for retry in range(max_retries):
        try:
            start_time = time.time()  # Track time taken for each retry attempt
            
            # Temporary solution to Chromium bug: 
            # Open a new tab for the URL
            driver.execute_script("window.open();")
            # Close the current tab
            driver.close()
            # Switch to the new tab (last opened tab)
            driver.switch_to.window(driver.window_handles[0])

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
            
            # Check for any error codes or if status_code is None
            if status_code is None or status_code == 0:
                print(f"   - Unable to determine page load status. Status code returned 0 or None. Possible network or server error. URL: {url} Retrying...")
                elapsed_time = time.time() - start_time  # Time taken for this attempt
                total_time_spent += elapsed_time  # Update total time spent
                
                # Calculate the remaining time before the next retry
                seconds_left = int((total_wait_time - total_time_spent) - (retry * wait_time))
                print(f"   - Remaining time for retries: {seconds_left} seconds.")
                
                was_retry = True  # Set flag to indicate a retry occurred
                continue  # Retry immediately if status_code is None or 0
            elif status_code >= 400:
                raise PageLoadException(f'Failed to load page. Status code: {status_code}. URL: {url}')
            else:
                if was_retry:
                    print("   - Retry successful! Continuing...")
                    was_retry = False  # Reset flag
                return True, status_code, url  # Page loaded successfully

        except TimeoutException as e:
            # Handle page load timeout explicitly
            frame = inspect.currentframe()  # Get the current frame
            lineno = frame.f_lineno  # Get the line number where the exception occurred
            filename = os.path.basename(inspect.getfile(frame))  # Get only the file name where the exception occurred
            print(f"   - TimeoutException: Page load timed out. Retrying... {str(e).splitlines()[0]} URL: {url} (File: {filename}, Line: {lineno})")
            elapsed_time = time.time() - start_time  # Time taken for this attempt
            
            # Update total time spent
            total_time_spent += elapsed_time
            
            if retry + 1 < max_retries:
                seconds_left = int((total_wait_time - total_time_spent))
                print(f"   - Retrying ({retry + 1}/{max_retries}) Time Remaining: {seconds_left}s")
                time.sleep(wait_time)
                was_retry = True  # Set flag to indicate a retry occurred
                continue
            else:
                print("   - Max retries reached or not retrying after timeout.")
                return False, status_code, url

        except WebDriverException as e:
            # Handle Selenium-related network errors
            frame = inspect.currentframe()  # Get the current frame
            lineno = frame.f_lineno  # Get the line number where the exception occurred
            filename = os.path.basename(inspect.getfile(frame))  # Get only the file name where the exception occurred
            print(f"   - Selenium WebDriver Error: {str(e).splitlines()[0]} URL: {url} (File: {filename}, Line: {lineno})")

            # Check for retryable errors
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
                # Calculate the time remaining before the next retry
                seconds_left = int((total_wait_time - total_time_spent) - (retry * wait_time))
                print(f"   - Retryable network error detected: {str(e).splitlines()[0]} Retrying... Time Remaining: {seconds_left}s")
            elif retry + 1 < max_retries:
                seconds_left = int((max_retries - retry) * wait_time)
                print(f"   - Retrying ({retry + 1}/{max_retries}) Time Remaining: {seconds_left}s")
                time.sleep(wait_time)
                was_retry = True  # Set flag to indicate a retry occurred
                continue
            else:
                print("   - Max retries reached or not retrying.")
                return False, status_code, url

        except PageLoadException as e:
            frame = inspect.currentframe()  # Get the current frame
            lineno = frame.f_lineno  # Get the line number where the exception occurred
            filename = os.path.basename(inspect.getfile(frame))  # Get only the file name where the exception occurred
            print(f"   - Error: {str(e).splitlines()[0]} URL: {url} (File: {filename}, Line: {lineno})")
            retryable_error_codes = [408, 425, 429, 500, 502, 503, 504]
            if retry + 1 < max_retries and status_code in retryable_error_codes:
                # Calculate the time remaining before the next retry
                seconds_left = int((total_wait_time - total_time_spent) - (retry * wait_time))
                print(f"   - Retryable PageLoadException error detected: {str(e).splitlines()[0]} Retrying... Time Remaining: {seconds_left}s")
                time.sleep(wait_time)
                was_retry = True  # Set flag to indicate a retry occurred
                continue
            else:
                print("   - Max retries reached. PageLoadException.")
                return False, status_code, url

    # All retries failed and page was not loaded successfully, return False
    return False, None, url
    
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