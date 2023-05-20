import os
import time
import csv
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from chromedriver_py import binary_path
try:
    from IMDBTraktSyncer import verifyCredentials
except:
    import verifyCredentials

def getImdbData(imdb_username, imdb_password, driver, directory, wait):
    # Process IMDB Ratings and Reviews
    print('Processing IMDB Ratings and Reviews')

    driver.get('https://www.imdb.com/list/ratings')

    dropdown = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".circle")))
    dropdown.click()

    csv_link = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".pop-up-menu-list-items a.pop-up-menu-list-item-link")))
    csv_link.click()

    #Wait for csv download to complete
    time.sleep(8)

    imdb_ratings = []

    # Read the ratings from the CSV file
    here = os.path.abspath(os.path.dirname(__file__))
    ratings_path = os.path.join(here, 'ratings.csv')
    try:
        with open(ratings_path, 'r') as file:
            reader = csv.reader(file)
            header = next(reader)  # skip the header row
            for row in reader:
                title = row[3]
                year = row[8]
                rating = row[1]
                imdb_id = row[0]
                if "tvSeries" in row[5] or "tvMiniSeries" in row[5]:
                    type = "show"
                elif "tvEpisode" in row[5]:
                    type = "episode"
                elif "movie" in row[5]:
                    type = "movie"
                else:
                    type = "unknown"
                imdb_ratings.append({'Title': title, 'Year': year, 'Rating': rating, 'ID': imdb_id, 'Type': type})
    except FileNotFoundError:
        print('Ratings file not found')
        
    # Delete csv files
    for file in os.listdir(directory):
        if file.endswith('.csv') and 'ratings' in file:
            os.remove(os.path.join(directory, file))

    #Get IMDB Reviews
    driver.get('https://www.imdb.com/profile')
    reviews_link = driver.find_element(By.CSS_SELECTOR, "div.aux-content-widget-2 div.subNavItem a[href*='comments-index']")
    reviews_link.click()
    
    def get_media_type(imdb_id):
        url = f"https://api.trakt.tv/search/imdb/{imdb_id}"
        headers = {
            "Content-Type": "application/json",
            "trakt-api-version": "2",
            "trakt-api-key": verifyCredentials.trakt_client_id
        }
        
        response = requests.get(url, headers=headers)
        while response.status_code == 429:
            time.sleep(1)
            response = requests.get(url, headers=headers)
        if response.status_code == 200:
            results = response.json()
            if results:
                media_type = results[0]['type']
                return media_type
        return None

    reviews = []

    while True:
        try:
            review_elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".imdb-user-review")))
            if not review_elements:
                break  # No review elements found, exit the loop
            
            for element in review_elements:
                review = {}
                # Extract review details
                review['Title'] = element.find_element(By.CSS_SELECTOR, ".lister-item-header a").text
                review['Year'] = element.find_element(By.CSS_SELECTOR, ".lister-item-header span").text.strip('()').split('–')[0].strip()
                review['ID'] = element.find_element(By.CSS_SELECTOR, ".lister-item-header a").get_attribute("href").split('/')[4]
                review['IMDBReviewID'] = element.get_attribute("data-review-id")
                review['Comment'] = element.find_element(By.CSS_SELECTOR, ".content > .text").text.strip()
                spoiler_warning_elements = element.find_elements(By.CSS_SELECTOR, ".spoiler-warning")
                review['Spoiler'] = len(spoiler_warning_elements) > 0
                # Get the media type using Trakt API
                media_type = get_media_type(review['ID'])
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

                next_link.click()

                # Wait until the URL changes
                wait.until(EC.url_changes(current_url))
                
                # Refresh review_elements
                review_elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".imdb-user-review")))

            except (NoSuchElementException, TimeoutException):
                break  # "Next" link not found or timed out waiting for the 'Next' link, exit the loop
        except Exception as e:
            print(f"Exception occurred: {e}")
            break

    imdb_reviews = reviews

    print('Processing IMDB Ratings and Reviews Complete')
    
    return imdb_ratings, imdb_reviews