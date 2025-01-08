import os
import requests
import zipfile
import shutil
import platform
import sys
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from IMDBTraktSyncer import errorHandling as EH
from IMDBTraktSyncer import errorLogger as EL

def get_main_directory():
    directory = os.path.dirname(os.path.realpath(__file__))
    return directory
    
def remove_read_only_attribute(path: Path):
    # Recursively remove read-only attribute from a folder and its contents
    for root, dirs, files in os.walk(path):
        for item in dirs + files:
            item_path = Path(root) / item
            item_path.chmod(item_path.stat().st_mode | 0o200)  # Remove read-only attribute

def get_user_data_directory():
    directory = os.path.dirname(os.path.realpath(__file__))  # Current script's directory
    version = get_latest_stable_version()  # Assuming this function exists and returns a version string

    # Path to the version directory
    version_directory = Path(directory) / "Chrome" / version

    # Automatically detect the Chrome binary directory
    chrome_binary_directory = None
    for subfolder in version_directory.iterdir():
        if subfolder.is_dir():  # Check only directories
            chrome_binary_directory = subfolder.name
            break  # Assume there's only one Chrome binary directory

    if not chrome_binary_directory:
        raise FileNotFoundError(f"No Chrome binary directory found under {version_directory}")

    # Define the user data directory path
    user_data_directory = version_directory / chrome_binary_directory / "user-data"

    # Create the directory if it doesn't exist
    user_data_directory.mkdir(parents=True, exist_ok=True)

    # Remove "read-only" attribute from the user data directory and all its contents
    remove_read_only_attribute(user_data_directory)

    return user_data_directory

def get_latest_stable_version():
    # Step 1: Get the latest stable version
    stable_url = "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions.json"
    stable_response = EH.make_request_with_retries(stable_url)
    stable_response.raise_for_status()
    stable_data = stable_response.json()
    stable_version = stable_data['channels']['Stable']['version']
    
    return stable_version
    
def get_version_data(version):
    # Step 1: Fetch the data from the URL
    versions_url = "https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json"
    response = EH.make_request_with_retries(versions_url)
    response.raise_for_status()
    data = response.json()

    # Step 2: Search for the specified version
    for entry in data["versions"]:
        if entry["version"] == version:
            # Step 3: Return data for the matching version
            return entry
    
    # Step 4: If version is not found, return None
    return None

def get_platform():
    system = platform.system().lower()
    arch = platform.machine().lower()

    if system == "windows":
        return "win64" if "64" in arch else "win32"
    elif system == "darwin":
        return "mac-arm64" if "arm" in arch else "mac-x64"
    elif system == "linux":
        return "linux64"
    else:
        raise ValueError("Unsupported operating system")

def is_chrome_up_to_date(main_directory, current_version):
    chrome_dir = Path(main_directory) / "Chrome" / current_version
    
    if not chrome_dir.exists():
        # Chrome directory for version not found. Chrome not downloaded or not up to date.
        return False

    # Check for the Chrome binary depending on the platform
    platform_binary = {
        "win32": ["chrome-headless-shell.exe", "chrome.exe"],  # Two possible filenames for Windows
        "win64": ["chrome-headless-shell.exe", "chrome.exe"],  # Two possible filenames for Windows
        "mac-arm64": ["chrome-headless-shell", "chrome"],  # Two possible filenames for macOS
        "mac-x64": ["chrome-headless-shell", "chrome"],  # Two possible filenames for macOS
        "linux64": ["chrome-headless-shell", "chrome"],  # Two possible filenames for Linux
    }

    platform_key = get_platform()
    binary_names = platform_binary.get(platform_key, ["chrome-headless-shell", "chrome"])  # Default to both names

    # Handle the additional subfolder under version
    for subfolder in chrome_dir.iterdir():
        if subfolder.is_dir():
            # Check both possible filenames
            for binary_name in binary_names:
                binary_path = subfolder / binary_name
                if binary_path.exists():
                    return True

    print(f"Chrome binary not found under {chrome_dir}.")
    return False

def download_and_extract_chrome(download_url, main_directory, version, max_wait_time=30, wait_interval=5):
    zip_path = Path(main_directory) / f"chrome-{version}.zip"
    extract_path = Path(main_directory) / "Chrome" / version

    # Ensure the main directory exists
    Path(main_directory).mkdir(parents=True, exist_ok=True)

    try:
        # Download the zip file
        response = EH.make_request_with_retries(download_url, stream=True)
        response.raise_for_status()

        # Get the expected file size from the response headers (if available)
        expected_file_size = int(response.headers.get('Content-Length', 0))
        print(f" - Expected file size: {expected_file_size} bytes")

        # Write the zip file to disk (wait until it's fully downloaded)
        with open(zip_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)

        # Check if the actual downloaded file size matches the expected file size
        actual_file_size = zip_path.stat().st_size
        print(f" - Downloaded file size: {actual_file_size} bytes")

        # Retry if file sizes don't match
        time_waited = 0
        while expected_file_size and actual_file_size != expected_file_size and time_waited < max_wait_time:
            print(f" - File size mismatch. Waiting for {wait_interval} seconds before checking again...")
            time.sleep(wait_interval)
            time_waited += wait_interval
            actual_file_size = zip_path.stat().st_size
            print(f" - Downloaded file size (after waiting): {actual_file_size} bytes")

        if expected_file_size and actual_file_size != expected_file_size:
            raise RuntimeError(f" - Downloaded file size mismatch: expected {expected_file_size} bytes, got {actual_file_size} bytes")

        # Add small delay to ensure the file is closed and ready for extraction
        time.sleep(5)

        # Extract the zip file
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_path)

        print(f" - Extraction complete to: {extract_path}")
        
        # Remove read-only attribute from the extracted folder
        remove_read_only_attribute(extract_path)

    except Exception as e:
        raise RuntimeError(f" - Failed to download or extract Chrome version {version}: {e}")

    finally:
        # Ensure the zip file is deleted after extraction
        time.sleep(5)  # Small delay to ensure all file handles are closed
        try:
            if zip_path.exists():
                zip_path.unlink()
                print(f" - File {zip_path} deleted.")

            # Find and delete other .zip files containing 'chrome' (case-insensitive) in the same directory
            for file in Path(main_directory).glob("*.zip"):
                if "chrome" in file.name.lower():
                    try:
                        file.unlink()
                        print(f" - Deleted file: {file}")
                    except Exception as e:
                        print(f" - Failed to delete file {file}: {e}")

        except PermissionError:
            print(f" - Permission denied when trying to delete {zip_path}. Ensure no other process is using it.")
        except Exception as e:
            print(f" - Unexpected error while deleting {zip_path}: {e}")

    return extract_path

def remove_old_versions(main_directory, latest_version):
    chrome_dir = Path(main_directory) / "Chrome"

    for version_dir in chrome_dir.iterdir():
        if version_dir.is_dir() and version_dir.name != latest_version:
            print(f"Removing old Chrome version: {version_dir.name}...")
            
            # Remove read-only attribute before deleting the directory
            remove_read_only_attribute(version_dir)
            
            # Now safely remove the old version
            shutil.rmtree(version_dir)

def get_chrome_binary_path(main_directory):
    version = get_latest_stable_version()

    chrome_dir = Path(main_directory) / "Chrome" / version
    
    if not chrome_dir.exists():
        raise FileNotFoundError(f"Chrome version {version} not found in {chrome_dir}")

    # Define possible binary names for each platform
    platform_binary = {
        "win32": ["chrome.exe", "chrome-headless-shell.exe"],  # Windows binaries
        "win64": ["chrome.exe", "chrome-headless-shell.exe"],  # Windows binaries
        "mac-arm64": ["chrome", "chrome-headless-shell"],      # macOS binaries
        "mac-x64": ["chrome", "chrome-headless-shell"],        # macOS binaries
        "linux64": ["chrome", "chrome-headless-shell"],        # Linux binaries
    }

    platform_key = get_platform()
    binary_names = platform_binary.get(platform_key, ["chrome", "chrome-headless-shell"])  # Default to both names

    # Look for the binary in the version directory
    for subfolder in chrome_dir.iterdir():
        if subfolder.is_dir():
            for binary_name in binary_names:
                binary_path = subfolder / binary_name
                if binary_path.exists():  # Check if the binary file exists
                    return str(binary_path)

    raise FileNotFoundError(f"Chrome binary not found under {chrome_dir}.")
    
def create_chrome_directory(main_directory):
    chrome_dir = Path(main_directory) / "Chrome"
    
    if not chrome_dir.exists():
        chrome_dir.mkdir(exist_ok=True)

    return chrome_dir
    
def delete_chromedriver_cache():
    try:
        # Get the path to the chromedriver cache directory
        if platform.system() == "Windows":
            # Use the 'USERPROFILE' environment variable to get the correct user folder on Windows
            user_profile = os.environ.get('USERPROFILE', '')
            chromedriver_cache = os.path.join(user_profile, '.cache', 'selenium', 'chromedriver')
        else:
            # On macOS/Linux, use the home directory
            chromedriver_cache = os.path.expanduser('~/.cache/selenium/chromedriver')

        # Check if the path exists
        if os.path.exists(chromedriver_cache):
            # Iterate through the folder and delete all files and subdirectories
            for root, dirs, files in os.walk(chromedriver_cache, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    shutil.rmtree(os.path.join(root, name))
            print(f"Selenium Chromedriver cache cleared at: {chromedriver_cache}")
        else:
            print(f"The path {chromedriver_cache} does not exist.")

    except Exception as e:
        print(f"An error occurred: {e}")

def checkChrome():
    main_directory = get_main_directory()
    
    #browser_type = "chrome"
    browser_type = "chrome-headless-shell"

    # Get latest version details
    latest_version = get_latest_stable_version()
    platform_key = get_platform()
    latest_version_data = get_version_data(latest_version)

    # Create Chrome directory if it doesn't exist
    create_chrome_directory(main_directory)
    
    # Always remove old versions, even if the latest version is already downloaded
    remove_old_versions(main_directory, latest_version)

    # Check if the latest version is already downloaded
    if is_chrome_up_to_date(main_directory, latest_version):
        # Chrome is already up to date
        # print(f"Chrome version {latest_version} is already up to date.")
        return

    # Get the download URL for the relevant platform
    download_url = None

    for entry in latest_version_data['downloads'][browser_type]:
        if entry['platform'] == platform_key:
            download_url = entry['url']
            break

    if not download_url:
        raise ValueError(f"No download available for platform {platform_key}")

    # Download and extract the latest version of Chrome
    print(f"Downloading Chrome version {latest_version}...")
    download_and_extract_chrome(download_url, main_directory, latest_version)
    print(f"Chrome version {latest_version} downloaded successfully.")
    
    # Clear the Chromedriver cache after downloading the new version of Chrome
    delete_chromedriver_cache()