import os
import json
import subprocess
import requests
import time
from . import checkChromedriver
from . import verifyCredentials
from . import traktRatings
from . import imdbRatings
from chromedriver_py import binary_path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def main():

    here = os.path.abspath(os.path.dirname(__file__))
    file_path = os.path.join(here, 'credentials.txt')
    with open(file_path, "r") as f:
        lines = f.readlines()
    values = {}
    for line in lines:
        key, value = line.strip().split("=")
        values[key] = value
    trakt_client_id = values["trakt_client_id"]
    trakt_client_secret = values["trakt_client_secret"]
    trakt_access_token = values["trakt_access_token"]
    imdb_username = values["imdb_username"]
    imdb_password = values["imdb_password"]

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument('--disable-notifications')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3')

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
        
    print('Setting IMDB Ratings')
        
    trakt_ratings = traktRatings.trakt_ratings
    imdb_ratings = imdbRatings.imdb_ratings
    imdb_ratings_to_set = [rating for rating in trakt_ratings if rating['ID'] not in [imdb_rating['ID'] for imdb_rating in imdb_ratings]]
    trakt_ratings_to_set = [rating for rating in imdb_ratings if rating['ID'] not in [trakt_rating['ID'] for trakt_rating in trakt_ratings]]

    # loop through each movie and TV show rating and submit rating on IMDb website
    for item in imdb_ratings_to_set:
        print(f'{item["Title"]} ({item["Year"]}): {item["Rating"]}/10 (IMDb ID: {item["ID"]})')
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
            
    # Loop through your data table and rate each item on Trakt
    for item in trakt_ratings_to_set:
        if "ID" in item:
            # This is a TV show
            data = {
                "shows": [{
                    "ids": {
                        "imdb": item["ID"]
                    },
                    "rating": item["Rating"]
                }]
            }
            print(f"Rating TV show {item['Title']} ({item['Year']}) with rating {item['Rating']} on Trakt")
        else:
            # This is a movie
            data = {
                "movies": [{
                    "ids": {
                        "imdb": item["ID"]
                    },
                    "rating": item["Rating"]
                }]
            }
            print(f"Rating movie {item['Title']} ({item['Year']}) with rating {item['Rating']} on Trakt")

        # Make the API call to rate the item
        response = requests.post(rate_url, headers=headers, json=data)
        time.sleep(1)
        while response.status_code == 429:
            print("Rate limit exceeded. Waiting for 1 second...")
            time.sleep(1)
            response = requests.post(rate_url, headers=headers, json=data)
        if response.status_code != 201:
            print(f"Error rating {item}: {response.content}")


    print("Closing webdriver...")
    driver.quit()
    service.stop()

if __name__ == '__main__':
    main()