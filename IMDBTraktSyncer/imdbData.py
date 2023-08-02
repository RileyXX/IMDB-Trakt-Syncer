import os
import time
import csv
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import SessionNotCreatedException
from chromedriver_py import binary_path
try:
    from IMDBTraktSyncer import errorHandling as EH
    from IMDBTraktSyncer import errorLogger as EL
except ImportError:
    import errorHandling as EH
    import errorLogger as EL

class PageLoadException(Exception):
    pass

def getImdbData(imdb_username, imdb_password, driver, directory, wait):
    # Process IMDB Ratings Reviews & Watchlist
    print('Processing IMDB Data')
    
    #Get IMDB Watchlist Items
    try:
        # Load page
        success, status_code, url = EH.get_page_with_retries('https://www.imdb.com/list/watchlist', driver, wait)
        if not success:
            # Page failed to load, raise an exception
            raise PageLoadException(f"Failed to load page. Status code: {status_code}. URL: {url}")

        csv_link = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".export a")))
        driver.execute_script("arguments[0].scrollIntoView(true);", csv_link)
        csv_link.click()

        #Wait for csv download to complete
        time.sleep(8)

        imdb_watchlist = []

        # Read the watchlist items from the CSV file
        here = os.path.abspath(os.path.dirname(__file__))
        watchlist_path = os.path.join(here, 'WATCHLIST.csv')
        try:
            with open(watchlist_path, 'r', encoding='utf-8') as file:
                reader = csv.reader(file)
                header = next(reader)  # skip the header row
                for row in reader:
                    title = row[5]
                    year = row[10]
                    imdb_id = row[1]
                    date_added = row[2]
                    # Convert date format
                    date_added = datetime.strptime(date_added, '%Y-%m-%d').strftime('%Y-%m-%dT%H:%M:%S.000Z')
                    if "tvSeries" in row[7] or "tvMiniSeries" in row[7]:
                        media_type = "show"
                    elif "tvEpisode" in row[7]:
                        media_type = "episode"
                    elif "movie" in row[7] or "tvSpecial" in row[7] or "tvMovie" in row[7] or "tvShort" in row[7] or "video" in row[7]:
                        media_type = "movie"
                    else:
                        media_type = "unknown"
                    imdb_watchlist.append({'Title': title, 'Year': year, 'IMDB_ID': imdb_id, 'Date_Added': date_added, 'Type': media_type})
        except FileNotFoundError:
            error_message = "Ratings file not found"
            print(f"{error_message}")
            EL.logger.error(error_message, exc_info=True)
            
        # Delete csv files
        for file in os.listdir(directory):
            if file.endswith('.csv') and 'WATCHLIST' in file:
                os.remove(os.path.join(directory, file))

    except (NoSuchElementException, TimeoutException):
        # No IMDB Watchlist Items
        imdb_watchlist = []
        pass
    
    # Get IMDB Ratings
    try:
        # Load page
        success, status_code, url = EH.get_page_with_retries('https://www.imdb.com/list/ratings', driver, wait)
        if not success:
            # Page failed to load, raise an exception
            raise PageLoadException(f"Failed to load page. Status code: {status_code}. URL: {url}")

        dropdown = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".circle")))
        dropdown.click()

        csv_link = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".pop-up-menu-list-items a.pop-up-menu-list-item-link")))
        csv_link.click()

        #Wait for csv download to complete
        time.sleep(8)

        imdb_ratings = []

        # Read the ratings from the CSV file
        here = os.path.abspath(os.path.dirname(__file__))
        ratings_path = os.path.join(here, 'ratings.csv')
        try:
            with open(ratings_path, 'r', encoding='utf-8') as file:
                reader = csv.reader(file)
                header = next(reader)  # skip the header row
                for row in reader:
                    title = row[3]
                    year = row[8]
                    rating = row[1]
                    imdb_id = row[0]
                    date_added = row[2]
                    # Convert date format
                    date_added = datetime.strptime(date_added, '%Y-%m-%d').strftime('%Y-%m-%dT%H:%M:%S.000Z')
                    if "tvSeries" in row[5] or "tvMiniSeries" in row[5]:
                        media_type = "show"
                    elif "tvEpisode" in row[5]:
                        media_type = "episode"
                    elif "movie" in row[5] or "tvSpecial" in row[5] or "tvMovie" in row[5] or "tvShort" in row[5] or "video" in row[5]:
                        media_type = "movie"
                    else:
                        media_type = "unknown"
                    imdb_ratings.append({'Title': title, 'Year': year, 'Rating': int(rating), 'IMDB_ID': imdb_id, 'Date_Added': date_added, 'Type': media_type})
        except FileNotFoundError:
            print('Ratings file not found')
            
        # Delete csv files
        for file in os.listdir(directory):
            if file.endswith('.csv') and 'ratings' in file:
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
        reviews_link = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div.aux-content-widget-2 div.subNavItem a[href*='comments-index']")))
        reviews_link.click()

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