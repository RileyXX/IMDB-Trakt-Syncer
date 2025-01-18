import time
import sys
import shutil
import subprocess
import os
import platform
import stat

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

def clear_user_data(main_directory):
    """
    Deletes the credentials.txt file and Chrome user data directories under the given main directory.

    :param main_directory: Directory path where credentials.txt and user data should be deleted.
    """
    credentials_path = os.path.join(main_directory, "credentials.txt")

    if os.path.exists(credentials_path):
        # Remove the credentials.txt file
        try_remove(credentials_path)

    # Construct the Chrome user data directory path dynamically
    chrome_directory = os.path.join(main_directory, "Chrome")
    user_data_found = False
    
    if os.path.exists(chrome_directory):
        for root, dirs, files in os.walk(chrome_directory):
            for dir_name in dirs:
                if dir_name == "userData":
                    user_data_directory = os.path.join(root, dir_name)
                    user_data_found = True
                    break
        
    if user_data_found:
        try_remove(user_data_directory)

    print("Clear user data complete.")

def clear_cache(main_directory):
    """
    Deletes all folders, .zip files, .txt files (except credentials.txt) in the given directory and clears selenium chromedriver cache.
    
    :param main_directory: Directory path where data should be cleared.
    """
    # Check if the given directory exists
    if not os.path.exists(main_directory):
        print(f"Error: The directory {main_directory} does not exist.")
        return
    
    # Walk through all files and folders in the directory
    for root, dirs, files in os.walk(main_directory, topdown=False):
        # Delete files first
        for file in files:
            file_path = os.path.join(root, file)
            
            # Skip deleting credentials.txt
            if file == "credentials.txt":
                print(f"Skipping {file_path} (credentials.txt)")
                continue  # Skip this file
            
            # Remove .zip files
            if file.endswith(".zip"):
                try_remove(file_path)
            
            # Remove .txt files (except credentials.txt)
            elif file.endswith(".txt"):
                try_remove(file_path)
            
            # Remove .csv files
            elif file.endswith(".csv"):
                try_remove(file_path)
        
        # Delete directories after files
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            try:
                # Ensure the directory is writable
                os.chmod(dir_path, 0o777)  # Make it writable
                shutil.rmtree(dir_path)  # Remove directory and its contents
                print(f"Removed directory: {dir_path}")
            except PermissionError as e:
                print(f"Permission error removing directory {dir_path}: {e}")
            except Exception as e:
                print(f"Error removing directory {dir_path}: {e}")
        
    # Clear selenium chromedriver cache
    clear_selenium_manager_cache()
    
    print("Clear cache complete.")
    
def uninstall(main_directory):
    """
    Deletes all folders, .zip files, .txt files (except credentials.txt and log.txt) in the given directory and clears selenium chromedriver cache before uninstalling.
        
    :param main_directory: Directory path where data should be cleared.
    """
    # Check if the given directory exists
    if not os.path.exists(main_directory):
        print(f"Error: The directory {main_directory} does not exist.")
        return
    
    # Walk through all files and folders in the directory
    for root, dirs, files in os.walk(main_directory, topdown=False):
        # Delete files first
        for file in files:
            file_path = os.path.join(root, file)
            
            # Skip deleting credentials.txt
            if file in ["credentials.txt", "log.txt"]:
                print(f"Skipping {file_path} (credentials.txt)")
                continue  # Skip this file
            
            # Remove .zip files
            if file.endswith(".zip"):
                try_remove(file_path)
            
            # Remove .txt files (except credentials.txt)
            elif file.endswith(".txt"):
                try_remove(file_path)
                
            # Remove .csv files
            elif file.endswith(".csv"):
                try_remove(file_path)
        
        # Delete directories after files
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            try:
                # Ensure the directory is writable
                os.chmod(dir_path, 0o777)  # Make it writable
                shutil.rmtree(dir_path)  # Remove directory and its contents
                print(f"Removed directory: {dir_path}")
            except PermissionError as e:
                print(f"Permission error removing directory {dir_path}: {e}")
            except Exception as e:
                print(f"Error removing directory {dir_path}: {e}")
    
    # Clear selenium chromedriver cache
    clear_selenium_manager_cache()
                
    # Uninstall the package
    print("Uninstalling the package...")
    subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "IMDBTraktSyncer"], check=True)

    print("Uninstall complete.")

def clean_uninstall(main_directory):
    """
    Deletes all folders, .zip files, .txt files in the given directory and clears selenium chromedriver cache before uninstalling.
        
    :param main_directory: Directory path where data should be cleared.
    """
    # Check if the given directory exists
    if not os.path.exists(main_directory):
        print(f"Error: The directory {main_directory} does not exist.")
        return
    
    # Walk through all files and folders in the directory
    for root, dirs, files in os.walk(main_directory, topdown=False):
        # Delete files first
        for file in files:
            file_path = os.path.join(root, file)
            
            # Remove .zip files
            if file.endswith(".zip"):
                try_remove(file_path)
            
            # Remove .txt files (except credentials.txt)
            elif file.endswith(".txt"):
                try_remove(file_path)
            
            # Remove .csv files
            elif file.endswith(".csv"):
                try_remove(file_path)
        
        # Delete directories after files
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            try:
                # Ensure the directory is writable
                os.chmod(dir_path, 0o777)  # Make it writable
                shutil.rmtree(dir_path)  # Remove directory and its contents
                print(f"Removed directory: {dir_path}")
            except PermissionError as e:
                print(f"Permission error removing directory {dir_path}: {e}")
            except Exception as e:
                print(f"Error removing directory {dir_path}: {e}")
    
    # Clear selenium chromedriver cache
    clear_selenium_manager_cache()
                
    # Uninstall the package
    print("Uninstalling the package...")
    subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "IMDBTraktSyncer"], check=True)

    print("Clean uninstall complete.")

def print_directory(main_directory):
    print(f"Install Directory: {main_directory}")