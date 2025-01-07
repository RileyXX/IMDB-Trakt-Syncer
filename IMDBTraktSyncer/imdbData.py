import os
import time
import csv
import requests
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

def getImdbData(imdb_username, imdb_password, driver, directory, wait):
    # Process IMDB Ratings Reviews & Watchlist
    print('Processing IMDB Data')
    
    
    # Generate watchlist export
    success, status_code, url = EH.get_page_with_retries('https://www.imdb.com/list/watchlist', driver, wait)
    if not success:
        # Page failed to load, raise an exception
        raise PageLoadException(f"Failed to load page. Status code: {status_code}. URL: {url}")

    export_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div[data-testid*='hero-list-subnav-export-button'] button")))
    export_button.click()
    time.sleep(3)
    
    # Generate ratings export
    success, status_code, url = EH.get_page_with_retries('https://www.imdb.com/list/ratings', driver, wait)
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
        success, status_code, url = EH.get_page_with_retries('https://www.imdb.com/exports/', driver, wait)
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
    
    #Get IMDB Watchlist Items
    try:
        # Load page
        success, status_code, url = EH.get_page_with_retries('https://www.imdb.com/exports/', driver, wait)
        if not success:
            # Page failed to load, raise an exception
            raise PageLoadException(f"Failed to load page. Status code: {status_code}. URL: {url}")

        # Locate all elements with the selector
        summary_items = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".ipc-metadata-list-summary-item")))

        # Iterate through the located elements to find the one containing the text "watchlist"
        csv_link = None
        for item in summary_items:
            if "watchlist" in item.text.lower():
                # Try to find the button inside this item
                button = item.find_element(By.CSS_SELECTOR, "button[data-testid*='export-status-button']")
                if button:
                    csv_link = button
                    break
        
        # Clear any previous csv files
        for file in os.listdir(directory):
            if file.endswith('.csv'):
                os.remove(os.path.join(directory, file))

        # Check if the csv_link was found and then perform the actions
        if csv_link:
            driver.execute_script("arguments[0].scrollIntoView(true);", csv_link)
            wait.until(EC.visibility_of(csv_link))
            driver.execute_script("arguments[0].click();", csv_link)
        else:
            print("Unable to fetch IMDB watchlist data.")

        #Wait for csv download to complete
        time.sleep(8)

        imdb_watchlist = []

        here = os.path.abspath(os.path.dirname(__file__))
        here = directory
        
        try:          
            # Find any CSV file in the directory
            csv_files = [f for f in os.listdir(directory) if f.endswith('.csv')]
            if not csv_files:
                raise FileNotFoundError("Watchlist data not found. No CSV files found in the directory")
            
            # Use the first CSV file found 
            watchlist_path = os.path.join(directory, csv_files[0])
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
            
        except FileNotFoundError as e:
            print(f"Error: {error_message}", exc_info=True)
            EL.logger.error(error_message, exc_info=True)

        # Delete csv files
        for file in os.listdir(directory):
            if file.endswith('.csv'):
                os.remove(os.path.join(directory, file))
        
    except (NoSuchElementException, TimeoutException):
        # No IMDB Watchlist Items
        imdb_watchlist = []
        pass
    
    # Get IMDB Ratings
    try:
        # Load page
        success, status_code, url = EH.get_page_with_retries('https://www.imdb.com/exports/', driver, wait)
        if not success:
            # Page failed to load, raise an exception
            raise PageLoadException(f"Failed to load page. Status code: {status_code}. URL: {url}")
        
        # Locate all elements with the selector
        summary_items = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".ipc-metadata-list-summary-item")))

        # Iterate through the located elements to find the one containing the text "ratings"
        csv_link = None
        for item in summary_items:
            if "ratings" in item.text.lower():
                # Try to find the button inside this item
                button = item.find_element(By.CSS_SELECTOR, "button[data-testid*='export-status-button']")
                if button:
                    csv_link = button
                    break
        
        # Clear any previous csv files
        for file in os.listdir(directory):
            if file.endswith('.csv'):
                os.remove(os.path.join(directory, file))

        # Check if the csv_link was found and then perform the actions
        if csv_link:
            driver.execute_script("arguments[0].scrollIntoView(true);", csv_link)
            wait.until(EC.visibility_of(csv_link))
            driver.execute_script("arguments[0].click();", csv_link)
        else:
            print("Unable to fetch IMDB ratings data.")

        #Wait for csv download to complete
        time.sleep(8)

        imdb_ratings = []

        here = os.path.abspath(os.path.dirname(__file__))
        directory = here

        try:          
            # Find any CSV file in the directory
            csv_files = [f for f in os.listdir(directory) if f.endswith('.csv')]
            if not csv_files:
                raise FileNotFoundError("Ratings data not found. No CSV files found in the directory")
                
            # Use the first CSV file found 
            ratings_path = os.path.join(directory, csv_files[0])
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
                        rating = row[header_index['Your Rating']]
                        imdb_id = row[header_index['Const']]
                        date_added = row[header_index['Date Rated']]
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
                                'Type': media_type
                            })
                        
        except FileNotFoundError:
            print(f"Error: {error_message}", exc_info=True)
            EL.logger.error(error_message, exc_info=True)
        
        # Delete csv files
        for file in os.listdir(directory):
            if file.endswith('.csv'):
                os.remove(os.path.join(directory, file))

    except (NoSuchElementException, TimeoutException):
        # No IMDB Ratings
        imdb_ratings = []
        error_message = "No IMDB Ratings"
        EL.logger.error(error_message, exc_info=True)
        pass
            
    def get_media_type(imdb_id):
        url = f"https://api.trakt.tv/search/imdb/{imdb_id}"
        response = EH.make_trakt_request(url)
        if response:
            results = response.json()
            if results:
                media_type = results[0].get('type')
                return media_type
        return None

    #Get IMDB Reviews
    
    # Load page
    success, status_code, url = EH.get_page_with_retries('https://www.imdb.com/profile', driver, wait)
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
        success, status_code, url = EH.get_page_with_retries(reviews_url, driver, wait)
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
        EL.logger.error(error_message, exc_info=True)

    # Filter out duplicate reviews for the same item based on ID
    filtered_reviews = []
    seen = set()
    for item in reviews:
        if item['IMDB_ID'] not in seen:
            seen.add(item['IMDB_ID'])
            filtered_reviews.append(item)
    imdb_reviews = filtered_reviews

    print('Processing IMDB Data Complete')
    
    return imdb_watchlist, imdb_ratings, imdb_reviews, errors_found_getting_imdb_reviews