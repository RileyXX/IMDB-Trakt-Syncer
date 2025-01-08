import time
import sys
import shutil
import subprocess
import os
import platform

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
            # Check if the path is a directory
            if os.path.isdir(file_path):
                # Ensure the directory and its contents are writable
                for root, dirs, files in os.walk(file_path, topdown=False):
                    for name in files:
                        file = os.path.join(root, name)
                        os.chmod(file, 0o777)  # Make file writable
                        os.remove(file)
                    for name in dirs:
                        folder = os.path.join(root, name)
                        os.chmod(folder, 0o777)  # Make folder writable
                        os.rmdir(folder)
                os.chmod(file_path, 0o777)  # Make the top-level folder writable
                os.rmdir(file_path)  # Finally, remove the directory
            else:
                # It's a file, ensure it's writable and remove it
                os.chmod(file_path, 0o777)  # Make it writable
                os.remove(file_path)
            print(f"Successfully removed: {file_path}")
            return True
        except PermissionError:
            print(f"Permission error for {file_path}, retrying...")
        except Exception as e:
            print(f"Error removing {file_path}: {e}")
        
        time.sleep(delay)
    return False

def delete_chromedriver_cache():
    # Clear selenium chromedriver cache
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
                    file_path = os.path.join(root, name)
                    if not try_remove(file_path):
                        print(f"Failed to remove file: {file_path}")
                for name in dirs:
                    dir_path = os.path.join(root, name)
                    if not try_remove(dir_path):
                        print(f"Failed to remove directory: {dir_path}")
            print(f"Selenium Chromedriver cache cleared at: {chromedriver_cache}")
        else:
            print(f"The path {chromedriver_cache} does not exist.")

    except Exception as e:
        print(f"An error occurred: {e}")

def clear_user_data(main_directory):
    """
    Deletes the credentials.txt file in the given directory.
    
    :param main_directory: Directory path where credentials.txt should be deleted.
    """
    credentials_path = os.path.join(main_directory, "credentials.txt")
    
    # Check if the credentials.txt file exists
    if not os.path.exists(credentials_path):
        print(f"Error: {credentials_path} does not exist.")
        return
    
    try:
        # Remove the credentials.txt file
        os.remove(credentials_path)
        print(f"Removed {credentials_path}")
    except PermissionError as e:
        print(f"Permission error removing {credentials_path}: {e}")
    except Exception as e:
        print(f"Error removing {credentials_path}: {e}")
    
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
    delete_chromedriver_cache()
    
    print("Clear cache complete.")
    
def uninstall(main_directory):
    """
    Deletes all folders, .zip files, .txt files (except credentials.txt) in the given directory and clears selenium chromedriver cache before uninstalling.
        
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
    delete_chromedriver_cache()
                
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
    delete_chromedriver_cache()
                
    # Uninstall the package
    print("Uninstalling the package...")
    subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "IMDBTraktSyncer"], check=True)

    print("Clean uninstall complete.")

def print_directory(main_directory):
    print(f"Install Directory: {main_directory}")