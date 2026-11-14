import os
import time
import csv
import traceback
import tempfile
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support import expected_conditions as EC
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from IMDBTraktSyncer import errorHandling as EH
from IMDBTraktSyncer import errorLogger as EL

class PageLoadException(Exception):
    pass

_EXISTING_IMDB_EXPORT_CACHE = {}

def _get_existing_imdb_export(file_path, required_columns):
    stat_result = os.stat(file_path)
    signature = (stat_result.st_mtime_ns, stat_result.st_size)
    cache_key = os.path.abspath(file_path)
    cache_entry = _EXISTING_IMDB_EXPORT_CACHE.get(cache_key)
    if cache_entry and cache_entry["signature"] == signature:
        return cache_entry

    with open(file_path, "r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        has_header = reader.fieldnames is not None
        fieldnames = reader.fieldnames or required_columns
        missing_columns = [column for column in required_columns if column not in fieldnames]
        if missing_columns:
            raise ValueError(
                f"Cannot update {os.path.basename(file_path)}; required columns are missing: "
                f"{', '.join(missing_columns)}"
            )
        rows = list(reader)

    rows_by_id = {}
    for row in rows:
        imdb_id = row.get("Const")
        if imdb_id:
            rows_by_id.setdefault(imdb_id, row)

    cache_entry = {
        "signature": signature,
        "fieldnames": fieldnames,
        "has_header": has_header,
        "rows": rows,
        "rows_by_id": rows_by_id
    }
    _EXISTING_IMDB_EXPORT_CACHE[cache_key] = cache_entry
    return cache_entry

def update_existing_imdb_export(directory, file_name, item):
    export_columns = {
        "watchlist.csv": ["Title", "Year", "Const", "Created", "Title Type"],
        "ratings.csv": ["Title", "Year", "Your Rating", "Const", "Date Rated", "Title Type"],
        "checkins.csv": ["Title", "Year", "Const", "Created", "Title Type"]
    }
    if file_name not in export_columns:
        raise ValueError(f"Unsupported IMDb export file: {file_name}")

    file_path = os.path.join(directory, file_name)
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"IMDb export file not found: {file_path}")
    cache_entry = _get_existing_imdb_export(file_path, export_columns[file_name])
    fieldnames = cache_entry["fieldnames"]
    has_header = cache_entry["has_header"]
    rows = cache_entry["rows"]
    rows_by_id = cache_entry["rows_by_id"]

    media_type = {
        "movie": "Movie",
        "show": "TV Series",
        "episode": "TV Episode"
    }.get(item.get("Type"), "")
    imdb_id = item.get("IMDB_ID")
    if not imdb_id:
        raise ValueError(f"Cannot update {file_name} without an IMDb title ID.")
    date_added = str(item.get("Date_Added") or datetime.now().strftime("%Y-%m-%d"))[:10]
    new_row = {column: "" for column in fieldnames}
    new_row.update({
        "Title": item.get("Title") or "",
        "Year": item.get("Year") or "",
        "Const": imdb_id,
        "Title Type": media_type
    })
    if file_name == "ratings.csv":
        new_row["Your Rating"] = item.get("Rating") or ""
        new_row["Date Rated"] = date_added
    else:
        new_row["Created"] = date_added

    existing_row = rows_by_id.get(new_row["Const"])
    if existing_row is not None:
        updates = {
            column: new_row[column]
            for column in export_columns[file_name]
        }
        if all(existing_row.get(column) == value for column, value in updates.items()):
            return
        updated_row = dict(existing_row)
        updated_row.update(updates)
        rows_to_write = [
            updated_row if row is existing_row else row
            for row in rows
        ]
    else:
        if "Position" in fieldnames:
            new_row["Position"] = str(len(rows) + 1)
        try:
            with open(
                file_path,
                "a",
                encoding="utf-8" if has_header else "utf-8-sig",
                newline=""
            ) as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="ignore")
                if not has_header:
                    writer.writeheader()
                writer.writerow(new_row)
        except OSError as exc:
            raise RuntimeError(f"Could not update IMDb export '{file_path}'.") from exc
        cache_entry["has_header"] = True
        rows.append(new_row)
        rows_by_id[new_row["Const"]] = new_row
        stat_result = os.stat(file_path)
        cache_entry["signature"] = (stat_result.st_mtime_ns, stat_result.st_size)
        return

    temporary_file = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8-sig",
            newline="",
            dir=directory,
            prefix=f".{file_name}-",
            suffix=".tmp",
            delete=False
        ) as file:
            temporary_file = file.name
            writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows_to_write)
        os.replace(temporary_file, file_path)
    except OSError as exc:
        raise RuntimeError(f"Could not update IMDb export '{file_path}'.") from exc
    finally:
        if temporary_file and os.path.exists(temporary_file):
            os.remove(temporary_file)
    existing_row.update(updates)
    stat_result = os.stat(file_path)
    cache_entry["signature"] = (stat_result.st_mtime_ns, stat_result.st_size)

def get_export_button(driver, wait):
    controls = "//*[self::button or self::a or @role='button' or @role='menuitem']"
    text_contains_export = (
        "contains(translate(normalize-space(.), "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'export')"
    )
    label_contains_export = (
        "contains(translate(@aria-label, "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'export')"
    )
    testid_contains_export = (
        "contains(translate(@data-testid, "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'export')"
    )
    export_locator = (
        By.XPATH,
        controls + f"[{text_contains_export} or {label_contains_export} or {testid_contains_export}]"
    )
    text_contains_actions = (
        "contains(translate(normalize-space(.), "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'action')"
    )
    label_contains_actions = (
        "contains(translate(@aria-label, "
        "'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'action')"
    )
    actions_locator = (
        By.XPATH,
        controls + (
            f"[{text_contains_actions} or {label_contains_actions} "
            "or @data-testid='hero-list-subnav-actions-menu-button']"
        )
    )
    legacy_locator = (
        By.CSS_SELECTOR,
        "[data-testid*='hero-list-subnav-export-button'] button, "
        "button[data-testid*='hero-list-subnav-export-button']"
    )
    actions_testid_locator = (
        By.CSS_SELECTOR,
        "button[data-testid='hero-list-subnav-actions-menu-button']"
    )

    def find_control(current_driver):
        for locator, is_export in (
            (export_locator, True),
            (legacy_locator, True),
            (actions_testid_locator, False),
            (actions_locator, False)
        ):
            for element in current_driver.find_elements(*locator):
                if element.is_displayed() and element.is_enabled():
                    return element, is_export
        return False

    control, is_export = wait.until(find_control)
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", control)
    if not is_export:
        driver.execute_script("arguments[0].click();", control)
        return wait.until(EC.element_to_be_clickable(export_locator))
    return control

def generate_imdb_exports(driver, wait, directory, sync_watchlist_value, sync_ratings_value, sync_watch_history_value, remove_watched_from_watchlists_value, mark_rated_as_watched_value):
    # Generate IMDB .csv exports
    if not any((sync_watchlist_value, sync_ratings_value, sync_watch_history_value, remove_watched_from_watchlists_value, mark_rated_as_watched_value)):
        return driver, wait
  
    # Generate watchlist export if sync_watchlist_value is True
    if sync_watchlist_value or remove_watched_from_watchlists_value:
        success, status_code, url, driver, wait = EH.get_page_with_retries('https://www.imdb.com/list/watchlist', driver, wait)
        if not success:
            # Page failed to load, raise an exception
            raise PageLoadException(f"Failed to load page. Status code: {status_code}. URL: {url}")

        try:
            export_button = get_export_button(driver, wait)
            # Scroll into view and click the button
            driver.execute_script("arguments[0].scrollIntoView(true);", export_button)
            wait.until(EC.visibility_of(export_button))
            driver.execute_script("arguments[0].click();", export_button)
            time.sleep(3)
        except TimeoutException as exc:
            raise RuntimeError(
                "Could not request an IMDb watchlist export. Sync stopped to avoid using stale or incomplete data."
            ) from exc
    
    # Generate ratings export if sync_ratings_value is True
    if sync_ratings_value or mark_rated_as_watched_value:
        success, status_code, url, driver, wait = EH.get_page_with_retries('https://www.imdb.com/list/ratings', driver, wait)
        if not success:
            # Page failed to load, raise an exception
            raise PageLoadException(f"Failed to load page. Status code: {status_code}. URL: {url}")
        try:
            export_button = get_export_button(driver, wait)
            # Scroll into view and click the button
            driver.execute_script("arguments[0].scrollIntoView(true);", export_button)
            wait.until(EC.visibility_of(export_button))
            driver.execute_script("arguments[0].click();", export_button)
            time.sleep(3)
        except TimeoutException as exc:
            raise RuntimeError(
                "Could not request an IMDb ratings export. Sync stopped to avoid using stale or incomplete data."
            ) from exc
    
    # Generate checkins export if sync_watch_history_value is True
    if sync_watch_history_value or remove_watched_from_watchlists_value or mark_rated_as_watched_value:
        success, status_code, url, driver, wait = EH.get_page_with_retries('https://www.imdb.com/list/checkins', driver, wait)
        if not success:
            # Page failed to load, raise an exception
            raise PageLoadException(f"Failed to load page. Status code: {status_code}. URL: {url}")

        try:
            export_button = get_export_button(driver, wait)
            driver.execute_script("arguments[0].scrollIntoView(true);", export_button)
            wait.until(EC.visibility_of(export_button))
            driver.execute_script("arguments[0].click();", export_button)
            time.sleep(3)
        except TimeoutException as exc:
            raise RuntimeError(
                "Could not request an IMDb check-ins export. Sync stopped to avoid using stale or incomplete data."
            ) from exc
    
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
        
        try:
            # Locate all elements with the selector
            summary_items = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".ipc-metadata-list-summary-item")))
        except TimeoutException as exc:
            raise RuntimeError(
                "No IMDb export jobs appeared after the export requests. Sync stopped; check https://www.imdb.com/exports/."
            ) from exc

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
    
def download_imdb_exports(driver, wait, directory, sync_watchlist_value, sync_ratings_value, sync_watch_history_value, remove_watched_from_watchlists_value, mark_rated_as_watched_value):
    """
    Download IMDB Exports and rename files with correct permissions.
    """
    if not any((sync_watchlist_value, sync_ratings_value, sync_watch_history_value, remove_watched_from_watchlists_value, mark_rated_as_watched_value)):
        return driver, wait

    # Load page
    success, status_code, url, driver, wait = EH.get_page_with_retries('https://www.imdb.com/exports/', driver, wait)
    if not success:
        # Page failed to load, raise an exception
        raise PageLoadException(f"Failed to load page. Status code: {status_code}. URL: {url}")

    # Locate all export blocks
    try:
        summary_items = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".ipc-metadata-list-summary-item")))
    except TimeoutException as exc:
        raise RuntimeError(
            "No IMDb exports are available to download. Sync stopped; check https://www.imdb.com/exports/."
        ) from exc

    # Helper function to find buttons for CSV downloads
    def find_button(item_text):
        for item in summary_items:
            if item_text.lower() in item.text.lower():
                try:
                    button = item.find_element(By.CSS_SELECTOR, "button[data-testid*='export-status-button']")
                    return button
                except NoSuchElementException:
                    print(f"Export button not found for '{item_text}' on IMDB exports page https://www.imdb.com/exports/")
                    return None
        print(f"No section found matching '{item_text}' on IMDB exports page https://www.imdb.com/exports/")
        return None

    # Find download buttons
    watchlist_csv_link = find_button("watchlist") if sync_watchlist_value or remove_watched_from_watchlists_value else None
    ratings_csv_link = find_button("ratings") if sync_ratings_value or mark_rated_as_watched_value else None
    checkins_csv_link = find_button("check-ins") if sync_watch_history_value or remove_watched_from_watchlists_value or mark_rated_as_watched_value else None

    file_mappings = []
    if sync_watchlist_value or remove_watched_from_watchlists_value:
        file_mappings.append((watchlist_csv_link, "watchlist.csv"))
    if sync_ratings_value or mark_rated_as_watched_value:
        file_mappings.append((ratings_csv_link, "ratings.csv"))
    if sync_watch_history_value or remove_watched_from_watchlists_value or mark_rated_as_watched_value:
        file_mappings.append((checkins_csv_link, "checkins.csv"))

    for csv_link, file_name in file_mappings:
        if csv_link is None:
            raise RuntimeError(
                f"Required IMDb export '{file_name}' is unavailable. Sync stopped; check https://www.imdb.com/exports/."
            )
    
    for csv_link, file_name in file_mappings:
        previous_files = set(os.listdir(directory))
        try:
            driver.execute_script("arguments[0].scrollIntoView(true);", csv_link)
            wait.until(EC.visibility_of(csv_link))
            driver.execute_script("arguments[0].click();", csv_link)
            deadline = time.monotonic() + 120
            downloaded_file = None
            while time.monotonic() < deadline:
                new_csvs = [
                    os.path.join(directory, name)
                    for name in os.listdir(directory)
                    if name not in previous_files and name.lower().endswith(".csv")
                ]
                if len(new_csvs) > 1:
                    raise RuntimeError("Multiple new CSV files appeared; cannot identify this export.")
                if new_csvs:
                    downloaded_file = new_csvs[0]
                    break
                time.sleep(1)
            if downloaded_file is None:
                raise RuntimeError("No new CSV download completed within 120 seconds.")
            os.replace(downloaded_file, os.path.join(directory, file_name))
        except Exception as exc:
            raise RuntimeError(f"Could not download IMDb export '{file_name}'. Sync stopped.") from exc

    return driver, wait

def validate_existing_imdb_exports(directory, sync_watchlist_value, sync_ratings_value, sync_watch_history_value, remove_watched_from_watchlists_value, mark_rated_as_watched_value):
    required_exports = {}
    if sync_watchlist_value or remove_watched_from_watchlists_value:
        required_exports["watchlist.csv"] = ["Title", "Year", "Const", "Created", "Title Type"]
    if sync_ratings_value or mark_rated_as_watched_value:
        required_exports["ratings.csv"] = ["Title", "Year", "Your Rating", "Const", "Date Rated", "Title Type"]
    if sync_watch_history_value or remove_watched_from_watchlists_value or mark_rated_as_watched_value:
        required_exports["checkins.csv"] = ["Title", "Year", "Const", "Created", "Title Type"]

    missing_exports = []
    invalid_exports = []
    for file_name, required_columns in required_exports.items():
        file_path = os.path.join(directory, file_name)
        if not os.path.isfile(file_path):
            missing_exports.append(file_name)
            continue

        if os.path.getsize(file_path) == 0:
            continue

        with open(file_path, "r", encoding="utf-8-sig", newline="") as file:
            header = next(csv.reader(file), None)
        if not header:
            invalid_exports.append(f"{file_name} (empty file or missing header)")
            continue

        missing_columns = [column for column in required_columns if column not in header]
        if missing_columns:
            invalid_exports.append(
                f"{file_name} (missing columns: {', '.join(missing_columns)})"
            )

    if missing_exports or invalid_exports:
        details = []
        if missing_exports:
            details.append(f"missing: {', '.join(missing_exports)}")
        if invalid_exports:
            details.append(f"invalid: {'; '.join(invalid_exports)}")
        raise ValueError(
            "Existing IMDb exports are not ready (" + "; ".join(details) + "). "
            f"Download the required CSV exports and place them in: {directory}"
        )

def prepare_imdb_exports(driver, wait, directory, sync_watchlist_value, sync_ratings_value, sync_watch_history_value, remove_watched_from_watchlists_value, mark_rated_as_watched_value, use_existing_exports=False):
    if use_existing_exports:
        validate_existing_imdb_exports(
            directory,
            sync_watchlist_value,
            sync_ratings_value,
            sync_watch_history_value,
            remove_watched_from_watchlists_value,
            mark_rated_as_watched_value
        )
        print(f"Using existing IMDb CSV exports from: {directory}")
        return driver, wait

    driver, wait = generate_imdb_exports(
        driver,
        wait,
        directory,
        sync_watchlist_value,
        sync_ratings_value,
        sync_watch_history_value,
        remove_watched_from_watchlists_value,
        mark_rated_as_watched_value
    )
    return download_imdb_exports(
        driver,
        wait,
        directory,
        sync_watchlist_value,
        sync_ratings_value,
        sync_watch_history_value,
        remove_watched_from_watchlists_value,
        mark_rated_as_watched_value
    )

def get_imdb_watchlist(driver, wait, directory, delete_csv=True):
    # Get IMDB Watchlist Items
    imdb_watchlist = []
    imdb_watchlist_size = 0
    try:          
        # Look for 'watchlist.csv'
        watchlist_filename = 'watchlist.csv'
        watchlist_path = os.path.join(directory, watchlist_filename)

        if not os.path.exists(watchlist_path):
            raise FileNotFoundError(f"IMDB watchlist data not found. '{watchlist_filename}' not found in the directory")

        if os.path.getsize(watchlist_path) == 0:
            print(f"{watchlist_filename} is empty. Assuming the IMDb list is empty.")
            if delete_csv:
                os.remove(watchlist_path)
            return imdb_watchlist, imdb_watchlist_size, driver, wait
        
        # Open and process the 'watchlist.csv' file
        with open(watchlist_path, 'r', encoding='utf-8-sig') as file:
            reader = csv.reader(file)
            header = next(reader)  # Read the header row

            # Create a mapping from header names to their index
            header_index = {column_name: index for index, column_name in enumerate(header)}
            
            required_columns = ["Title", "Year", "Const", "Created", "Title Type"]
            missing_columns = [col for col in required_columns if col not in header_index]
            if missing_columns:
                raise ValueError(f"Required columns missing from CSV file: {', '.join(missing_columns)}")

            for row in reader:
                imdb_watchlist_size += 1
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
        if delete_csv and os.path.exists(watchlist_path):
            os.remove(watchlist_path)
        
    except FileNotFoundError as e:
        imdb_watchlist = []
        imdb_watchlist_size = 0
        error_message = f"{watchlist_filename} file not found. Assuming the IMDB list is empty."
        print(error_message)
        EL.logger.error(error_message, exc_info=True)
        """
        error_message = str(e)
        print(f"Error: {error_message}")
        traceback.print_exc()
        EL.logger.error(error_message, exc_info=True)
        """
    
    except (NoSuchElementException, TimeoutException):
        # No IMDB Watchlist Items
        imdb_watchlist = []
        imdb_watchlist_size = 0
    
    return imdb_watchlist, imdb_watchlist_size, driver, wait

def get_imdb_ratings(driver, wait, directory, delete_csv=True):
    # Get IMDB Ratings
    imdb_ratings = []
    try:
        # Look for 'ratings.csv'
        ratings_filename = 'ratings.csv'
        ratings_path = os.path.join(directory, ratings_filename)

        if not os.path.exists(ratings_path):
            raise FileNotFoundError(f"IMDB ratings data not found. '{ratings_filename}' not found in the directory")

        if os.path.getsize(ratings_path) == 0:
            print(f"{ratings_filename} is empty. Assuming the IMDb list is empty.")
            if delete_csv:
                os.remove(ratings_path)
            return imdb_ratings, driver, wait
        
        # Open and process the 'ratings.csv' file
        with open(ratings_path, 'r', encoding='utf-8-sig') as file:
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
        if delete_csv and os.path.exists(ratings_path):
            os.remove(ratings_path)
        
    except FileNotFoundError as e:
        error_message = f"{ratings_filename} file not found. Assuming the IMDB list is empty."
        print(error_message)
        EL.logger.error(error_message, exc_info=True)
        """
        error_message = str(e)
        print(f"Error: {error_message}")
        traceback.print_exc()
        EL.logger.error(error_message, exc_info=True)
        """
    
    except (NoSuchElementException, TimeoutException):
        # No IMDB Ratings Items
        imdb_ratings = []
        pass
    
    return imdb_ratings, driver, wait
    
def get_imdb_checkins(driver, wait, directory, delete_csv=True):
    # Get IMDB Check-ins
    imdb_checkins = []
    imdb_checkins_size = 0
    try:
        # Look for 'checkins.csv'
        checkins_filename = 'checkins.csv'
        checkins_path = os.path.join(directory, checkins_filename)

        if not os.path.exists(checkins_path):
            raise FileNotFoundError(f"IMDB Check-ins data not found. '{checkins_filename}' not found in the directory")

        if os.path.getsize(checkins_path) == 0:
            print(f"{checkins_filename} is empty. Assuming the IMDb list is empty.")
            if delete_csv:
                os.remove(checkins_path)
            return imdb_checkins, imdb_checkins_size, driver, wait
        
        # Open and process the 'checkins.csv' file
        with open(checkins_path, 'r', encoding='utf-8-sig') as file:
            reader = csv.reader(file)
            header = next(reader)  # Read the header row

            # Create a mapping from header names to their index
            header_index = {column: index for index, column in enumerate(header)}
            
            required_columns = ["Title", "Year", "Const", "Created", "Title Type"]
            missing_columns = [col for col in required_columns if col not in header_index]
            if missing_columns:
                raise ValueError(f"Required columns missing from CSV file: {', '.join(missing_columns)}")

            for row in reader:
                imdb_checkins_size += 1
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
        if delete_csv and os.path.exists(checkins_path):
            os.remove(checkins_path)
        
    except FileNotFoundError as e:
        imdb_checkins = []
        imdb_checkins_size = 0
        error_message = f"{checkins_filename} file not found. Assuming the IMDB list is empty."
        print(error_message)
        EL.logger.error(error_message, exc_info=True)
        """
        error_message = str(e)
        print(f"Error: {error_message}")
        traceback.print_exc()
        EL.logger.error(error_message, exc_info=True)
        """
    
    except (NoSuchElementException, TimeoutException):
        # No IMDB Check-in Items
        imdb_checkins = []
        imdb_checkins_size = 0
    
    return imdb_checkins, imdb_checkins_size, driver, wait
            
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
        reviews_url = driver.current_url + "/reviews/"
        
        # Load page
        success, status_code, url, driver, wait = EH.get_page_with_retries(reviews_url, driver, wait)
        if not success:
            # Page failed to load, raise an exception
            raise PageLoadException(f"Failed to load page. Status code: {status_code}. URL: {url}")
            
        while True:
            try:
                try:
                    review_elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div[data-testid='review-card-parent']")))
                except (NoSuchElementException, TimeoutException):
                    # No review elements found. There are no reviews. Exit the loop without an error.
                    error_message = "No review elements found. There are no reviews. Exit the loop without an error."
                    EL.logger.error(error_message, exc_info=True)
                    break
                
                for element in review_elements:
                    review = {}
                    # Extract review details
                    review['Title'] = element.find_element(By.CSS_SELECTOR, "div[data-testid='review-title-header'] h4 span").text.strip()
                    date_text = element.find_element(By.CSS_SELECTOR, "li.review-date").text
                    review['Year'] = int(date_text.strip().split()[-1]) if date_text else None
                    review['IMDB_ID'] = element.find_element(By.CSS_SELECTOR, "div[data-testid='review-summary'] a").get_attribute("href").split('/')[4]
                    review['IMDBReviewID'] = element.find_element(By.CSS_SELECTOR, "div[data-testid='review-summary'] a").get_attribute("href").split('/')[6]
                    review['Comment'] = element.find_element(By.CSS_SELECTOR, "div[data-testid='review-overflow']").text.strip()
                    spoiler_warning_elements = element.find_elements(By.CSS_SELECTOR, ".review-spoiler-button")
                    review['Spoiler'] = len(spoiler_warning_elements) > 0
                    # Get the media type using Trakt API
                    media_type = get_media_type(review['IMDB_ID'])
                    if media_type:
                        review['Type'] = media_type
                    else:
                        review['Type'] = 'unknown'

                    # if review['Type'] != 'unknown':
                    reviews.append(review)
                    
                try:
                    # Check if "Next" link exists
                    next_link = driver.find_element(By.CSS_SELECTOR, "div[data-testid='index-pagination-nxt']")
                    # Get the 'aria-disabled' attribute
                    is_disabled = next_link.get_attribute("aria-disabled")
                    
                    if is_disabled is None or is_disabled == "true":
                        break  # No more pages, exit the loop
                    
                    # Get the current url before clicking the "Next" link
                    current_url = driver.current_url
                    
                    # Click the "Next" link
                    # Scroll into view and click the button
                    driver.execute_script("arguments[0].scrollIntoView(true);", next_link)
                    wait.until(EC.visibility_of(next_link))
                    driver.execute_script("arguments[0].click();", next_link)

                    # Wait until the URL changes
                    wait.until(lambda driver: driver.current_url != current_url)
                    
                    # Refresh review_elements
                    review_elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div[data-testid='review-card-parent']")))

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
            except EH.IMDbHTTP405Exception:
                raise
            except Exception as e:
                errors_found_getting_imdb_reviews = True
                error_message = f"Exception occurred while getting IMDB reviews: {type(e)}"
                print(f"{error_message}")
                EL.logger.error(error_message, exc_info=True)
                break
    
    except EH.IMDbHTTP405Exception:
        raise
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