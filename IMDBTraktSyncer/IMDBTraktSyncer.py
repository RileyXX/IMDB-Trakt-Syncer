import os
import time
import sys
import argparse
import subprocess
from datetime import datetime, timezone
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from IMDBTraktSyncer import arguments

class PageLoadException(Exception):
    pass

def main():
    parser = argparse.ArgumentParser(description="IMDBTraktSyncer CLI")
    parser.add_argument("--clear-user-data", action="store_true", help="Clears user entered credentials.")
    parser.add_argument("--clear-cache", action="store_true", help="Clears cached browsers, drivers and error logs.")
    parser.add_argument("--uninstall", action="store_true", help="Clears cached browsers and drivers before uninstalling.")
    parser.add_argument("--clean-uninstall", action="store_true", help="Clears all cached data, inluding user credentials, cached browsers and drivers before uninstalling.")
    parser.add_argument("--directory", action="store_true", help="Prints the package install directory.")
    
    args = parser.parse_args()
    
    main_directory = os.path.dirname(os.path.realpath(__file__))

    if args.clear_user_data:
        arguments.clear_user_data(main_directory)
    
    if args.clear_cache:
        arguments.clear_cache(main_directory)
    
    if args.uninstall:
        arguments.uninstall(main_directory)
    
    if args.clean_uninstall:
        arguments.clean_uninstall(main_directory)
    
    if args.directory:
        arguments.print_directory(main_directory)
    
    # If no arguments are passed, run the main package logic
    if not any([args.clear_user_data, args.clear_cache, args.uninstall, args.clean_uninstall, args.directory]):
        
        # Run main package
        print("Starting IMDBTraktSyncer....")
        from IMDBTraktSyncer import checkVersion as CV
        from IMDBTraktSyncer import verifyCredentials as VC
        from IMDBTraktSyncer import checkChrome as CC
        from IMDBTraktSyncer import traktData
        from IMDBTraktSyncer import imdbData
        from IMDBTraktSyncer import errorHandling as EH
        from IMDBTraktSyncer import errorLogger as EL
        
        # Check if package is up to date
        CV.checkVersion()
        
        try:
            # Print credentials directory
            VC.print_directory(main_directory)
            
            # Get credentials
            _, _, _, _, imdb_username, imdb_password = VC.prompt_get_credentials()
            sync_watchlist_value = VC.prompt_sync_watchlist()
            sync_ratings_value = VC.prompt_sync_ratings()
            remove_watched_from_watchlists_value = VC.prompt_remove_watched_from_watchlists()
            sync_reviews_value = VC.prompt_sync_reviews()
            sync_watch_history_value = VC.prompt_sync_watch_history()
            mark_rated_as_watched_value = VC.prompt_mark_rated_as_watched()
            remove_watchlist_items_older_than_x_days_value, watchlist_days_to_remove_value = VC.prompt_remove_watchlist_items_older_than_x_days()
            
            # Check if Chrome portable browser is downloaded and up to date
            CC.checkChrome()
            browser_type, headless = CC.get_browser_type()

            # Set up directory for downloads
            directory = os.path.dirname(os.path.realpath(__file__))

            # Start WebDriver
            print('Starting WebDriver...')
            
            chrome_binary_path  = CC.get_chrome_binary_path(directory)
            chromedriver_binary_path  = CC.get_chromedriver_binary_path(directory)
            user_data_directory = CC.get_user_data_directory()
            
            # Initialize Chrome options
            options = Options()
            options.binary_location = chrome_binary_path
            options.add_argument(f"--user-data-dir={user_data_directory}")
            if headless == True:
                options.add_argument("--headless=new")
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36')
            options.add_experimental_option("prefs", {
                "download.default_directory": directory,
                "download.directory_upgrade": True,
                "download.prompt_for_download": False,
                "profile.default_content_setting_values.automatic_downloads": 1,
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False
            })
            options.add_argument('--disable-gpu')
            options.add_argument('--start-maximized')
            options.add_argument('--disable-notifications')
            options.add_argument("--disable-third-party-cookies")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-extensions")
            options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
            options.add_argument('--log-level=3')
            
            service = Service(executable_path=chromedriver_binary_path)
                        
            # Temporary solution for removing "DevTools listening on ws:" line on Windows for better readability
            # Only use CREATE_NO_WINDOW on Windows systems (32-bit or 64-bit)
            if browser_type == "chrome":
                if sys.platform == "win32":
                    creation_flags = subprocess.CREATE_NO_WINDOW
                    service.creation_flags = creation_flags

            try:
                # Initialize WebDriver with the given options and service
                driver = webdriver.Chrome(service=service, options=options)
                driver.set_page_load_timeout(60)

            except Exception as e:
                error_message = (f"Error initializing WebDriver: {str(e)}")
                print(f"{error_message}")
                EL.logger.error(error_message)
                raise SystemExit
            
            # Example: Wait for an element and interact with it
            wait = WebDriverWait(driver, 10)
            
            # go to IMDB homepage
            success, status_code, url, driver, wait = EH.get_page_with_retries('https://www.imdb.com/', driver, wait)
            if not success:
                # Page failed to load, raise an exception
                raise PageLoadException(f"Failed to load page. Status code: {status_code}. URL: {url}")

            time.sleep(2)

            # Check if still signed in from previous session
            try:
                element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".nav__userMenu .navbar__user-menu-toggle__button")))
                print("Successfully signed in to IMDB")
            except TimeoutException:
                # Not signed in from previous session, proceed with sign in logic
                time.sleep(2)
                
                # Load sign in page
                success, status_code, url, driver, wait = EH.get_page_with_retries('https://www.imdb.com/registration/signin', driver, wait)
                if not success:
                    # Page failed to load, raise an exception
                    raise PageLoadException(f"Failed to load page. Status code: {status_code}. URL: {url}")

                # Wait for sign in link to appear and then click it
                links = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.display-button-container a.ipc-btn')))

                # Loop through the elements to find the one with 'IMDb' in the text
                for link in links:
                    if 'IMDb' in link.get_attribute('textContent'):
                        driver.execute_script("arguments[0].click();", link)
                        break  # stop after clicking the first matching one

                # wait for email input field and password input field to appear, then enter credentials and submit
                email_input = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "input[type='email']")))[0]
                password_input = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "input[type='password']")))[0]
                email_input.send_keys(imdb_username)
                password_input.send_keys(imdb_password)
                submit_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='submit']")))
                driver.execute_script("arguments[0].click();", submit_button)

                time.sleep(2)

                # go to IMDB homepage
                success, status_code, url, driver, wait = EH.get_page_with_retries('https://www.imdb.com/', driver, wait)
                if not success:
                    # Page failed to load, raise an exception
                    raise PageLoadException(f"Failed to load page. Status code: {status_code}. URL: {url}")

                time.sleep(2)

                # Check if signed in
                try:
                    element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".nav__userMenu .navbar__user-menu-toggle__button")))
                    print("Successfully signed in to IMDB")
                except TimeoutException:
                    print("\nError: Not signed in to IMDB")
                    print("\nPossible Causes and Solutions:")
                    print("- IMDB captcha check triggered or incorrect IMDB login.")
                    
                    print("\n1. IMDB Captcha Check:")
                    print("   If your login is correct, the issue is likely due to an IMDB captcha check.")
                    print("   To resolve this, follow these steps:")
                    print("   - Log in to IMDB on your browser (preferably Chrome) and on the same computer.")
                    print("   - If already logged in, log out and log back in.")
                    print("   - Repeat this process until a captcha check is triggered.")
                    print("   - Complete the captcha and finish logging in.")
                    print("   - After successfully logging in, run the script again.")
                    print("   - You may need to repeat these steps until the captcha check is no longer triggered.")
                    
                    print("\n2. Incorrect IMDB Login:")
                    print("   If your IMDB login is incorrect, update your login credentials:")
                    print("   - Edit the 'credentials.txt' file in your settings directory with the correct login information.")
                    print("   - Alternatively, delete the 'credentials.txt' file and run the script again.")
                    
                    print("\nFor more details, see the following GitHub link:")
                    print("https://github.com/RileyXX/IMDB-Trakt-Syncer/issues/2")
                    
                    print("\nStopping script...")
                    
                    EL.logger.error("Error: Not signed in to IMDB")
                    driver.close()
                    driver.quit()
                    service.stop()
                    raise SystemExit
            
            # Check IMDB Language for compatability
            # Get Current Language
            language_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "span[id*='nav-language-selector-contents'] .selected"))).get_attribute("aria-label")
            original_language = language_element
            if (original_language != "English (United States)"):
                print("Temporarily changing IMDB Language to English for compatability. See: https://www.imdb.com/preferences/general")
                # Open Language Dropdown
                language_dropdown = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "label[for*='nav-language-selector']")))
                driver.execute_script("arguments[0].click();", language_dropdown)
                # Change Language to English
                english_element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "span[id*='nav-language-selector-contents'] li[aria-label*='English (United States)']")))
                driver.execute_script("arguments[0].click();", english_element)
            
            # Check IMDB reference view setting for compatability. See: https://www.imdb.com/preferences/general
            # Load page
            success, status_code, url, driver, wait = EH.get_page_with_retries(f'https://www.imdb.com/preferences/general', driver, wait)
            if not success:
                # Page failed to load, raise an exception
                raise PageLoadException(f"Failed to load page. Status code: {status_code}. URL: {url}")
            # Find reference view checkbox
            reference_checkbox = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[id*='ttdp']"))).get_attribute("checked")
            reference_view_changed = False
            if reference_checkbox:
                print("Temporarily disabling reference view IMDB setting for compatability. See: https://www.imdb.com/preferences/general")
                # Click reference view checkbox
                reference_checkbox = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[id*='ttdp']")))
                driver.execute_script("arguments[0].click();", reference_checkbox)
                # Submit
                submit = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".article input[type*='submit']")))
                driver.execute_script("arguments[0].click();", submit)
                reference_view_changed = True
                time.sleep(1)
                
            # Initalize list values
            trakt_watchlist = trakt_ratings = trakt_reviews = trakt_watch_history = imdb_watchlist = imdb_ratings = imdb_reviews = imdb_watch_history = []
            
            # Get Trakt Data
            print('Processing Trakt Data')
            trakt_encoded_username = traktData.get_trakt_encoded_username()
            if sync_watchlist_value or remove_watched_from_watchlists_value:
                trakt_watchlist = traktData.get_trakt_watchlist(trakt_encoded_username)
            if sync_ratings_value or mark_rated_as_watched_value:
                trakt_ratings = traktData.get_trakt_ratings(trakt_encoded_username)
            if sync_reviews_value:
                trakt_reviews = traktData.get_trakt_comments(trakt_encoded_username)
            if sync_watch_history_value or remove_watched_from_watchlists_value or mark_rated_as_watched_value:
                trakt_watch_history = traktData.get_trakt_watch_history(trakt_encoded_username)
            print('Processing Trakt Data Complete')
            
            # Get IMDB Data
            print('Processing IMDB Data')
            driver, wait = imdbData.generate_imdb_exports(driver, wait, directory, sync_watchlist_value, sync_ratings_value, sync_watch_history_value, remove_watched_from_watchlists_value, mark_rated_as_watched_value)
            driver, wait = imdbData.download_imdb_exports(driver, wait, directory, sync_watchlist_value, sync_ratings_value, sync_watch_history_value, remove_watched_from_watchlists_value, mark_rated_as_watched_value)
            if sync_watchlist_value or remove_watched_from_watchlists_value:
                imdb_watchlist, imdb_watchlist_size, driver, wait = imdbData.get_imdb_watchlist(driver, wait, directory)
            if sync_ratings_value or mark_rated_as_watched_value:
                imdb_ratings, driver, wait = imdbData.get_imdb_ratings(driver, wait, directory)
            if sync_reviews_value:
                imdb_reviews, errors_found_getting_imdb_reviews, driver, wait = imdbData.get_imdb_reviews(driver, wait, directory)
            if sync_watch_history_value or remove_watched_from_watchlists_value or mark_rated_as_watched_value:
                imdb_watch_history, imdb_watch_history_size, driver, wait = imdbData.get_imdb_checkins(driver, wait, directory)
            print('Processing IMDB Data Complete')
                        
            if sync_watchlist_value:
                # Check if IMDB watchlist has reached the 10,000 item limit. If limit is reached, disable syncing watchlists.
                imdb_watchlist_limit_reached = EH.check_if_watchlist_limit_reached(imdb_watchlist_size)
                              
            if sync_watch_history_value or mark_rated_as_watched_value:
                # Check if IMDB watch history has reached the 10,000 item limit. If limit is reached, disable syncing watch history.
                imdb_watch_history_limit_reached = EH.check_if_watch_history_limit_reached(imdb_watch_history_size)
            
            # Remove duplicates from Trakt watch_history
            trakt_watch_history = EH.remove_duplicates_by_imdb_id(trakt_watch_history)
            
            # Get trakt and imdb data and filter out items with missing imdb id
            trakt_ratings = [rating for rating in trakt_ratings if rating.get('IMDB_ID') is not None]
            imdb_ratings = [rating for rating in imdb_ratings if rating.get('IMDB_ID') is not None]
            trakt_reviews = [review for review in trakt_reviews if review.get('IMDB_ID') is not None]
            imdb_reviews = [review for review in imdb_reviews if review.get('IMDB_ID') is not None]
            trakt_watchlist = [item for item in trakt_watchlist if item.get('IMDB_ID') is not None]
            imdb_watchlist = [item for item in imdb_watchlist if item.get('IMDB_ID') is not None]
            trakt_watch_history = [item for item in trakt_watch_history if item.get('IMDB_ID') is not None]
            imdb_watch_history = [item for item in imdb_watch_history if item.get('IMDB_ID') is not None]
                       
            # Update outdated IMDB_IDs from trakt lists based on matching Title and Type comparison
            trakt_ratings, imdb_ratings, driver, wait = EH.update_outdated_imdb_ids_from_trakt(trakt_ratings, imdb_ratings, driver, wait)
            trakt_reviews, imdb_reviews, driver, wait = EH.update_outdated_imdb_ids_from_trakt(trakt_reviews, imdb_reviews, driver, wait)
            trakt_watchlist, imdb_watchlist, driver, wait = EH.update_outdated_imdb_ids_from_trakt(trakt_watchlist, imdb_watchlist, driver, wait)
            trakt_watch_history, imdb_watch_history, driver, wait = EH.update_outdated_imdb_ids_from_trakt(trakt_watch_history, imdb_watch_history, driver, wait)
            
            '''
            # Removed temporarily to monitor impact. Most conflicts should be resolved by update_outdated_imdb_ids_from_trakt() function
            # Filter out items that share the same Title, Year and Type, AND have non-matching IMDB_ID values
            trakt_ratings, imdb_ratings = EH.filter_out_mismatched_items(trakt_ratings, imdb_ratings)
            trakt_reviews, imdb_reviews = EH.filter_out_mismatched_items(trakt_reviews, imdb_reviews)
            trakt_watchlist, imdb_watchlist = EH.filter_out_mismatched_items(trakt_watchlist, imdb_watchlist)
            trakt_watch_history, imdb_watch_history = EH.filter_out_mismatched_items(trakt_watch_history, imdb_watch_history)
            '''
            
            # Filter out items already set: Filters items from the target_list that are not already present in the source_list based on key
            imdb_ratings_to_set = EH.filter_items(imdb_ratings, trakt_ratings, key="IMDB_ID")
            trakt_ratings_to_set = EH.filter_items(trakt_ratings, imdb_ratings, key="IMDB_ID")

            imdb_reviews_to_set = EH.filter_items(imdb_reviews, trakt_reviews, key="IMDB_ID")
            trakt_reviews_to_set = EH.filter_items(trakt_reviews, imdb_reviews, key="IMDB_ID")

            imdb_watchlist_to_set = EH.filter_items(imdb_watchlist, trakt_watchlist, key="IMDB_ID")
            trakt_watchlist_to_set = EH.filter_items(trakt_watchlist, imdb_watchlist, key="IMDB_ID")

            imdb_watch_history_to_set = EH.filter_items(imdb_watch_history, trakt_watch_history, key="IMDB_ID")
            trakt_watch_history_to_set = EH.filter_items(trakt_watch_history, imdb_watch_history, key="IMDB_ID")
            
            if mark_rated_as_watched_value:
                # Combine Trakt and IMDB Ratings into one list
                combined_ratings = trakt_ratings + imdb_ratings

                # Remove duplicates from combined_ratings by IMDB_ID
                combined_ratings = EH.remove_duplicates_by_imdb_id(combined_ratings)

                # Loop through combined ratings and check if they are already in both watch histories
                for item in combined_ratings:
                    imdb_id = item['IMDB_ID']

                    # Skip items with 'Type' as 'show' (shows cannot be marked as watched on Trakt)
                    if item['Type'] == 'show':
                        continue
                    
                    # Check if this imdb_id exists in both trakt_watch_history and imdb_watch_history
                    if not any(imdb_id == watch_item['IMDB_ID'] for watch_item in trakt_watch_history) and \
                       not any(imdb_id == watch_item['IMDB_ID'] for watch_item in imdb_watch_history):
                        # If not found in both, add to the appropriate watch history to set list
                        trakt_watch_history_to_set.append(item)
                        imdb_watch_history_to_set.append(item)
                        trakt_watch_history.append(item)
                        imdb_watch_history.append(item)
                        
                        # Remove duplicates from trakt and imdb watch history (in case items added with mark_rated_as_watched_value)
                        trakt_watch_history = EH.remove_duplicates_by_imdb_id(trakt_watch_history)
                        imdb_watch_history = EH.remove_duplicates_by_imdb_id(imdb_watch_history)
            
            # Skip adding shows to trakt watch history, because it will mark all episodes as watched
            trakt_watch_history_to_set = EH.remove_shows(trakt_watch_history_to_set)
            
            # Filter ratings to update
            imdb_ratings_to_update = []
            trakt_ratings_to_update = []

            # Dictionary to store IMDB_IDs and their corresponding ratings for IMDB and Trakt
            imdb_ratings_dict = {rating['IMDB_ID']: rating for rating in imdb_ratings}
            trakt_ratings_dict = {rating['IMDB_ID']: rating for rating in trakt_ratings}

            # Include only items with the same IMDB_ID and different ratings and prefer the most recent rating
            for imdb_id, imdb_rating in imdb_ratings_dict.items():
                if imdb_id in trakt_ratings_dict:
                    trakt_rating = trakt_ratings_dict[imdb_id]
                    if imdb_rating['Rating'] != trakt_rating['Rating']:
                        imdb_date_added = datetime.fromisoformat(imdb_rating['Date_Added'].replace('Z', '')).replace(tzinfo=timezone.utc)
                        trakt_date_added = datetime.fromisoformat(trakt_rating['Date_Added'].replace('Z', '')).replace(tzinfo=timezone.utc)
                        
                        # Check if ratings were added on different days
                        if (imdb_date_added.year, imdb_date_added.month, imdb_date_added.day) != (trakt_date_added.year, trakt_date_added.month, trakt_date_added.day):
                            # If IMDB rating is more recent, add the Trakt rating to the update list, and vice versa
                            if imdb_date_added > trakt_date_added:
                                trakt_ratings_to_update.append(imdb_rating)
                            else:
                                imdb_ratings_to_update.append(trakt_rating)

            # Update ratings_to_set
            imdb_ratings_to_set.extend(imdb_ratings_to_update)
            trakt_ratings_to_set.extend(trakt_ratings_to_update)
            
            # Filter out setting review IMDB where the comment length is less than 600 characters
            imdb_reviews_to_set = EH.filter_by_comment_length(imdb_reviews_to_set, 600)
            
            # Initialize watchlist_items_to_remove variables
            trakt_watchlist_items_to_remove = []
            imdb_watchlist_items_to_remove = []
            
            # If remove_watched_from_watchlists_value is true
            if remove_watched_from_watchlists_value:
                # Combine Trakt and IMDB Watch History into one list
                watched_content = trakt_watch_history + imdb_watch_history
                
                # Remove duplicates from watched_content
                watched_content = EH.remove_duplicates_by_imdb_id(watched_content)
                
                # Get the IDs from watched_content
                watched_content_ids = set(item['IMDB_ID'] for item in watched_content if item['IMDB_ID'])
                        
                # Filter out watched content from trakt_watchlist_to_set
                trakt_watchlist_to_set = [item for item in trakt_watchlist_to_set if item['IMDB_ID'] not in watched_content_ids]
                # Filter out watched content from imdb_watchlist_to_set
                imdb_watchlist_to_set = [item for item in imdb_watchlist_to_set if item['IMDB_ID'] not in watched_content_ids]
                
                # Find items to remove from trakt_watchlist
                trakt_watchlist_items_to_remove = [item for item in trakt_watchlist if item['IMDB_ID'] in watched_content_ids]
                # Find items to remove from imdb_watchlist
                imdb_watchlist_items_to_remove = [item for item in imdb_watchlist if item['IMDB_ID'] in watched_content_ids]
                
                # Sort lists by date
                trakt_watchlist_items_to_remove = EH.sort_by_date_added(trakt_watchlist_items_to_remove)
                imdb_watchlist_items_to_remove = EH.sort_by_date_added(imdb_watchlist_items_to_remove)
            
            # If remove_watchlist_items_older_than_x_days_value is true, add items older than x days to watchlist_items_to_remove lists
            if remove_watchlist_items_older_than_x_days_value:
                days = watchlist_days_to_remove_value
                
                combined_watchlist = trakt_watchlist + imdb_watchlist
                combined_watchlist = EH.remove_duplicates_by_imdb_id(combined_watchlist)
                
                # Get items older than x days
                combined_watchlist_to_remove = EH.get_items_older_than_x_days(combined_watchlist, days)
                
                # Append items to remove to the watchlist_items_to_remove lists
                trakt_watchlist_items_to_remove.extend(combined_watchlist_to_remove)
                imdb_watchlist_items_to_remove.extend(combined_watchlist_to_remove)
                
                # Remove combined_watchlist_to_remove items from watchlist_to_set lists
                imdb_watchlist_to_set, trakt_watchlist_to_set = EH.remove_combined_watchlist_to_remove_items_from_watchlist_to_set_lists_by_imdb_id(combined_watchlist_to_remove, imdb_watchlist_to_set, trakt_watchlist_to_set)
            
            # Sort lists by date
            imdb_ratings_to_set = EH.sort_by_date_added(imdb_ratings_to_set)
            trakt_ratings_to_set = EH.sort_by_date_added(trakt_ratings_to_set)
            imdb_watchlist_to_set = EH.sort_by_date_added(imdb_watchlist_to_set)
            trakt_watchlist_to_set = EH.sort_by_date_added(trakt_watchlist_to_set)
            imdb_watch_history_to_set = EH.sort_by_date_added(imdb_watch_history_to_set)
            trakt_watch_history_to_set = EH.sort_by_date_added(trakt_watch_history_to_set)
            
            if sync_watchlist_value and imdb_watchlist_limit_reached:
                # IMDB watchlist limit reached, skip watchlist actions for IMDB
                imdb_watchlist_to_set = []
            
            if sync_watch_history_value and imdb_watch_history_limit_reached:
                # IMDB watch history limit reached, skip watch history actions for IMDB
                imdb_watch_history_to_set = []
            
            if mark_rated_as_watched_value and imdb_watch_history_limit_reached:
                # IMDB watch history limit reached, skip watch history actions for IMDB
                imdb_watch_history_to_set = []
                        
            # If sync_watchlist_value is true
            if sync_watchlist_value:
                # Set Trakt Watchlist Items
                if trakt_watchlist_to_set:
                    print('Setting Trakt Watchlist Items')

                    # Count the total number of items
                    num_items = len(trakt_watchlist_to_set)
                    item_count = 0

                    for item in trakt_watchlist_to_set:
                        item_count += 1
                        
                        imdb_id = item['IMDB_ID']
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
                        else:
                            data = None

                        if data:
                            response = EH.make_trakt_request(url, payload=data)
                            
                            season_number = item.get('SeasonNumber')
                            episode_number = item.get('EpisodeNumber')
                            if season_number and episode_number:
                                season_number = str(season_number).zfill(2)
                                episode_number = str(episode_number).zfill(2)
                                episode_title = f'[S{season_number}E{episode_number}] '
                            else:
                                episode_title = ''
                            
                            if response and response.status_code in [200, 201, 204]:
                                print(f" - Added {item['Type']} ({item_count} of {num_items}): {episode_title}{item['Title']} ({item['Year']}) to Trakt Watchlist ({item['IMDB_ID']})")
                                
                            else:
                                error_message = f"Failed to add {item['Type']} ({item_count} of {num_items}): {episode_title}{item['Title']} ({item['Year']}) to Trakt Watchlist ({item['IMDB_ID']})"
                                print(f"   - {error_message}")
                                EL.logger.error(error_message)

                    print('Setting Trakt Watchlist Items Complete')
                else:
                    print('No Trakt Watchlist Items To Set')

                # Set IMDB Watchlist Items
                if imdb_watchlist_to_set:
                    print('Setting IMDB Watchlist Items')
                    
                    # Count the total number of items
                    num_items = len(imdb_watchlist_to_set)
                    item_count = 0
                                    
                    for item in imdb_watchlist_to_set:
                        season_number = item.get('SeasonNumber')
                        episode_number = item.get('EpisodeNumber')
                        if season_number and episode_number:
                            season_number = str(season_number).zfill(2)
                            episode_number = str(episode_number).zfill(2)
                            episode_title = f'[S{season_number}E{episode_number}] '
                        else:
                            episode_title = ''
                        
                        year_str = f' ({item["Year"]})' if item["Year"] is not None else '' # sometimes year is None for episodes from trakt so remove it from the print string
                        try:
                            item_count += 1
                                                       
                            # Load page
                            success, status_code, url, driver, wait = EH.get_page_with_retries(f'https://www.imdb.com/title/{item["IMDB_ID"]}/', driver, wait)
                            if not success:
                                # Page failed to load, raise an exception
                                raise PageLoadException(f"Failed to load page. Status code: {status_code}. URL: {url}")
                            
                            current_url = driver.current_url
                            
                            # Check if the URL doesn't contain "/reference"
                            if "/reference" not in current_url:
                                # Wait until the loader has disappeared, indicating the watchlist button has loaded
                                wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, '[data-testid="tm-box-wl-loader"]')))
                                
                                # Scroll the page to bring the element into view
                                watchlist_button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'button[data-testid="tm-box-wl-button"]')))
                                driver.execute_script("arguments[0].scrollIntoView(true);", watchlist_button)
                                
                                # Wait for the element to be clickable
                                watchlist_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-testid="tm-box-wl-button"]')))
                                
                                # Check if item is already in watchlist otherwise skip it
                                if 'ipc-icon--done' not in watchlist_button.get_attribute('innerHTML'):
                                    retry_count = 0
                                    while retry_count < 2:
                                        driver.execute_script("arguments[0].click();", watchlist_button)
                                        try:
                                            WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'button[data-testid="tm-box-wl-button"] .ipc-icon--done')))
                                            
                                            print(f" - Added {item['Type']} ({item_count} of {num_items}): {episode_title}{item['Title']}{year_str} to IMDB Watchlist ({item['IMDB_ID']})")
                                            
                                            break  # Break the loop if successful
                                        except TimeoutException:
                                            retry_count += 1

                                    if retry_count == 2:
                                        error_message = f"Failed to add item ({item_count} of {num_items}): {episode_title}{item['Title']}{year_str} to IMDB Watchlist ({item['IMDB_ID']})"
                                        print(f" - {error_message}")
                                        EL.logger.error(error_message)
                                else:
                                    error_message1 = f" - Failed to add item ({item_count} of {num_items}): {episode_title}{item['Title']}{year_str} to IMDB Watchlist ({item['IMDB_ID']})"
                                    error_message2 = f"   - {item['Type'].capitalize()} already exists in IMDB watchlist."
                                    EL.logger.error(error_message1)
                                    EL.logger.error(error_message2)
                            else:
                                # Handle the case when the URL contains "/reference"
                                
                                # Scroll the page to bring the element into view
                                watchlist_button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.titlereference-watch-ribbon > .wl-ribbon')))
                                driver.execute_script("arguments[0].scrollIntoView(true);", watchlist_button)
                                
                                # Check if watchlist_button has class .not-inWL before clicking
                                if 'not-inWL' in watchlist_button.get_attribute('class'):
                                    driver.execute_script("arguments[0].click();", watchlist_button)
                            
                        except (NoSuchElementException, TimeoutException, PageLoadException):
                            error_message = f"Failed to add item ({item_count} of {num_items}): {item['Title']}{year_str} to IMDB Watchlist ({item['IMDB_ID']})"
                            print(f"  - {error_message}")
                            EL.logger.error(error_message, exc_info=True)
                            pass

                    
                    print('Setting IMDB Watchlist Items Complete')
                else:
                    print('No IMDB Watchlist Items To Set')
             
            # If sync_ratings_value is true
            if sync_ratings_value:
                
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
                                        "imdb": item["IMDB_ID"]
                                    },
                                    "rating": item["Rating"]
                                }]
                            }
                        elif item["Type"] == "movie":
                            # This is a movie
                            data = {
                                "movies": [{
                                    "ids": {
                                        "imdb": item["IMDB_ID"]
                                    },
                                    "rating": item["Rating"]
                                }]
                            }
                        elif item["Type"] == "episode":
                            # This is an episode
                            data = {
                                "episodes": [{
                                    "ids": {
                                        "imdb": item["IMDB_ID"]
                                    },
                                    "rating": item["Rating"]
                                }]
                            }
                        else:
                            data = None
                        
                        if data:
                            # Make the API call to rate the item
                            response = EH.make_trakt_request(rate_url, payload=data)
                            
                            season_number = item.get('SeasonNumber')
                            episode_number = item.get('EpisodeNumber')
                            if season_number and episode_number:
                                season_number = str(season_number).zfill(2)
                                episode_number = str(episode_number).zfill(2)
                                episode_title = f'[S{season_number}E{episode_number}] '
                            else:
                                episode_title = ''
                            
                            if response and response.status_code in [200, 201, 204]:
                                print(f" - Rated {item['Type']} ({item_count} of {num_items}): {episode_title}{item['Title']} ({item['Year']}): {item['Rating']}/10 on Trakt ({item['IMDB_ID']})")
                            else:
                                error_message = f"Failed rating {item['Type']} ({item_count} of {num_items}): {episode_title}{item['Title']} ({item['Year']}): {item['Rating']}/10 on Trakt ({item['IMDB_ID']})"
                                print(f"   - {error_message}")
                                EL.logger.error(error_message)

                    print('Setting Trakt Ratings Complete')
                else:
                    print('No Trakt Ratings To Set')

                # Set IMDB Ratings
                if imdb_ratings_to_set:
                    print('Setting IMDB Ratings')
                        
                    # loop through each movie and TV show rating and submit rating on IMDB website
                    for i, item in enumerate(imdb_ratings_to_set, 1):
                        
                        season_number = item.get('SeasonNumber')
                        episode_number = item.get('EpisodeNumber')
                        if season_number and episode_number:
                            season_number = str(season_number).zfill(2)
                            episode_number = str(episode_number).zfill(2)
                            episode_title = f'[S{season_number}E{episode_number}] '
                        else:
                            episode_title = ''
                        
                        year_str = f' ({item["Year"]})' if item["Year"] is not None else '' # sometimes year is None for episodes from trakt so remove it from the print string
                        
                        try:
                            # Load page
                            success, status_code, url, driver, wait = EH.get_page_with_retries(f'https://www.imdb.com/title/{item["IMDB_ID"]}/', driver, wait)
                            if not success:
                                # Page failed to load, raise an exception
                                raise PageLoadException(f"Failed to load page. Status code: {status_code}. URL: {url}")
                            
                            current_url = driver.current_url
                            
                            # Check if the URL doesn't contain "/reference"
                            if "/reference" not in current_url:
                                # Wait until the rating bar has loaded
                                wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, '[data-testid="hero-rating-bar__loading"]')))
                                
                                # Wait until rate button is located and scroll to it
                                button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="hero-rating-bar__user-rating"] button.ipc-btn')))
                                # driver.execute_script("arguments[0].scrollIntoView(true);", button)
                                
                                # click on "Rate" button and select rating option, then submit rating
                                locator = (By.CSS_SELECTOR, '[data-testid="hero-rating-bar__user-rating"] button.ipc-btn')
                                button = wait.until(lambda d: (lambda el: el if el.get_attribute("aria-disabled") == "false" else False)(d.find_element(*locator)))
                                try:
                                    has_existing_rating = button.find_element(By.CSS_SELECTOR, '[data-testid="hero-rating-bar__user-rating__score"] span')
                                    existing_rating_text = has_existing_rating.get_attribute("textContent").strip()
                                    existing_rating = int(existing_rating_text)
                                except NoSuchElementException:
                                    existing_rating = None
                                except ValueError as e:
                                    error_message = f'There was a ValueError when attempting to get existing rating for for this item {item["Type"]}. See error log for details. Script will still attempt to rate this {item["Type"]}. : ({i} of {len(imdb_ratings_to_set)}) {episode_title}{item["Title"]}{year_str}: {item["Rating"]}/10 on IMDB ({item["IMDB_ID"]})'
                                    print(error_message)
                                    existing_rating = None
                                    EL.logger.error(error_message, exc_info=True)
                                    
                                if existing_rating != item["Rating"]:
                                    button = driver.find_element(By.CSS_SELECTOR, '[data-testid="hero-rating-bar__user-rating"] button.ipc-btn')
                                    driver.execute_script("arguments[0].click();", button)
                                    rating_option_element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, f'button[aria-label="Rate {item["Rating"]}"]')))
                                    driver.execute_script("arguments[0].click();", rating_option_element)
                                    submit_element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.ipc-rating-prompt__rate-button')))
                                    driver.execute_script("arguments[0].click();", submit_element)
                                    time.sleep(1)
                                    
                                    print(f' - Rated {item["Type"]}: ({i} of {len(imdb_ratings_to_set)}) {episode_title}{item["Title"]}{year_str}: {item["Rating"]}/10 on IMDB ({item["IMDB_ID"]})')
                                    
                                else:
                                    error_message1 = f' - Rating already exists on IMDB for this {item["Type"]}: ({i} of {len(imdb_ratings_to_set)}) {episode_title}{item["Title"]}{year_str}: {item["Rating"]}/10 on IMDB ({item["IMDB_ID"]})'
                                    print(error_message1)
                                    EL.logger.error(error_message1)
                            else:
                                # Handle the case when the URL contains "/reference"
                                
                                # Wait until rate button is located and scroll to it
                                button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.ipl-rating-interactive__star-container')))
                                driver.execute_script("arguments[0].scrollIntoView(true);", button)

                                # click on "Rate" button and select rating option, then submit rating
                                button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '.ipl-rating-interactive__star-container')))
                                driver.execute_script("arguments[0].click();", button)
                                
                                # Find the rating option element based on the data-value attribute
                                rating_option_element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, f'.ipl-rating-selector__star-link[data-value="{item["Rating"]}"]')))
                                driver.execute_script("arguments[0].click();", rating_option_element)
                                
                                time.sleep(1)
                                
                        except (NoSuchElementException, TimeoutException, PageLoadException):
                            error_message = f'Failed to rate {item["Type"]}: ({i} of {len(imdb_ratings_to_set)}) {episode_title}{item["Title"]}{year_str}: {item["Rating"]}/10 on IMDB ({item["IMDB_ID"]})'
                            print(f" - {error_message}")
                            EL.logger.error(error_message, exc_info=True)
                            pass

                    print('Setting IMDB Ratings Complete')
                else:
                    print('No IMDB Ratings To Set')

            # If sync_reviews_value is true
            if sync_reviews_value:
                
                # Check if there was an error getting IMDB reviews
                if not errors_found_getting_imdb_reviews:
                    
                    # Set Trakt Reviews
                    if trakt_reviews_to_set:
                        print('Setting Trakt Reviews')

                        # Count the total number of items
                        num_items = len(trakt_reviews_to_set)
                        item_count = 0

                        for item in trakt_reviews_to_set:
                            item_count += 1
                            
                            imdb_id = item['IMDB_ID']
                            comment = item['Comment']
                            media_type = item['Type']  # 'movie', 'show', or 'episode'

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
                            else:
                                data = None
                            
                            if data:
                                response = EH.make_trakt_request(url, payload=data)
                                
                                season_number = item.get('SeasonNumber')
                                episode_number = item.get('EpisodeNumber')
                                if season_number and episode_number:
                                    season_number = str(season_number).zfill(2)
                                    episode_number = str(episode_number).zfill(2)
                                    episode_title = f'[S{season_number}E{episode_number}] '
                                else:
                                    episode_title = ''

                                if response and response.status_code in [200, 201, 204]:
                                    print(f" - Submitted comment ({item_count} of {num_items}): {episode_title}{item['Title']} ({item['Year']}) on Trakt ({item['IMDB_ID']})")
                                else:
                                    error_message = f"Failed to submit comment ({item_count} of {num_items}): {episode_title}{item['Title']} ({item['Year']}) on Trakt ({item['IMDB_ID']})"
                                    print(f"   - {error_message}")
                                    EL.logger.error(error_message)

                        print('Trakt Reviews Set Successfully')
                    else:
                        print('No Trakt Reviews To Set')

                    # Set IMDB Reviews
                    if imdb_reviews_to_set:
                        # Call the check_last_run() function
                        if VC.check_imdb_reviews_last_submitted():
                            print('Setting IMDB Reviews')
                            
                            # Count the total number of items
                            num_items = len(imdb_reviews_to_set)
                            item_count = 0
                            
                            for item in imdb_reviews_to_set:
                                item_count += 1
                                try:
                                
                                    season_number = item.get('SeasonNumber')
                                    episode_number = item.get('EpisodeNumber')
                                    if season_number and episode_number:
                                        season_number = str(season_number).zfill(2)
                                        episode_number = str(episode_number).zfill(2)
                                        episode_title = f'[S{season_number}E{episode_number}] '
                                    else:
                                        episode_title = ''
                                
                                    print(f" - Submitting review ({item_count} of {num_items}): {episode_title}{item['Title']} ({item['Year']}) on IMDB ({item['IMDB_ID']})")
                                    
                                    # Load page
                                    success, status_code, url, driver, wait = EH.get_page_with_retries(f'https://contribute.imdb.com/review/{item["IMDB_ID"]}/add?bus=imdb', driver, wait)
                                    if not success:
                                        # Page failed to load, raise an exception
                                        raise PageLoadException(f"Failed to load page. Status code: {status_code}. URL: {url}")
                                    
                                    review_title_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#text-input__0")))
                                    review_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#textarea__0")))
                                    
                                    # Clear old review inputs if review already exists
                                    review_title_input.clear()
                                    review_input.clear()
                                    
                                    review_title_input.send_keys("My Review")
                                    review_input.send_keys(item["Comment"])
                                    
                                    no_element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#is_spoiler-1")))
                                    yes_element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#is_spoiler-0")))
                                    
                                    if item["Spoiler"]:
                                        driver.execute_script("arguments[0].click();", yes_element)                                        
                                    else:
                                        driver.execute_script("arguments[0].click();", no_element)
                                                            
                                    submit_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label='Submit']")))

                                    driver.execute_script("arguments[0].click();", submit_button)
                                    
                                    time.sleep(3) # wait for rating to submit
                                except (NoSuchElementException, TimeoutException, PageLoadException):
                                    error_message = f"Failed to submit review ({item_count} of {num_items}): {item['Title']} ({item['Year']}) on IMDB ({item['IMDB_ID']})"
                                    print(f"   - {error_message}")
                                    EL.logger.error(error_message, exc_info=True)
                                    pass
                            
                            print('Setting IMDB Reviews Complete')
                        else:
                            print('IMDB reviews were submitted within the last 10 days. Skipping IMDB review submission.')
                    else:
                        print('No IMDB Reviews To Set')
                else:
                    print('There was an error getting IMDB reviews. See exception. Skipping reviews submissions.')

            # If remove_watched_from_watchlists_value is true
            if remove_watched_from_watchlists_value or remove_watchlist_items_older_than_x_days_value:
                
                # Remove Watched Items Trakt Watchlist
                if trakt_watchlist_items_to_remove:
                    print('Removing Watched Items From Trakt Watchlist')

                    # Set the API endpoint
                    remove_url = "https://api.trakt.tv/sync/watchlist/remove"

                    # Count the total number of items
                    num_items = len(trakt_watchlist_items_to_remove)
                    item_count = 0

                    # Loop through the items to remove from the watchlist
                    for item in trakt_watchlist_items_to_remove:
                        item_count += 1
                        if item["Type"] == "show":
                            # This is a TV show
                            data = {
                                "shows": [{
                                    "ids": {
                                        "imdb": item["IMDB_ID"]
                                    }
                                }]
                            }
                        elif item["Type"] == "movie":
                            # This is a movie
                            data = {
                                "movies": [{
                                    "ids": {
                                        "imdb": item["IMDB_ID"]
                                    }
                                }]
                            }
                        elif item["Type"] == "episode":
                            
                            # This is an episode
                            data = {
                                "episodes": [{
                                    "ids": {
                                        "imdb": item["IMDB_ID"]
                                    }
                                }]
                            }
                        else:
                            data = None

                        if data:
                            # Make the API call to remove the item from the watchlist
                            response = EH.make_trakt_request(remove_url, payload=data)

                            season_number = item.get('SeasonNumber')
                            episode_number = item.get('EpisodeNumber')
                            if season_number and episode_number:
                                season_number = str(season_number).zfill(2)
                                episode_number = str(episode_number).zfill(2)
                                episode_title = f'[S{season_number}E{episode_number}] '
                            else:
                                episode_title = ''
                                                        
                            if response and response.status_code in [200, 201, 204]:
                                print(f" - Removed {item['Type']} ({item_count} of {num_items}): {episode_title}{item['Title']} ({item['Year']}) from Trakt Watchlist ({item['IMDB_ID']})")
                            else:
                                error_message = f"Failed removing {item['Type']} ({item_count} of {num_items}): {episode_title}{item['Title']} ({item['Year']}) from Trakt Watchlist ({item['IMDB_ID']})"
                                print(f"   - {error_message}")
                                EL.logger.error(error_message)

                    print('Removing Watched Items From Trakt Watchlist Complete')
                else:
                    print('No Trakt Watchlist Items To Remove')

                # Remove Watched Items IMDB Watchlist
                if imdb_watchlist_items_to_remove:
                    print('Removing Watched Items From IMDB Watchlist')
                    
                    # Count the total number of items
                    num_items = len(imdb_watchlist_items_to_remove)
                    item_count = 0
                                    
                    for item in imdb_watchlist_items_to_remove:
                    
                        season_number = item.get('SeasonNumber')
                        episode_number = item.get('EpisodeNumber')
                        if season_number and episode_number:
                            season_number = str(season_number).zfill(2)
                            episode_number = str(episode_number).zfill(2)
                            episode_title = f'[S{season_number}E{episode_number}] '
                        else:
                            episode_title = ''
                        
                        year_str = f' ({item["Year"]})' if item["Year"] is not None else '' # sometimes year is None for episodes from trakt so remove it from the print string
                        
                        try:
                            item_count += 1
                            
                            # Load page
                            success, status_code, url, driver, wait = EH.get_page_with_retries(f'https://www.imdb.com/title/{item["IMDB_ID"]}/', driver, wait)
                            if not success:
                                # Page failed to load, raise an exception
                                raise PageLoadException(f"Failed to load page. Status code: {status_code}. URL: {url}")
                            
                            current_url = driver.current_url
                            
                            # Check if the URL doesn't contain "/reference"
                            if "/reference" not in current_url:
                                # Wait until the loader has disappeared, indicating the watchlist button has loaded
                                wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, '[data-testid="tm-box-wl-loader"]')))
                                
                                # Scroll the page to bring the element into view
                                watchlist_button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'button[data-testid="tm-box-wl-button"]')))
                                driver.execute_script("arguments[0].scrollIntoView(true);", watchlist_button)
                                
                                # Wait for the element to be clickable
                                watchlist_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-testid="tm-box-wl-button"]')))
                                
                                # Check if item is not in watchlist otherwise skip it
                                if 'ipc-icon--add' not in watchlist_button.get_attribute('innerHTML'):
                                    retry_count = 0
                                    while retry_count < 2:
                                        driver.execute_script("arguments[0].click();", watchlist_button)
                                        try:
                                            WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'button[data-testid="tm-box-wl-button"] .ipc-icon--add')))
                                            
                                            print(f" - Removed {item['Type']} ({item_count} of {num_items}): {episode_title}{item['Title']}{year_str} from IMDB Watchlist ({item['IMDB_ID']})")
                                            
                                            break  # Break the loop if successful
                                        except TimeoutException:
                                            retry_count += 1

                                    if retry_count == 2:
                                        error_message = f"Failed to remove {item['Type']} ({item_count} of {num_items}): {episode_title}{item['Title']}{year_str} from IMDB Watchlist ({item['IMDB_ID']})"
                                        print(f" - {error_message}")
                                        EL.logger.error(error_message)
                                    
                                else:
                                    error_message1 = f" - Failed to remove {item['Type']} ({item_count} of {num_items}): {episode_title}{item['Title']}{year_str} from IMDB Watchlist ({item['IMDB_ID']})"
                                    error_message2 = f"   - {item['Type'].capitalize()} not in IMDB watchlist."
                                    EL.logger.error(error_message1)
                                    EL.logger.error(error_message2)
                        
                            else:
                                # Handle the case when the URL contains "/reference"
                                
                                # Scroll the page to bring the element into view
                                watchlist_button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.titlereference-watch-ribbon > .wl-ribbon')))
                                driver.execute_script("arguments[0].scrollIntoView(true);", watchlist_button)
                                
                                # Check if watchlist_button doesn't have the class .not-inWL before clicking
                                if 'not-inWL' not in watchlist_button.get_attribute('class'):
                                    driver.execute_script("arguments[0].click();", watchlist_button)

                        except (NoSuchElementException, TimeoutException, PageLoadException):
                            error_message = f"Failed to remove {item['Type']} ({item_count} of {num_items}): {item['Title']}{year_str} from IMDB Watchlist ({item['IMDB_ID']})"
                            print(f" - {error_message}")
                            EL.logger.error(error_message, exc_info=True)
                            pass

                    
                    print('Removing Watched Items From IMDB Watchlist Complete')
                else:
                    print('No IMDB Watchlist Items To Remove')
            
            # If sync_watch_history_value is true
            if sync_watch_history_value or mark_rated_as_watched_value:
            
                # Set Trakt Watch History
                if trakt_watch_history_to_set:
                    print('Setting Trakt Watch History')

                    # Set the API endpoint for syncing watch history
                    watch_history_url = "https://api.trakt.tv/sync/history"
                    
                    # Count the total number of items
                    num_items = len(trakt_watch_history_to_set)
                    item_count = 0
                    
                    # Loop through your data table and set watch history for each item
                    for item in trakt_watch_history_to_set:
                        item_count += 1
                        
                        # Initialize the data variable for the current item
                        data = None
                        
                        if item["Type"] == "movie":
                            # This is a movie
                            data = {
                                "movies": [{
                                    "ids": {
                                        "imdb": item["IMDB_ID"]
                                    },
                                    "watched_at": item["WatchedAt"]  # Mark when the movie was watched
                                }]
                            }
                        
                        elif item["Type"] == "episode":
                        
                            # This is an episode                                
                            data = {
                                "episodes": [{
                                    "ids": {
                                        "imdb": item["IMDB_ID"]
                                    },
                                    "watched_at": item["WatchedAt"]  # Mark when the episode was watched
                                }]
                            }
                        
                        '''
                        # Skip adding shows, because it will mark all episodes as watched
                        elif item["Type"] == "show":
                            # This is an episode
                            data = {
                                "shows": [{
                                    "ids": {
                                        "imdb": item["IMDB_ID"]
                                    },
                                    "watched_at": item["WatchedAt"]  # Mark when the episode was watched
                                }]
                            }
                        '''
                        
                        if data:
                            # Make the API call to mark the item as watched
                            response = EH.make_trakt_request(watch_history_url, payload=data)
                            
                            season_number = item.get('SeasonNumber')
                            episode_number = item.get('EpisodeNumber')
                            if season_number and episode_number:
                                season_number = str(season_number).zfill(2)
                                episode_number = str(episode_number).zfill(2)
                                episode_title = f'[S{season_number}E{episode_number}] '
                            else:
                                episode_title = ''
                            
                            year_str = f' ({item["Year"]})' if item["Year"] is not None else '' # sometimes year is None for episodes from trakt so remove it from the print string
                            
                            if response and response.status_code in [200, 201, 204]:
                                print(f" - Adding {item['Type']} ({item_count} of {num_items}): {episode_title}{item['Title']} ({item['Year']}) to Trakt Watch History ({item['IMDB_ID']})")
                            
                            else:
                                error_message = f"Failed to add {item['Type']} ({item_count} of {num_items}): {episode_title}{item['Title']} ({item['Year']}) to Trakt Watch History ({item['IMDB_ID']})"
                                print(f"   - {error_message}")
                                EL.logger.error(error_message)

                    print('Setting Trakt Watch History Complete')
                else:
                    print('No Trakt Watch History To Set')
                    
                # Set IMDB Watch History Items
                if imdb_watch_history_to_set:
                    print('Setting IMDB Watch History Items')
                    
                    # Count the total number of items
                    num_items = len(imdb_watch_history_to_set)
                    item_count = 0
                                    
                    for item in imdb_watch_history_to_set:
                        
                        season_number = item.get('SeasonNumber')
                        episode_number = item.get('EpisodeNumber')
                        if season_number and episode_number:
                            season_number = str(season_number).zfill(2)
                            episode_number = str(episode_number).zfill(2)
                            episode_title = f'[S{season_number}E{episode_number}] '
                        else:
                            episode_title = ''
                            
                        year_str = f' ({item.get("Year")})' if item.get("Year") is not None else ''  # Handles None safely
                        
                        try:
                            item_count += 1
                            
                            # Load page
                            success, status_code, url, driver, wait = EH.get_page_with_retries(f'https://www.imdb.com/title/{item["IMDB_ID"]}/', driver, wait)
                            if not success:
                                # Page failed to load, raise an exception
                                raise PageLoadException(f"Failed to load page. Status code: {status_code}. URL: {url}")
                            
                            current_url = driver.current_url
                            
                            # Check if the URL doesn't contain "/reference"
                            if "/reference" not in current_url:
                                # Wait until the loader has disappeared, indicating the watch history button has loaded
                                wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, '[data-testid="tm-box-wl-loader"]')))
                                
                                # Scroll the page to bring the element into view
                                watch_history_button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'button[data-testid="tm-box-addtolist-button"]')))
                                driver.execute_script("arguments[0].scrollIntoView(true);", watch_history_button)
                                
                                # Wait for the element to be clickable
                                watch_history_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-testid="tm-box-addtolist-button"]')))
                                
                                driver.execute_script("arguments[0].click();", watch_history_button)
                                
                                watch_history_button = wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'Your check-ins')]")))
                                
                                watch_history_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'Your check-ins')]")))
                                                                
                                # Check if item is already in watch history otherwise skip it
                                if 'true' not in watch_history_button.get_attribute('data-titleinlist'):
                                    retry_count = 0
                                    while retry_count < 2:
                                        driver.execute_script("arguments[0].click();", watch_history_button)
                                        try:
                                            WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'ipc-promptable-base__content')]//div[@data-titleinlist='true']")))
                                            
                                            print(f" - Adding {item.get('Type')} ({item_count} of {num_items}): {episode_title}{item.get('Title')}{year_str} to IMDB Watch History ({item.get('IMDB_ID')})")
                            
                                            break  # Break the loop if successful
                                        except TimeoutException:
                                            retry_count += 1

                                    if retry_count == 2:
                                        error_message = f"Failed to add {item['Type']} ({item_count} of {num_items}): {episode_title}{item['Title']}{year_str} to IMDB Watch History ({item['IMDB_ID']})"
                                        print(f" - {error_message}")
                                        EL.logger.error(error_message)
                                else:
                                    error_message1 = f" - Failed to add {item['Type']} ({item_count} of {num_items}): {episode_title}{item['Title']}{year_str} to IMDB Watch History ({item['IMDB_ID']})"
                                    error_message2 = f"   - {item['Type'].capitalize()} already exists in IMDB watch history."
                                    EL.logger.error(error_message1)
                                    EL.logger.error(error_message2)
                            else:
                                # Handle the case when the URL contains "/reference"
                                error_message1 = f"IMDB reference view setting is enabled. Adding items to IMDB Check-ins is not supported. See: https://www.imdb.com/preferences/general"
                                error_message2 = f"Failed to add item ({item_count} of {num_items}): {item['Title']}{year_str} to IMDB Watch History ({item['IMDB_ID']})"
                                print(f" - {error_message1}")
                                print(f" - {error_message2}")
                                EL.logger.error(error_message1)
                                EL.logger.error(error_message2)
                            
                        except (NoSuchElementException, TimeoutException, PageLoadException):
                            error_message = f"Failed to add item ({item_count} of {num_items}): {episode_title}{item['Title']}{year_str} to IMDB Watch History ({item['IMDB_ID']})"
                            print(f" - {error_message}")
                            EL.logger.error(error_message, exc_info=True)
                            pass

                    
                    print('Setting IMDB Watch History Items Complete')
                else:
                    print('No IMDB Watch History Items To Set')
            
            # Change language back to original if was changed
            if (original_language != "English (United States)"):
                print("Changing IMDB Language Back to Original. See: https://www.imdb.com/preferences/general")
                # go to IMDB homepage
                success, status_code, url, driver, wait = EH.get_page_with_retries('https://www.imdb.com/', driver, wait)
                if not success:
                    # Page failed to load, raise an exception
                    raise PageLoadException(f"Failed to load page. Status code: {status_code}. URL: {url}")
                
                # Change Language Back to Original
                # Open Language Dropdown
                language_dropdown = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "label[for*='nav-language-selector']")))
                driver.execute_script("arguments[0].click();", language_dropdown)
                # Change Language to Original
                original_language_element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, f"span[id*='nav-language-selector-contents'] li[aria-label*='{original_language}']")))
                driver.execute_script("arguments[0].click();", original_language_element)
                
            # Find reference view checkbox
            if reference_view_changed:
                print("Changing reference view IMDB setting back to original. See: https://www.imdb.com/preferences/general")
                # Load page
                success, status_code, url, driver, wait = EH.get_page_with_retries(f'https://www.imdb.com/preferences/general', driver, wait)
                if not success:
                    # Page failed to load, raise an exception
                    raise PageLoadException(f"Failed to load page. Status code: {status_code}. URL: {url}")
                # Click reference view checkbox
                reference_checkbox = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[id*='ttdp']")))
                driver.execute_script("arguments[0].click();", reference_checkbox)
                # Submit
                submit = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".article input[type*='submit']")))
                driver.execute_script("arguments[0].click();", submit)
                time.sleep(1)
            
            #Close web driver
            print("Closing webdriver...")
            driver.close()
            driver.quit()
            service.stop()
            print("IMDBTraktSyncer Complete")
        
        except Exception as e:
            error_message = "An error occurred while running the script."
            EH.report_error(error_message)
            EL.logger.error(error_message, exc_info=True)
            
            # Close the driver and stop the service if they were initialized
            if 'driver' in locals() and driver is not None:
                driver.close()
                driver.quit()
            if 'service' in locals() and service is not None:
                service.stop()

if __name__ == '__main__':
    main()