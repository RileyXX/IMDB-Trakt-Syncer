import os
import requests
import zipfile
import shutil
import platform
import sys
import time
import subprocess
import tempfile
import stat
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from IMDBTraktSyncer import errorHandling as EH

def get_main_directory():
    directory = os.path.dirname(os.path.realpath(__file__))
    return directory
    
def get_browser_type():
    # Change browser type
    # Valid options: "chrome" or "chrome-headless-shell"
    browser_type = "chrome"
    
    # Run headless setting
    # Valid options: True or False
    headless = True
    
    return browser_type, headless

def try_remove(file_path, retries=3, delay=1):
    """
    Tries to remove a file or directory, retrying if it's in use or read-only.

    :param file_path: The path of the file or directory to be removed.
    :param retries: Number of retries before giving up.
    :param delay: Time in seconds between retries.
    :return: True if the file/directory is successfully removed, False otherwise.
    """
    for attempt in range(retries):
        try:
            if os.path.isdir(file_path):
                # Ensure the directory and its contents are writable
                for root, dirs, files in os.walk(file_path, topdown=False):
                    for name in files:
                        file = os.path.join(root, name)
                        if sys.platform != 'win32':  # chmod on Linux/macOS
                            os.chmod(file, 0o777)  # Make file writable
                        os.remove(file)
                    for name in dirs:
                        folder = os.path.join(root, name)
                        if sys.platform != 'win32':  # chmod on Linux/macOS
                            os.chmod(folder, 0o777)  # Make folder writable
                        os.rmdir(folder)

                if sys.platform != 'win32':  # chmod on Linux/macOS
                    os.chmod(file_path, 0o777)  # Make the top-level folder writable
                os.rmdir(file_path)  # Finally, remove the directory
            else:
                # It's a file, ensure it's writable and remove it
                if sys.platform != 'win32':  # chmod on Linux/macOS
                    os.chmod(file_path, 0o777)  # Make it writable
                os.remove(file_path)

            print(f"Successfully removed: {file_path}")
            return True
        except PermissionError:
            print(f"Permission error for {file_path}, retrying...")
        except Exception as e:
            print(f"Error removing {file_path}: {e}")

        time.sleep(delay)

    # If running on Windows, handle read-only files
    if sys.platform == 'win32':
        try:
            # Remove read-only attribute on Windows
            if os.path.exists(file_path):
                os.chmod(file_path, stat.S_IWRITE)  # Remove read-only attribute
                if os.path.isdir(file_path):
                    shutil.rmtree(file_path)  # Remove non-empty directory
                else:
                    os.remove(file_path)
            print(f"Successfully removed (after read-only fix): {file_path}")
            return True
        except Exception as e:
            print(f"Error removing {file_path} on Windows: {e}")

    return False
    
def grant_permissions(path: Path):
    """
    Recursively remove read-only attribute from a folder and its contents.
    Ensures directories are accessible (add execute permission) and files are executable where needed.
    Compatible with macOS, Linux, and Windows.
    """
    # Determine the operating system
    is_windows = sys.platform.startswith('win')

    for root, dirs, files in os.walk(path):
        for item in dirs + files:
            item_path = Path(root) / item
            try:
                # For Windows: Ensure the file is not read-only
                if is_windows:
                    # Set the read-only attribute to False for files (Windows)
                    os.chmod(item_path, item_path.stat().st_mode & ~stat.S_IREAD)  # Remove read-only attribute
                else:
                    # For Linux/macOS, add write permissions
                    current_permissions = item_path.stat().st_mode
                    item_path.chmod(current_permissions | 0o777)  # Add write permission (u+w)

                    # Ensure directories are executable
                    if item_path.is_dir():
                        item_path.chmod(current_permissions | 0o777)  # Add execute permission (u+x) for directories
                    else:
                        # For files (including chromedriver), make sure they are executable
                        item_path.chmod(current_permissions | 0o777)  # Add execute permission (u+x, g+x, o+x) for files

            except PermissionError:
                print(f"Permission denied: Unable to modify {item_path}")
            except Exception as e:
                print(f"Error modifying permissions for {item_path}: {e}")

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
    user_data_directory = version_directory / chrome_binary_directory / "userData"

    # Create the directory if it doesn't exist
    user_data_directory.mkdir(parents=True, exist_ok=True)

    # Remove "read-only" attribute
    grant_permissions(user_data_directory)

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
        "mac-arm64": ["chrome-headless-shell", "Google Chrome for Testing"],  # Two possible filenames for macOS
        "mac-x64": ["chrome-headless-shell", "Google Chrome for Testing"],  # Two possible filenames for macOS
        "linux64": ["chrome-headless-shell", "chrome"]  # Two possible filenames for Linux
    }

    platform_key = get_platform()
    binary_names = platform_binary.get(platform_key, ["chrome-headless-shell", "chrome"])  # Default to both names
                
    # Logic for macOS special cases
    if platform_key in ["mac-arm64", "mac-x64"]:
        for subfolder in chrome_dir.iterdir():
            if subfolder.is_dir():
                for binary_name in binary_names:
                    if binary_name == "Google Chrome for Testing":
                        # For macOS regular Chrome, the binary is inside the .app bundle in the version directory
                        binary_path = chrome_dir / subfolder / "Google Chrome for Testing.app" / "Contents" / "MacOS" / "Google Chrome for Testing"
                    else:
                        # For macOS headless shell, the binary is directly under the version directory
                        binary_path = chrome_dir / subfolder / binary_name

                    if binary_path.exists():
                        return True

    # General case for other platforms
    for subfolder in chrome_dir.iterdir():
        if subfolder.is_dir():
            for binary_name in binary_names:
                binary_path = subfolder / binary_name
                if binary_path.exists():  # Check if the binary file exists
                    return True

    print(f"Chrome binary not found under {chrome_dir}.")
    return False
    
def is_chromedriver_up_to_date(main_directory, current_version):
    chromedriver_dir = Path(main_directory) / "Chromedriver" / current_version
    
    if not chromedriver_dir.exists():
        # Chromedriver directory for version not found. Chrome not downloaded or not up to date.
        return False

    # Check for the Chromedriver binary depending on the platform
    platform_binary = {
        "win32": ["chromedriver.exe"],  # Two possible filenames for Windows
        "win64": ["chromedriver.exe"],  # Two possible filenames for Windows
        "mac-arm64": ["chromedriver"],  # Two possible filenames for macOS
        "mac-x64": ["chromedriver"],  # Two possible filenames for macOS
        "linux64": ["chromedriver"],  # Two possible filenames for Linux
    }

    platform_key = get_platform()
    binary_names = platform_binary.get(platform_key, ["chromedriver"])  # Default to chromedriver

    # Handle the additional subfolder under version
    for subfolder in chromedriver_dir.iterdir():
        if subfolder.is_dir():
            # Check both possible filenames
            for binary_name in binary_names:
                binary_path = subfolder / binary_name
                if binary_path.exists():
                    return True

    print(f"Chromedriver binary not found under {chromedriver_dir}.")
    return False

def download_and_extract_chrome(download_url, main_directory, version, max_wait_time=300, wait_interval=5):
    temp_dir = tempfile.gettempdir()  # Use a temporary directory for the download
    temp_zip_path = Path(temp_dir) / f"chrome-{version}.zip"
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

        # Write the zip file to a temporary location
        with open(temp_zip_path, "wb") as temp_file:
            for chunk in response.iter_content(chunk_size=8192):
                temp_file.write(chunk)

        # Validate the downloaded file size
        actual_file_size = temp_zip_path.stat().st_size
        print(f" - Downloaded file size: {actual_file_size} bytes")

        # Retry until file sizes match or timeout occurs
        time_waited = 0
        while expected_file_size and actual_file_size != expected_file_size and time_waited < max_wait_time:
            print(f" - File size mismatch. Waiting for {wait_interval} seconds before checking again...")
            time.sleep(wait_interval)
            time_waited += wait_interval
            actual_file_size = temp_zip_path.stat().st_size
            print(f" - Downloaded file size (after waiting): {actual_file_size} bytes")

        if expected_file_size and actual_file_size != expected_file_size:
            raise RuntimeError(f" - Downloaded file size mismatch: expected {expected_file_size} bytes, got {actual_file_size} bytes")

        # Move the temp file to the final location
        shutil.move(str(temp_zip_path), str(zip_path))
        print(f" - Download complete. File moved to: {zip_path}")

        # Verify the integrity of the ZIP file before extraction
        if not zipfile.is_zipfile(zip_path):
            raise RuntimeError(f" - The downloaded file is not a valid ZIP archive: {zip_path}")

        # Extract the zip file
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_path)

        print(f" - Extraction complete to: {extract_path}")
        
        # Remove read-only attribute from the extracted folder
        grant_permissions(extract_path)

    except Exception as e:
        raise RuntimeError(f" - Failed to download or extract Chrome version {version}: {e}")

    finally:
        # Cleanup the ZIP file
        try:
            if zip_path.exists():
                zip_path.unlink()
                print(f" - File {zip_path} deleted.")

            # Remove any stray .zip files in the directory
            for file in Path(main_directory).glob("*.zip"):
                if "chrome-" in file.name.lower():
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
    
def download_and_extract_chromedriver(download_url, main_directory, version, max_wait_time=300, wait_interval=5):
    temp_dir = tempfile.gettempdir()  # Use a temporary directory for the download
    temp_zip_path = Path(temp_dir) / f"chromedriver-{version}.zip"
    zip_path = Path(main_directory) / f"chromedriver-{version}.zip"
    extract_path = Path(main_directory) / "Chromedriver" / version

    # Ensure the main directory exists
    Path(main_directory).mkdir(parents=True, exist_ok=True)

    try:
        # Download the zip file
        response = EH.make_request_with_retries(download_url, stream=True)
        response.raise_for_status()

        # Get the expected file size from the response headers (if available)
        expected_file_size = int(response.headers.get('Content-Length', 0))
        print(f" - Expected file size: {expected_file_size} bytes")

        # Write the zip file to a temporary location
        with open(temp_zip_path, "wb") as temp_file:
            for chunk in response.iter_content(chunk_size=8192):
                temp_file.write(chunk)

        # Validate the downloaded file size
        actual_file_size = temp_zip_path.stat().st_size
        print(f" - Downloaded file size: {actual_file_size} bytes")

        # Retry until file sizes match or timeout occurs
        time_waited = 0
        while expected_file_size and actual_file_size != expected_file_size and time_waited < max_wait_time:
            print(f" - File size mismatch. Waiting for {wait_interval} seconds before checking again...")
            time.sleep(wait_interval)
            time_waited += wait_interval
            actual_file_size = temp_zip_path.stat().st_size
            print(f" - Downloaded file size (after waiting): {actual_file_size} bytes")

        if expected_file_size and actual_file_size != expected_file_size:
            raise RuntimeError(f" - Downloaded file size mismatch: expected {expected_file_size} bytes, got {actual_file_size} bytes")

        # Move the temp file to the final location
        shutil.move(str(temp_zip_path), str(zip_path))
        print(f" - Download complete. File moved to: {zip_path}")

        # Verify the integrity of the ZIP file before extraction
        if not zipfile.is_zipfile(zip_path):
            raise RuntimeError(f" - The downloaded file is not a valid ZIP archive: {zip_path}")

        # Extract the zip file
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_path)

        print(f" - Extraction complete to: {extract_path}")
        
        # Remove read-only attribute from the extracted folder
        grant_permissions(extract_path)

    except Exception as e:
        raise RuntimeError(f" - Failed to download or extract Chromedriver version {version}: {e}")

    finally:
        # Clean up extracted files (excluding the chromedriver executable)
        try:
            # Get the path to the extracted directory
            chromedriver_dir = Path(extract_path)

            # Clean up all files except the chromedriver executable
            if chromedriver_dir.exists():
                for item in chromedriver_dir.iterdir():
                    # Check if the item is a subfolder (assumed to be the one containing the binary files)
                    if item.is_dir():
                        subfolder = item
                        # Now, clean up files inside the subfolder
                        for sub_item in subfolder.iterdir():
                            # Skip deleting chromedriver executable
                            if sub_item.name.lower() in ["chromedriver.exe", "chromedriver"]:
                                continue
                            try_remove(sub_item)  # Remove other files

            # Cleanup the ZIP file
            if zip_path.exists():
                zip_path.unlink()
                print(f" - File {zip_path} deleted.")

            # Remove any stray .zip files in the directory
            for file in Path(main_directory).glob("*.zip"):
                if "chromedriver-" in file.name.lower():
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

def remove_old_versions(main_directory, latest_version, browser_type):
    chrome_dir = Path(main_directory) / "Chrome"
    chromedriver_dir = Path(main_directory) / "Chromedriver"

    # Delete downloaded browser if not the correct type (chrome vs chrome-headless-shell)
    if browser_type == "chrome":
        for version_dir in chrome_dir.iterdir():
            if version_dir.is_dir():
                for sub_dir in version_dir.iterdir():
                    if sub_dir.is_dir():
                        # All platforms (including macOS) use the same path for chrome-headless-shell
                        headless_shell_path = sub_dir / "chrome-headless-shell" if os.name != "nt" else sub_dir / "chrome-headless-shell.exe"
                        
                        if headless_shell_path.exists():
                            print(f"chrome-headless-shell found in {headless_shell_path}, but script is set to use regular Chrome. Removing entire contents of {chrome_dir}...")
                            try_remove(version_dir)
                            return  # Exit the function after removal
    elif browser_type == "chrome-headless-shell":
        for version_dir in chrome_dir.iterdir():
            if version_dir.is_dir():
                for sub_dir in version_dir.iterdir():
                    if sub_dir.is_dir():
                        # macOS-specific path for regular Chrome binary
                        if os.name == "posix":  # macOS
                            chrome_path = sub_dir / "Google Chrome for Testing.app" / "Contents" / "MacOS" / "Google Chrome for Testing"
                        else:  # Windows or Linux
                            chrome_path = sub_dir / "chrome" if os.name != "nt" else sub_dir / "chrome.exe"
                        
                        if chrome_path.exists():
                            print(f"Chrome found in {chrome_path}, but script is set to use chrome-headless-shell. Removing entire contents of {chrome_dir}...")
                            try_remove(version_dir)
                            return  # Exit the function after removal

    # Remove old versions for "chrome" or "chrome-headless-shell"
    for version_dir in chrome_dir.iterdir():
        if version_dir.is_dir() and version_dir.name != latest_version:
            print(f"Removing old Chrome version: {version_dir.name}...")
            try_remove(version_dir)

    for version_dir in chromedriver_dir.iterdir():
        if version_dir.is_dir() and version_dir.name != latest_version:
            print(f"Removing old Chromedriver version: {version_dir.name}...")
            try_remove(version_dir)

def get_chrome_binary_path(main_directory):
    version = get_latest_stable_version()

    # Build the path to the version directory
    chrome_dir = Path(main_directory) / "Chrome" / version

    if not chrome_dir.exists():
        raise FileNotFoundError(f"Chrome version {version} not found in {chrome_dir}")

    # Define possible binary names for each platform
    platform_binary = {
        "win32": ["chrome-headless-shell.exe", "chrome.exe"],  # Two possible filenames for Windows
        "win64": ["chrome-headless-shell.exe", "chrome.exe"],  # Two possible filenames for Windows
        "mac-arm64": ["chrome-headless-shell", "Google Chrome for Testing"],  # Updated for macOS
        "mac-x64": ["chrome-headless-shell", "Google Chrome for Testing"],  # Updated for macOS
        "linux64": ["chrome-headless-shell", "chrome"]  # Two possible filenames for Linux
    }

    platform_key = get_platform()  # Get the platform key (e.g., win32, mac-arm64, etc.)
    binary_names = platform_binary.get(platform_key, ["chrome-headless-shell", "chrome"])  # Default to both names

    # Logic for macOS special cases
    if platform_key in ["mac-arm64", "mac-x64"]:
        for subfolder in chrome_dir.iterdir():
            if subfolder.is_dir():
                for binary_name in binary_names:
                    if binary_name == "Google Chrome for Testing":
                        # For macOS regular Chrome, the binary is inside the .app bundle in the version directory
                        binary_path = chrome_dir / subfolder / "Google Chrome for Testing.app" / "Contents" / "MacOS" / "Google Chrome for Testing"
                    else:
                        # For macOS headless shell, the binary is directly under the version directory
                        binary_path = chrome_dir / subfolder / binary_name

                    if binary_path.exists():
                        return str(binary_path)

    # General case for other platforms
    for subfolder in chrome_dir.iterdir():
        if subfolder.is_dir():
            for binary_name in binary_names:
                binary_path = subfolder / binary_name
                if binary_path.exists():  # Check if the binary file exists
                    return str(binary_path)

    raise FileNotFoundError(f"No valid Chrome binary found for platform {platform_key} in {chrome_dir}")
    
def get_chromedriver_binary_path(main_directory):
    version = get_latest_stable_version()

    chromedriver_dir = Path(main_directory) / "Chromedriver" / version
    
    if not chromedriver_dir.exists():
        raise FileNotFoundError(f"Chromedriver version {version} not found in {chromedriver_dir}")

    # Define possible binary names for each platform
    platform_binary = {
        "win32": ["chromedriver.exe"],  # Windows binaries
        "win64": ["chromedriver.exe"],  # Windows binaries
        "mac-arm64": ["chromedriver"],      # macOS binaries
        "mac-x64": ["chromedriver"],        # macOS binaries
        "linux64": ["chromedriver"],        # Linux binaries
    }

    platform_key = get_platform()
    binary_names = platform_binary.get(platform_key, ["chromedriver"])  # Default to chromedriver

    # Look for the binary in the version directory
    for subfolder in chromedriver_dir.iterdir():
        if subfolder.is_dir():
            for binary_name in binary_names:
                binary_path = subfolder / binary_name
                if binary_path.exists():  # Check if the binary file exists
                    return str(binary_path)

    raise FileNotFoundError(f"Chromedriver binary not found under {chromedriver_dir}.")
    
def create_chrome_directory(main_directory):
    chrome_dir = Path(main_directory) / "Chrome"
    
    if not chrome_dir.exists():
        chrome_dir.mkdir(exist_ok=True)

    return chrome_dir
    
def create_chromedriver_directory(main_directory):
    chrome_dir = Path(main_directory) / "Chromedriver"
    
    if not chrome_dir.exists():
        chrome_dir.mkdir(exist_ok=True)

    return chrome_dir
    
def get_selenium_install_location():
    try:
        # Use pip show to get Selenium installation details
        result = subprocess.run([sys.executable, '-m', 'pip', 'show', 'selenium'], 
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        for line in result.stdout.splitlines():
            if line.startswith("Location:"):
                site_packages_directory = line.split("Location:")[1].strip()
                selenium_directory = os.path.join(site_packages_directory, 'selenium')
                return selenium_directory
    except Exception as e:
        print("Error finding Selenium install location using pip show:", e)
        return None

def clear_selenium_manager_cache():
    try:
        # Get the Selenium install location
        selenium_install_location = get_selenium_install_location()
        if not selenium_install_location:
            print("Could not determine Selenium install location. Skipping cache clear.")
            return

        webdriver_common_path = os.path.join(selenium_install_location, "webdriver", "common")
        
        # Determine the OS and set the appropriate folder and file name
        os_name = platform.system().lower()

        if os_name == "windows":
            selenium_manager_path = os.path.join(webdriver_common_path, "windows", "selenium-manager.exe")
        elif os_name == "linux":
            selenium_manager_path = os.path.join(webdriver_common_path, "linux", "selenium-manager")
        elif os_name == "darwin":  # macOS
            selenium_manager_path = os.path.join(webdriver_common_path, "macos", "selenium-manager")
        else:
            print("Unsupported operating system.")
            return

        # Ensure the Selenium Manager file exists
        if not os.path.isfile(selenium_manager_path):
            print(f"Selenium Manager file not found at: {selenium_manager_path}")
            return

        # Build the command
        command = f"{selenium_manager_path} --clear-cache --browser chrome --driver chromedriver"

        try:
            # Run the command
            result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            print("Selenium Chromedriver cache cleared")
        except subprocess.CalledProcessError as e:
            print("Error running Selenium Manager command:", e.stderr)
    except Exception as e:
        print("An unexpected error occurred:", e)

def checkChrome():
    main_directory = get_main_directory()
    
    browser_type, _ = get_browser_type()

    # Get latest version details
    latest_version = get_latest_stable_version()
    platform_key = get_platform()
    latest_version_data = get_version_data(latest_version)

    # Create Chrome directory if it doesn't exist
    create_chrome_directory(main_directory)
    
    # Create Chromedriver directory if it doesn't exist
    create_chromedriver_directory(main_directory)
    
    # Always remove old versions, even if the latest version is already downloaded
    remove_old_versions(main_directory, latest_version, browser_type)
    
    # Remove "read-only" attribute
    grant_permissions(main_directory)

    # Check if the latest versions of Chrome and Chromedriver are already downloaded
    if is_chrome_up_to_date(main_directory, latest_version) and is_chromedriver_up_to_date(main_directory, latest_version):
        # Chrome and Chromedriver are already up to date
        return

    # Get the Chrome download URL for the relevant platform
    chrome_download_url = None

    for entry in latest_version_data['downloads'][browser_type]:
        if entry['platform'] == platform_key:
            chrome_download_url = entry['url']
            break

    if not chrome_download_url:
        raise ValueError(f"No download available for platform {platform_key}")
        
    # Get the Chromedriver download URL for the relevant platform
    chromedriver_download_url = None

    for entry in latest_version_data['downloads']["chromedriver"]:
        if entry['platform'] == platform_key:
            chromedriver_download_url = entry['url']
            break

    if not chromedriver_download_url:
        raise ValueError(f"No download available for platform {platform_key}")

    # Download and extract the latest version of Chrome
    print(f"Downloading Chrome version {latest_version}...")
    download_and_extract_chrome(chrome_download_url, main_directory, latest_version)
    print(f"Chrome version {latest_version} downloaded successfully.")
    
    # Download and extract the latest version of Chromedriver
    print(f"Downloading Chromedriver version {latest_version}...")
    download_and_extract_chromedriver(chromedriver_download_url, main_directory, latest_version)
    print(f"Chromedriver version {latest_version} downloaded successfully.")
    
    # Clear the Chromedriver cache after downloading the new version of Chrome
    clear_selenium_manager_cache()