import os
import time
import csv
import requests
import traceback
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import SessionNotCreatedException
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from IMDBTraktSyncer import errorHandling as EH
from IMDBTraktSyncer import errorLogger as EL

class PageLoadException(Exception):
    pass

def generate_imdb_exports(driver, wait, directory, sync_watchlist_value, sync_ratings_value, sync_watch_history_value, remove_watched_from_watchlists_value, mark_rated_as_watched_value):
    # Generate IMDB .csv exports
  
    # Generate watchlist export if sync_watchlist_value is True
    if sync_watchlist_value or remove_watched_from_watchlists_value:
        success, status_code, url, driver, wait = EH.get_page_with_retries('https://www.imdb.com/list/watchlist', driver, wait)
        if not success:
            # Page failed to load, raise an exception
            raise PageLoadException(f"Failed to load page. Status code: {status_code}. URL: {url}")

        export_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div[data-testid*='hero-list-subnav-export-button'] button")))
        export_button.click()
        time.sleep(3)
    
    # Generate ratings export if sync_ratings_value is True
    if sync_ratings_value or mark_rated_as_watched_value:
        success, status_code, url, driver, wait = EH.get_page_with_retries('https://www.imdb.com/list/ratings', driver, wait)
        if not success:
            # Page failed to load, raise an exception
            raise PageLoadException(f"Failed to load page. Status code: {status_code}. URL: {url}")

        export_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div[data-testid*='hero-list-subnav-export-button'] button")))
        export_button.click()
        time.sleep(3)
    
    # Generate checkins export if sync_watch_history_value is True
    if sync_watch_history_value or remove_watched_from_watchlists_value or mark_rated_as_watched_value:
        success, status_code, url, driver, wait = EH.get_page_with_retries('https://www.imdb.com/list/checkins', driver, wait)
        if not success:
            # Page failed to load, raise an exception
            raise PageLoadException(f"Failed to load page. Status code: {status_code}. URL: {url}")

        export_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div[data-testid*='hero-list-subnav-export-button'] button")))
        export_button.click()
        time.sleep(3)
    
    # Wait for export processing to finish
    # Function to check if any summary item contains "in progress"
    def check_in_progress(summary_items):
        for item in summary_items:
            if "in progress" in item.text.lower():
                return True
        return False
    # Maximum time to wait in seconds
    max_wait_time = 1200
    start_time = time.time()

    while time.time() - start_time < max_wait_time:
        # Wait for export processing to finish
        success, status_code, url, driver, wait = EH.get_page_with_retries('https://www.imdb.com/exports/', driver, wait)
        if not success:
            # Page failed to load, raise an exception
            raise PageLoadException(f"Failed to load page. Status code: {status_code}. URL: {url}")
        
        # Locate all elements with the selector
        summary_items = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".ipc-metadata-list-summary-item")))

        # Check if any summary item contains "in progress"
        if not check_in_progress(summary_items):
            #print("No 'in progress' found. Proceeding.")
            break
        else:
            #print("'In progress' found. Waiting for 30 seconds before retrying.")
            time.sleep(30)
    else:
        raise TimeoutError("IMDB data processing did not complete within the allotted 20 minutes.")
    
    return driver, wait
    
def grant_permissions_and_rename_file(src_path, dest_name):
    """
    Grant full permissions to the file and rename it to the given name.
    :param src_path: Path to the downloaded file.
    :param dest_name: New name for the file (e.g., 'ratings.csv').
    """
    try:
        # Grant full permissions
        os.chmod(src_path, 0o777)
        
        # Rename the file
        dest_path = os.path.join(os.path.dirname(src_path), dest_name)
        os.rename(src_path, dest_path)
    except Exception as e:
        print(f"Error while renaming file {src_path} to {dest_name}: {e}")
        
def download_imdb_exports(driver, wait, directory, sync_watchlist_value, sync_ratings_value, sync_watch_history_value, remove_watched_from_watchlists_value, mark_rated_as_watched_value):
    """
    Download IMDB Exports and rename files with correct permissions.
    """
    # Load page
    success, status_code, url, driver, wait = EH.get_page_with_retries('https://www.imdb.com/exports/', driver, wait)
    if not success:
        # Page failed to load, raise an exception
        raise PageLoadException(f"Failed to load page. Status code: {status_code}. URL: {url}")

    # Locate all elements with the selector
    summary_items = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".ipc-metadata-list-summary-item")))

    # Helper function to find buttons for CSV downloads
    def find_button(item_text):
        for item in summary_items:
            if item_text.lower() in item.text.lower():
                button = item.find_element(By.CSS_SELECTOR, "button[data-testid*='export-status-button']")
                if button:
                    return button
        return None

    # Find download buttons
    watchlist_csv_link = find_button("watchlist") if sync_watchlist_value or remove_watched_from_watchlists_value else None
    ratings_csv_link = find_button("ratings") if sync_ratings_value or mark_rated_as_watched_value else None
    checkins_csv_link = find_button("check-ins") if sync_watch_history_value or remove_watched_from_watchlists_value or mark_rated_as_watched_value else None

    # Clear any previous csv files
    for file in os.listdir(directory):
        if file.endswith('.csv'):
            os.remove(os.path.join(directory, file))

    # Download each file and rename accordingly
    file_mappings = [
        (watchlist_csv_link, "watchlist.csv"),
        (ratings_csv_link, "ratings.csv"),
        (checkins_csv_link, "checkins.csv")
    ]
    
    for csv_link, file_name in file_mappings:
        if csv_link:
            # Scroll into view and click the button
            driver.execute_script("arguments[0].scrollIntoView(true);", csv_link)
            wait.until(EC.visibility_of(csv_link))
            driver.execute_script("arguments[0].click();", csv_link)
            
            # Wait for download to complete
            time.sleep(10)

            # Find the most recent file in the directory
            downloaded_files = sorted(
                [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith('.csv')],
                key=os.path.getmtime,
                reverse=True
            )
            if downloaded_files:
                grant_permissions_and_rename_file(downloaded_files[0], file_name)
            else:
                print(f"Unable to locate downloaded file for {file_name}")

    return driver, wait

def get_imdb_watchlist(driver, wait, directory):
    # Get IMDB Watchlist Items
    imdb_watchlist = []
    try:          
        # Look for 'watchlist.csv'
        watchlist_filename = 'watchlist.csv'
        watchlist_path = os.path.join(directory, watchlist_filename)

        if not os.path.exists(watchlist_path):
            raise FileNotFoundError(f"IMDB watchlist data not found. '{watchlist_filename}' not found in the directory")
        
        # Open and process the 'watchlist.csv' file
        with open(watchlist_path, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            header = next(reader)  # Read the header row

            # Create a mapping from header names to their index
            header_index = {column_name: index for index, column_name in enumerate(header)}
            
            required_columns = ["Title", "Year", "Const", "Created", "Title Type"]
            missing_columns = [col for col in required_columns if col not in header_index]
            if missing_columns:
                raise ValueError(f"Required columns missing from CSV file: {', '.join(missing_columns)}")

            for row in reader:
                title = row[header_index['Title']]
                year = row[header_index['Year']]
                year = int(year) if year else None
                imdb_id = row[header_index['Const']]
                date_added = row[header_index['Created']]
                media_type = row[header_index['Title Type']]
                # Convert date format
                date_added = datetime.strptime(date_added, '%Y-%m-%d').strftime('%Y-%m-%dT%H:%M:%S.000Z')
                if media_type in ["TV Series", "TV Mini Series"]:
                    media_type = "show"
                elif media_type == "TV Episode":
                    media_type = "episode"
                elif media_type in ["Movie", "TV Special", "TV Movie", "TV Short", "Video"]:
                    media_type = "movie"
                else:
                    media_type = "unknown"

                if media_type != "unknown":
                    imdb_watchlist.append({
                        'Title': title,
                        'Year': year,
                        'IMDB_ID': imdb_id,
                        'Date_Added': date_added,
                        'Type': media_type
                    })
    
        # Delete 'watchlist.csv'
        if os.path.exists(watchlist_path):
            os.remove(watchlist_path)
        
    except FileNotFoundError as e:
        error_message = str(e)
        print(f"Error: {error_message}")
        traceback.print_exc()
        EL.logger.error(error_message, exc_info=True)
    
    except (NoSuchElementException, TimeoutException):
        # No IMDB Watchlist Items
        imdb_watchlist = []
        pass
    
    return imdb_watchlist, driver, wait

def get_imdb_ratings(driver, wait, directory):
    # Get IMDB Ratings
    imdb_ratings = []
    try:
        # Look for 'ratings.csv'
        ratings_filename = 'ratings.csv'
        ratings_path = os.path.join(directory, ratings_filename)

        if not os.path.exists(ratings_path):
            raise FileNotFoundError(f"IMDB ratings data not found. '{ratings_filename}' not found in the directory")
        
        # Open and process the 'ratings.csv' file
        with open(ratings_path, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            header = next(reader)  # Read the header row

            # Create a mapping from header names to their index
            header_index = {column: index for index, column in enumerate(header)}
            
            required_columns = ["Title", "Year", "Your Rating", "Const", "Date Rated", "Title Type"]
            missing_columns = [col for col in required_columns if col not in header_index]
            if missing_columns:
                raise ValueError(f"Required columns missing from CSV file: {', '.join(missing_columns)}")

            for row in reader:
                title = row[header_index['Title']]
                year = row[header_index['Year']]
                year = int(year) if year else None
                rating = row[header_index['Your Rating']]
                imdb_id = row[header_index['Const']]
                date_added = row[header_index['Date Rated']]
                watched_at = row[header_index['Date Rated']]
                media_type = row[header_index['Title Type']]
                # Convert date format
                date_added = datetime.strptime(date_added, '%Y-%m-%d').strftime('%Y-%m-%dT%H:%M:%S.000Z')
                if media_type == "TV Series" or media_type == "TV Mini Series":
                    media_type = "show"
                elif media_type == "TV Episode":
                    media_type = "episode"
                elif media_type in ["Movie", "TV Special", "TV Movie", "TV Short", "Video"]:
                    media_type = "movie"
                else:
                    media_type = "unknown"
                
                # Append to the list
                if media_type != "unknown":
                    imdb_ratings.append({
                        'Title': title,
                        'Year': year,
                        'Rating': int(rating),
                        'IMDB_ID': imdb_id,
                        'Date_Added': date_added,
                        'WatchedAt': date_added,
                        'Type': media_type
                    })
        
        # Delete 'ratings.csv'
        if os.path.exists(ratings_path):
            os.remove(ratings_path)
        
    except FileNotFoundError as e:
        error_message = str(e)
        print(f"Error: {error_message}")
        traceback.print_exc()
        EL.logger.error(error_message, exc_info=True)
    
    except (NoSuchElementException, TimeoutException):
        # No IMDB Ratings Items
        imdb_ratings = []
        pass
    
    return imdb_ratings, driver, wait
    
def get_imdb_checkins(driver, wait, directory):
    # Get IMDB Check-ins
    imdb_checkins = []
    try:
        # Look for 'checkins.csv'
        checkins_filename = 'checkins.csv'
        checkins_path = os.path.join(directory, checkins_filename)

        if not os.path.exists(checkins_path):
            raise FileNotFoundError(f"IMDB Check-ins data not found. '{checkins_filename}' not found in the directory")
        
        # Open and process the 'checkins.csv' file
        with open(checkins_path, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            header = next(reader)  # Read the header row

            # Create a mapping from header names to their index
            header_index = {column: index for index, column in enumerate(header)}
            
            required_columns = ["Title", "Year", "Const", "Created", "Title Type"]
            missing_columns = [col for col in required_columns if col not in header_index]
            if missing_columns:
                raise ValueError(f"Required columns missing from CSV file: {', '.join(missing_columns)}")

            for row in reader:
                title = row[header_index['Title']]
                year = row[header_index['Year']]
                year = int(year) if year else None
                imdb_id = row[header_index['Const']]
                date_added = row[header_index['Created']]
                media_type = row[header_index['Title Type']]
                # Convert date format
                date_added = datetime.strptime(date_added, '%Y-%m-%d').strftime('%Y-%m-%dT%H:%M:%S.000Z')
                if media_type in ["TV Series", "TV Mini Series"]:
                    media_type = "show"
                elif media_type == "TV Episode":
                    media_type = "episode"
                elif media_type in ["Movie", "TV Special", "TV Movie", "TV Short", "Video"]:
                    media_type = "movie"
                else:
                    media_type = "unknown"

                if media_type != "unknown":
                    imdb_checkins.append({
                        'Title': title,
                        'Year': year,
                        'IMDB_ID': imdb_id,
                        'Date_Added': date_added,
                        'WatchedAt': date_added,
                        'Type': media_type
                    })
                        
        # Delete 'checkins.csv'
        if os.path.exists(checkins_path):
            os.remove(checkins_path)
        
    except FileNotFoundError as e:
        error_message = str(e)
        print(f"Error: {error_message}")
        traceback.print_exc()
        EL.logger.error(error_message, exc_info=True)
    
    except (NoSuchElementException, TimeoutException):
        # No IMDB Check-in Items
        imdb_checkins = []
        pass
    
    return imdb_checkins, driver, wait
            
def get_media_type(imdb_id):
    url = f"https://api.trakt.tv/search/imdb/{imdb_id}"
    response = EH.make_trakt_request(url)
    if response:
        results = response.json()
        if results:
            media_type = results[0].get('type')
            return media_type
    return None

def get_imdb_reviews(driver, wait, directory):
    #Get IMDB Reviews
    
    # Load page
    success, status_code, url, driver, wait = EH.get_page_with_retries('https://www.imdb.com/profile', driver, wait)
    if not success:
        # Page failed to load, raise an exception
        raise PageLoadException(f"Failed to load page. Status code: {status_code}. URL: {url}")
    
    reviews = []
    errors_found_getting_imdb_reviews = False
    try:
        # Wait until the current page URL contains the string "user/"
        wait.until(lambda driver: "user/" in driver.current_url)
        
        # Copy the full URL to a variable and append reviews to it
        reviews_url = driver.current_url + "reviews/"
        
        # Load page
        success, status_code, url, driver, wait = EH.get_page_with_retries(reviews_url, driver, wait)
        if not success:
            # Page failed to load, raise an exception
            raise PageLoadException(f"Failed to load page. Status code: {status_code}. URL: {url}")
            
        while True:
            try:
                try:
                    review_elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".imdb-user-review")))
                except (NoSuchElementException, TimeoutException):
                    # No review elements found. There are no reviews. Exit the loop without an error.
                    error_message = "No review elements found. There are no reviews. Exit the loop without an error."
                    EL.logger.error(error_message, exc_info=True)
                    break
                
                for element in review_elements:
                    review = {}
                    # Extract review details
                    review['Title'] = element.find_element(By.CSS_SELECTOR, ".lister-item-header a").text
                    review['Year'] = element.find_element(By.CSS_SELECTOR, ".lister-item-header span").text.strip('()').split('–')[0].strip()
                    review['Year'] = int(review['Year']) if review['Year'] else None
                    review['IMDB_ID'] = element.find_element(By.CSS_SELECTOR, ".lister-item-header a").get_attribute("href").split('/')[4]
                    review['IMDBReviewID'] = element.get_attribute("data-review-id")
                    review['Comment'] = element.find_element(By.CSS_SELECTOR, ".content > .text").text.strip()
                    spoiler_warning_elements = element.find_elements(By.CSS_SELECTOR, ".spoiler-warning")
                    review['Spoiler'] = len(spoiler_warning_elements) > 0
                    # Get the media type using Trakt API
                    media_type = get_media_type(review['IMDB_ID'])
                    if media_type:
                        review['Type'] = media_type
                    else:
                        review['Type'] = 'unknown'

                    if review['Type'] != 'unknown':
                        reviews.append(review)

                try:
                    # Check if "Next" link exists
                    next_link = driver.find_element(By.CSS_SELECTOR, "a.next-page")
                    if next_link.get_attribute("href") == "#":
                        break  # No more pages, exit the loop
                    
                    # Get the current url before clicking the "Next" link
                    current_url = driver.current_url
                    
                    # Click the "Next" link
                    next_link.click()

                    # Wait until the URL changes
                    wait.until(lambda driver: driver.current_url != current_url)
                    
                    # Refresh review_elements
                    review_elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".imdb-user-review")))

                except NoSuchElementException:
                    # "Next" link not found on IMDB reviews page, exit the loop without error
                    error_message = '"Next" link not found on IMDB reviews page. Exiting the loop without error.'
                    EL.logger.warning(error_message, exc_info=True)
                    break
                except TimeoutException:
                    # Timed out waiting for URL change or next page review elements on IMDB reviews page
                    error_message = 'Timed out waiting for URL change or next page review elements on IMDB reviews page. Exiting the loop without error.'
                    EL.logger.error(error_message, exc_info=True)
                    break
            except Exception as e:
                errors_found_getting_imdb_reviews = True
                error_message = f"Exception occurred while getting IMDB reviews: {type(e)}"
                print(f"{error_message}")
                EL.logger.error(error_message, exc_info=True)
                break
    
    except Exception as e:
        errors_found_getting_imdb_reviews = True
        error_message = f"Exception occurred while getting IMDB reviews: {type(e)}"
        print(f"{error_message}")
        traceback.print_exc()
        EL.logger.error(error_message, exc_info=True)

    # Filter out duplicate reviews for the same item based on ID
    filtered_reviews = []
    seen = set()
    for item in reviews:
        if item['IMDB_ID'] not in seen:
            seen.add(item['IMDB_ID'])
            filtered_reviews.append(item)
    imdb_reviews = filtered_reviews
    
    return imdb_reviews, errors_found_getting_imdb_reviews, driver, wait