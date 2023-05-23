import os
import json
import requests
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import SessionNotCreatedException
try:
    from IMDBTraktSyncer import checkChromedriver
    from IMDBTraktSyncer import verifyCredentials as VC
    from IMDBTraktSyncer import traktData
    from IMDBTraktSyncer import imdbData
    from IMDBTraktSyncer import errorHandling as EH
except ImportError:
    import checkChromedriver
    import verifyCredentials as VC
    import traktData
    import imdbData
    import errorHandling as EH
from chromedriver_py import binary_path


def main():
    try:

        #Get credentials
        imdb_username = VC.imdb_username
        imdb_password = VC.imdb_password
        
        directory = os.path.dirname(os.path.realpath(__file__))
        
        logging.getLogger('selenium.webdriver').setLevel(logging.WARNING)
        
        #Start web driver
        print('Starting webdriver...')
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3')
        options.add_experimental_option("prefs", {"download.default_directory": directory, "download.directory_upgrade": True, "download.prompt_for_download": False, "credentials_enable_service": False, "profile.password_manager_enabled": False})
        options.add_argument("--disable-save-password-bubble")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-autofill-for-password-fields")
        options.add_argument('--disable-notifications')
        options.add_argument("--disable-third-party-cookies")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-extensions")
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument('--log-level=3')

        service = Service(executable_path=binary_path)
        try:
            driver = webdriver.Chrome(service=service, options=options)
        except SessionNotCreatedException as e:
            error_message = str(e)
            if "This version of ChromeDriver only supports Chrome version" in error_message:
                extract_message = error_message.split("Stacktrace:")[0].replace("Message: session not created:", "").strip()
                print(f"Error: {extract_message}")
                print("See this link for details on how to fix: https://github.com/RileyXX/IMDB-Trakt-Syncer/issues/16")
                raise SystemExit
            else:
                raise

        wait = WebDriverWait(driver, 10)

        driver.get('https://www.imdb.com/registration/signin')

        # wait for sign in link to appear and then click it
        sign_in_link = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'a.list-group-item > .auth-provider-text')))
        if 'IMDb' in sign_in_link.text:
            sign_in_link.click()

        # wait for email input field and password input field to appear, then enter credentials and submit
        email_input = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "input[type='email']")))[0]
        password_input = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "input[type='password']")))[0]
        email_input.send_keys(imdb_username)
        password_input.send_keys(imdb_password)
        submit_button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='submit']")))
        submit_button.click()

        time.sleep(2)

        # go to IMDB homepage
        driver.get('https://www.imdb.com/')

        time.sleep(2)

        # Check if signed in
        element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".nav__userMenu.navbar__user")))
        if element.find_elements(By.CSS_SELECTOR, ".imdb-header__account-toggle--logged-in"):
            print("Successfully signed in to IMDB")
        else:
            print("Error: Not signed in to IMDB")
            print("\nPossible IMDB captcha check or IMDB login incorrect.")
            print("\nIf your login is correct then an IMDB captcha check likely the cause of this error. To fix this, simply login to the IMDB website in your browser, preferably Chrome, and from the same computer. If logged in, log out and log back in. It may ask you to fill in a captcha; complete it and finish logging in. After logging in successfully on your browser, run the script again and it should work. You may need to repeat this step once or twice if it still gives you issues.")
            print("\nIf your IMDB login is incorrect, simply edit the credentials.txt file with the correct login or delete the credentials file and run the script again.")
            print("\nSee this GitHub link for more details: https://github.com/RileyXX/IMDB-Trakt-Syncer/issues/2")
            print("\nStopping script...")
            raise SystemExit
        
        trakt_watchlist, trakt_ratings, trakt_reviews = traktData.getTraktData()
        imdb_watchlist, imdb_ratings, imdb_reviews = imdbData.getImdbData(imdb_username, imdb_password, driver, directory, wait)

        #Get trakt and imdb ratings and filter out trakt ratings with missing imdb id
        trakt_ratings = [rating for rating in trakt_ratings if rating['ID'] is not None]
        imdb_ratings = [rating for rating in imdb_ratings if rating['ID'] is not None]
        trakt_reviews = [review for review in trakt_reviews if review['ID'] is not None]
        imdb_reviews = [review for review in imdb_reviews if review['ID'] is not None]
        trakt_watchlist = [item for item in trakt_watchlist if item['ID'] is not None]
        imdb_watchlist = [item for item in imdb_watchlist if item['ID'] is not None]
        #Filter out ratings already set
        imdb_ratings_to_set = [rating for rating in trakt_ratings if rating['ID'] not in [imdb_rating['ID'] for imdb_rating in imdb_ratings]]
        trakt_ratings_to_set = [rating for rating in imdb_ratings if rating['ID'] not in [trakt_rating['ID'] for trakt_rating in trakt_ratings]]
        imdb_reviews_to_set = [review for review in trakt_reviews if review['ID'] not in [imdb_review['ID'] for imdb_review in imdb_reviews]]
        trakt_reviews_to_set = [review for review in imdb_reviews if review['ID'] not in [trakt_review['ID'] for trakt_review in trakt_reviews]]
        imdb_watchlist_to_set = [item for item in trakt_watchlist if item['ID'] not in [imdb_item['ID'] for imdb_item in imdb_watchlist]]
        trakt_watchlist_to_set = [item for item in imdb_watchlist if item['ID'] not in [trakt_item['ID'] for trakt_item in trakt_watchlist]]
        # Remove duplicate reviews and filter by out any items for imdb_reviews_to_set where comment length is less than 600 characters
        def remove_duplicates_and_filter(lst, key, min_comment_length=None):
            seen = set()
            result = []
            for item in lst:
                if item[key] not in seen and (min_comment_length is None or ('Comment' in item and len(item['Comment']) >= min_comment_length)):
                    seen.add(item[key])
                    result.append(item)
            return result

        imdb_reviews_to_set = remove_duplicates_and_filter(imdb_reviews_to_set, 'ID', 600)
        trakt_reviews_to_set = remove_duplicates_and_filter(trakt_reviews_to_set, 'ID')
        
        # If sync_watchlist_value is true
        if VC.sync_watchlist_value:
            # Set Trakt Watchlist Items
            if trakt_watchlist_to_set:
                print('Setting Trakt Watchlist Items')

                # Count the total number of items
                num_items = len(trakt_watchlist_to_set)
                item_count = 0

                for item in trakt_watchlist_to_set:
                    item_count += 1
                    imdb_id = item['ID']
                    media_type = item['Type']  # 'movie', 'show', or 'episode'

                    url = f"https://api.trakt.tv/sync/watchlist"

                    data = {
                        "movies": [],
                        "shows": [],
                        "episodes": []
                    }

                    if media_type == 'movie':
                        data['movies'].append({
                            "ids": {
                                "imdb": imdb_id
                            }
                        })
                    elif media_type == 'show':
                        data['shows'].append({
                            "ids": {
                                "imdb": imdb_id
                            }
                        })
                    elif media_type == 'episode':
                        data['episodes'].append({
                            "ids": {
                                "imdb": imdb_id
                            }
                        })

                    response = EH.make_trakt_request(url, payload=data)
                    if response:
                        print(f"Adding item ({item_count} of {num_items}): {item['Title']} ({item['Year']}) to Trakt Watchlist")
                    else:
                        print(f"Failed to add item ({item_count} of {num_items}): {item['Title']} ({item['Year']}) to Trakt Watchlist")
                        print("Error Response:", response.content, response.status_code)

                print('Trakt Watchlist Items Set Successfully')
            else:
                print('No Trakt Watchlist Items To Set')

            # Set IMDB Watchlist Items
            if imdb_watchlist_to_set:
                print('Setting IMDB Watchlist Items')
                
                # Count the total number of items
                num_items = len(imdb_watchlist_to_set)
                item_count = 0
                
                for item in imdb_watchlist_to_set:
                    try:
                        item_count += 1
                        year_str = f' ({item["Year"]})' if item["Year"] is not None else '' # sometimes year is None for episodes from trakt so remove it from the print string
                        print(f"Adding item ({item_count} of {num_items}): {item['Title']}{year_str} to IMDB Watchlist")
                        
                        driver.get(f'https://www.imdb.com/title/{item["ID"]}/')
                                            
                        watchlist_button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'button[data-testid="tm-box-wl-button"]')))
                        
                        # Check if item is already in watchlist otherwise skip it
                        if 'ipc-icon--done' not in watchlist_button.get_attribute('innerHTML'):
                            watchlist_button.click()
                            time.sleep(1)
                    except (NoSuchElementException, TimeoutException):
                        print(f"Failed to add item ({item_count} of {num_items}): {item['Title']}{year_str} to IMDB Watchlist ({item['ID']})")
                        pass

                
                print('Setting IMDB Watchlist Items Complete')
            else:
                print('No IMDB Watchlist Items To Set')

        #Set Trakt Ratings
        if trakt_ratings_to_set:
            print('Setting Trakt Ratings')

            # Set the API endpoints
            rate_url = "https://api.trakt.tv/sync/ratings"
            
            # Count the total number of items
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
                    print(f"Rating TV show ({item_count} of {num_items}): {item['Title']} ({item['Year']}): {item['Rating']}/10 on Trakt")
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
                    print(f"Rating movie ({item_count} of {num_items}): {item['Title']} ({item['Year']}): {item['Rating']}/10 on Trakt")
                elif item["Type"] == "episode":
                    # This is an episode
                    data = {
                        "episodes": [{
                            "ids": {
                                "imdb": item["ID"]
                            },
                            "rating": item["Rating"]
                        }]
                    }
                    print(f"Rating episode ({item_count} of {num_items}): {item['Title']} ({item['Year']}): {item['Rating']}/10 on Trakt")

                # Make the API call to rate the item
                response = EH.make_trakt_request(rate_url, payload=data)

                if response is None:
                    print(f"Error rating {item}: {response.content}")

            print('Setting Trakt Ratings Complete')
        else:
            print('No Trakt Ratings To Set')

        #Set IMDB Ratings
        if imdb_ratings_to_set:
            print('Setting IMDB Ratings')

            # loop through each movie and TV show rating and submit rating on IMDB website
            for i, item in enumerate(imdb_ratings_to_set, 1):
                year_str = f' ({item["Year"]})' if item["Year"] is not None else '' # sometimes year is None for episodes from trakt so remove it from the print string
                print(f'Rating {item["Type"]}: ({i} of {len(imdb_ratings_to_set)}) {item["Title"]}{year_str}: {item["Rating"]}/10 on IMDB')
                driver.get(f'https://www.imdb.com/title/{item["ID"]}/')

                # click on "Rate" button and select rating option, then submit rating
                button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'button.ipc-btn span')))
                try:
                    element_rating_bar = button.find_element(By.CSS_SELECTOR, '[data-testid="hero-rating-bar__user-rating__unrated"]')
                    if element_rating_bar:
                        driver.execute_script("arguments[0].click();", button)
                        rating_option_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, f'button[aria-label="Rate {item["Rating"]}"]')))
                        driver.execute_script("arguments[0].click();", rating_option_element)
                        submit_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'button.ipc-rating-prompt__rate-button')))
                        submit_element.click()
                        time.sleep(1)
                except (NoSuchElementException, TimeoutException):
                    print(f'Failed to rate {item["Type"]}: ({i} of {len(imdb_ratings_to_set)}) {item["Title"]}{year_str}: {item["Rating"]}/10 on IMDB ({item["ID"]})')
                    pass

            print('Setting IMDB Ratings Complete')
        else:
            print('No IMDB Ratings To Set')

        # If sync_reviews_value is true
        if VC.sync_reviews_value:
            # Set Trakt Reviews
            if trakt_reviews_to_set:
                print('Setting Trakt Reviews')

                # Count the total number of items
                num_items = len(trakt_reviews_to_set)
                item_count = 0

                for review in trakt_reviews_to_set:
                    item_count += 1
                    imdb_id = review['ID']
                    comment = review['Comment']
                    media_type = review['Type']  # 'movie', 'show', or 'episode'

                    url = f"https://api.trakt.tv/comments"

                    data = {
                        "comment": comment
                    }

                    if media_type == 'movie':
                        data['movie'] = {
                            "ids": {
                                "imdb": imdb_id
                            }
                        }
                    elif media_type == 'show':
                        data['show'] = {
                            "ids": {
                                "imdb": imdb_id
                            }
                        }
                    elif media_type == 'episode':
                        data['episode'] = {
                            "ids": {
                                "imdb": episode_id
                            }
                        }
                    
                    response = EH.make_trakt_request(url, payload=data)
                    if response:
                        print(f"Submitted comment ({item_count} of {num_items}): {review['Title']} ({review['Year']}) on Trakt")
                    else:
                        print(f"Failed to submit comment ({item_count} of {num_items}): {review['Title']} ({review['Year']}) on Trakt")
                        print("Error Response:", response.content, response.status_code)

                print('Trakt Reviews Set Successfully')
            else:
                print('No Trakt Reviews To Set')

            # Set IMDB Reviews
            if imdb_reviews_to_set:
                # Call the check_last_run() function
                if VC.check_imdb_reviews_last_submitted():
                    print('Setting IMDB Reviews')
                    
                    # Count the total number of items
                    num_items = len(trakt_reviews_to_set)
                    item_count = 0
                    
                    for review in imdb_reviews_to_set:
                        item_count += 1
                        try:
                            print(f"Submitting review ({item_count} of {num_items}): {review['Title']} ({review['Year']}) on IMDB")
                            driver.get(f'https://contribute.imdb.com/review/{review["ID"]}/add?bus=imdb')
                            
                            review_title_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input.klondike-input")))
                            review_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "textarea.klondike-textarea")))
                            
                            review_title_input.send_keys("My Review")
                            review_input.send_keys(review["Comment"])
                            
                            no_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul.klondike-userreview-spoiler li:nth-child(2)")))
                            yes_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul.klondike-userreview-spoiler li:nth-child(1)")))
                            
                            if review["Spoiler"]:
                                yes_element.click()                        
                            else:
                                no_element.click()
                                                    
                            submit_button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input.a-button-input[type='submit']")))

                            submit_button.click()
                            
                            time.sleep(1)
                        except (NoSuchElementException, TimeoutException):
                            print(f"Failed to submit review ({item_count} of {num_items}): {review['Title']} ({review['Year']}) on IMDB ({item['ID']})")
                            pass
                    
                    print('Setting IMDB Reviews Complete')
                else:
                    print('IMDB reviews were submitted within the last 7 days. Skipping IMDB review submission.')
            else:
                print('No IMDB Reviews To Set')

        #Close web driver
        print("Closing webdriver...")
        driver.quit()
        service.stop()
    
    except Exception as e:
        error_message = "An error occurred while running the script."
        EH.report_error(error_message)

if __name__ == '__main__':
    main()