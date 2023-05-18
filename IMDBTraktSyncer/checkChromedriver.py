import feedparser
import subprocess
import pkg_resources
import platform

def get_chrome_version():
    system = platform.system()
    if system == 'Windows':
        from winreg import ConnectRegistry, HKEY_CURRENT_USER, OpenKey, QueryValueEx

        try:
            registry = ConnectRegistry(None, HKEY_CURRENT_USER)
            key = OpenKey(registry, r'Software\Google\Chrome\BLBeacon')
            version, _ = QueryValueEx(key, 'version')
            return version.split('.')[0]
        except:
            return None

    elif system == 'Darwin':
        try:
            plist_path = '/Applications/Google Chrome.app/Contents/Info.plist'
            with open(plist_path, 'rb') as plist_file:
                plist_content = plist_file.read().decode('utf-8')
            version_start = plist_content.index('<key>CFBundleShortVersionString</key>') + 38
            version_end = plist_content.index('</string>', version_start)
            return plist_content[version_start:version_end].split('.')[0]
        except:
            return None

    elif system == 'Linux':
        try:
            process = subprocess.run(['google-chrome', '--version'], capture_output=True, text=True)
            version = process.stdout.strip().split(' ')[2].split('.')[0]
            return version
        except:
            return None

    return None

def install_chromedriver(version):
    # Install the chromedriver-py package using pip
    subprocess.run(['pip', 'install', f'chromedriver-py=={version}'])

def install_chromedriver_fallback_method():
    print("Using install chromedriver-py fallback method")
    # Install the chromedriver-py package using pip
    feed = feedparser.parse('https://pypi.org/rss/project/chromedriver-py/releases.xml')
    # Get the second latest release version
    version = feed.entries[1].title.split()[-1]
    # Install the chromedriver-py package using pip
    subprocess.run(['pip', 'install', f'chromedriver-py=={version}'])

# Check if chromedriver-py is already installed
try:
    dist = pkg_resources.get_distribution('chromedriver-py')
    installed_version = dist.version.split('.')[0]  # Retrieve only the prefix
    chrome_version = get_chrome_version()

    if chrome_version and installed_version != chrome_version:
        # Make a request to the RSS feed
        feed = feedparser.parse('https://pypi.org/rss/project/chromedriver-py/releases.xml')

        # Find the corresponding chromedriver-py version
        matching_version = None
        for entry in feed.entries:
            title = entry.title
            if title.startswith(chrome_version):
                matching_version = title.split()[-1]
                break

        if matching_version:
            # Install the corresponding chromedriver-py version
            install_chromedriver(matching_version)
        else:
            print(f"No matching chromedriver-py version found for Chrome {chrome_version}")
    else:
        # print("chromedriver-py is already installed with the correct version.")
        pass
except pkg_resources.DistributionNotFound:
    chrome_version = get_chrome_version()

    if chrome_version:
        # Make a request to the RSS feed
        feed = feedparser.parse('https://pypi.org/rss/project/chromedriver-py/releases.xml')

        # Find the corresponding chromedriver-py version
        matching_version = None
        for entry in feed.entries:
            title = entry.title
            if title.startswith(chrome_version):
                matching_version = title.split()[-1]
                break

        if matching_version:
            # Install the corresponding chromedriver-py version
            install_chromedriver(matching_version)
        else:
            print(f"No matching chromedriver-py version found for Chrome {chrome_version}")
            install_chromedriver_fallback_method()
    else:
        print("Failed to retrieve Chrome version.")
        install_chromedriver_fallback_method()
