import os
import json
import subprocess
import requests
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
try:
    from IMDbTraktSyncer import checkChromedriver
    from IMDbTraktSyncer import verifyCredentials
    from IMDbTraktSyncer import traktRatings
    from IMDbTraktSyncer import imdbRatings
except:
    import checkChromedriver
    import verifyCredentials
    import traktRatings
    import imdbRatings
from chromedriver_py import binary_path


def main():

    #Get credentials
    trakt_client_id = verifyCredentials.trakt_client_id
    trakt_client_secret = verifyCredentials.trakt_client_secret
    trakt_access_token = verifyCredentials.trakt_access_token
    imdb_username = verifyCredentials.imdb_username
    imdb_password = verifyCredentials.imdb_password
    
    directory = os.path.dirname(os.path.realpath(__file__))
    
    #Start web driver
    print('Starting webdriver')
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3')
    options.add_experimental_option("prefs", {"download.default_directory": directory, "download.directory_upgrade": True, "download.prompt_for_download": False})
    options.add_argument("--disable-save-password-bubble")
    options.add_argument('--disable-notifications')
    options.add_argument("--disable-third-party-cookies")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-extensions")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument('--log-level=3')

    service = Service(executable_path=binary_path)
    driver = webdriver.Chrome(service=service, options=options)

    wait = WebDriverWait(driver, 20)

    driver.get('https://www.imdb.com/registration/signin')

    # wait for sign in link to appear and then click it
    sign_in_link = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.auth-provider-text')))
    if sign_in_link.text == 'Sign in with IMDb':
        sign_in_link.click()

    # wait for email input field and password input field to appear, then enter credentials and submit
    email_input = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "input[type='email']")))[0]
    password_input = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "input[type='password']")))[0]
    email_input.send_keys(imdb_username)
    password_input.send_keys(imdb_password)
    submit_button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='submit']")))
    submit_button.click()

    time.sleep(2)

    # go to IMDb homepage
    driver.get('https://www.imdb.com/')

    time.sleep(2)

    # Check if signed in
    element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".nav__userMenu.navbar__user")))
    if "Sign In" in element.text:
        print("Not signed in")
    else:
        print("Signed in")
    
    trakt_ratings = traktRatings.getTraktRatings(trakt_client_id, trakt_access_token)
    imdb_ratings = imdbRatings.getImdbRatings(imdb_username, imdb_password, driver, directory, wait)
    
    print('Setting IMDB Ratings')
        
    #Get trakt and imdb ratings and filter out trakt ratings wish missing imbd id
    trakt_ratings = [rating for rating in trakt_ratings if rating['ID'] is not None]
    imdb_ratings = [rating for rating in imdb_ratings if rating['ID'] is not None]
    #Filter out ratings already set
    imdb_ratings_to_set = [rating for rating in trakt_ratings if rating['ID'] not in [imdb_rating['ID'] for imdb_rating in imdb_ratings]]
    trakt_ratings_to_set = [rating for rating in imdb_ratings if rating['ID'] not in [trakt_rating['ID'] for trakt_rating in trakt_ratings]]

    # loop through each movie and TV show rating and submit rating on IMDb website
    for i, item in enumerate(imdb_ratings_to_set, 1):
        print(f'Rating {item["Type"]}: ({i} of {len(imdb_ratings_to_set)}) {item["Title"]} ({item["Year"]}): {item["Rating"]}/10 on IMDb')
        driver.get(f'https://www.imdb.com/title/{item["ID"]}/')
        time.sleep(2)

        # click on "Rate" button and select rating option, then submit rating
        buttons = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'button.ipc-btn span')))
        found_rate_button = False
        for button in buttons:
            if "Rate" in button.text:
                driver.execute_script("arguments[0].click();", button)
                rating_option_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, f'button[aria-label="Rate {item["Rating"]}"]')))
                driver.execute_script("arguments[0].click();", rating_option_element)
                submit_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'button.ipc-rating-prompt__rate-button')))
                submit_element.click()
                found_rate_button = True
                break

        if not found_rate_button:
            continue
            
    print('Setting Trakt Ratings')

    # Set the API endpoints
    oauth_url = "https://api.trakt.tv/oauth/token"
    rate_url = "https://api.trakt.tv/sync/ratings"

    # Set the headers
    headers = {
        "Content-Type": "application/json",
        "trakt-api-version": "2",
        "trakt-api-key": trakt_client_id,
        "Authorization": f"Bearer {trakt_access_token}"
    }
    
    # Count the total number of items to rate
    num_items = len(trakt_ratings_to_set)
    item_count = 0
            
    # Loop through your data table and rate each item on Trakt
    for item in trakt_ratings_to_set:
        item_count += 1
        if item["Type"] == "show":
            # This is a TV show
            data = {
                "shows": [{
                    "ids": {
                        "imdb": item["ID"]
                    },
                    "rating": item["Rating"]
                }]
            }
            print(f"Rating TV show ({item_count} of {num_items}): {item['Title']} ({item['Year']}) with rating {item['Rating']}/10 on Trakt")
        elif item["Type"] == "movie":
            # This is a movie
            data = {
                "movies": [{
                    "ids": {
                        "imdb": item["ID"]
                    },
                    "rating": item["Rating"]
                }]
            }
            print(f"Rating movie ({item_count} of {num_items}): {item['Title']} ({item['Year']}) with rating {item['Rating']}/10 on Trakt")

        # Make the API call to rate the item
        response = requests.post(rate_url, headers=headers, json=data)
        time.sleep(1)
        while response.status_code == 429:
            print("Rate limit exceeded. Waiting for 1 second...")
            time.sleep(1)
            response = requests.post(rate_url, headers=headers, json=data)
        if response.status_code != 201:
            print(f"Error rating {item}: {response.content}")

    #Close web driver
    print("Closing webdriver...")
    driver.quit()
    service.stop()

if __name__ == '__main__':
    main()