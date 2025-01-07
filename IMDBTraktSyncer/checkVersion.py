import xml.etree.ElementTree as ET
import urllib.request
import subprocess
import sys

def get_installed_version():
    """
    Retrieve the installed version of the 'imdbtraktsyncer' package.
    First, attempts to use 'pip' directly.
    If that fails, it falls back to calling 'sys.executable -m pip'.
    """
    # Try calling 'pip' directly
    try:
        result = subprocess.run(
            ['pip', 'show', 'IMDBTraktSyncer'],
            capture_output=True,
            text=True,
            check=True
        )
        for line in result.stdout.splitlines():
            if line.startswith("Version:"):
                return line.split()[1]
    except subprocess.CalledProcessError as e:
        print(f"Error: Could not retrieve version using 'pip' command directly: {e}")
    except FileNotFoundError:
        print("Error: 'pip' is not installed or not in PATH.")
    except Exception as e:
        print(f"Unexpected error during fallback to 'pip': {e}")
    
    print("Fallback: Try using 'sys.executable -m pip'")
    
    # Fallback: Attempt using 'sys.executable -m pip'
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'show', 'IMDBTraktSyncer'],
            capture_output=True,
            text=True,
            check=True
        )
        for line in result.stdout.splitlines():
            if line.startswith("Version:"):
                print(line.split()[1])
                return line.split()[1]
    except subprocess.CalledProcessError as e:
        print(f"Error: Could not retrieve python version using '{sys.executable} -m pip': {e}")
    except FileNotFoundError:
        print(f"Error: Python executable '{sys.executable}' does not have pip installed.")

    # If all attempts fail
    return None

def get_latest_version():
    try:
        with urllib.request.urlopen("https://pypi.org/rss/project/imdbtraktsyncer/releases.xml") as response:
            xml_data = response.read()
        root = ET.fromstring(xml_data)
        for item in root.findall('./channel/item'):
            title = item.find('title').text
            if title:
                return title
    except Exception as e:
        print(f"Error retrieving latest version: {e}")
        return None

def compare_versions(installed, latest):
    def parse_version(v):
        return tuple(map(int, v.split('.')))
    
    return parse_version(installed) < parse_version(latest)

def checkVersion():
    installed_version = get_installed_version()
    if not installed_version:
        print("IMDBTraktSyncer is not installed.")
        return

    latest_version = get_latest_version()
    if not latest_version:
        print("Could not retrieve the latest version.")
        return

    if compare_versions(installed_version, latest_version):
        print(f"A new version of IMDBTraktSyncer is available: {latest_version} (installed: {installed_version}).")
        print("To update use: python -m pip install IMDBTraktSyncer --upgrade")
        print("Documentation: https://github.com/RileyXX/IMDB-Trakt-Syncer/releases")
    # else:
        # print(f"IMDBTraktSyncer is up to date (installed: {installed_version})")