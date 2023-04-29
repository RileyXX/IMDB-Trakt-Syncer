import feedparser
import subprocess
import pkg_resources

# Check if chromedriver-py is already installed
try:
    pkg_resources.get_distribution('chromedriver-py')
#    print("chromedriver-py is already installed. Skipping installation.")
except pkg_resources.DistributionNotFound:
    # Make a request to the RSS feed
    feed = feedparser.parse('https://pypi.org/rss/project/chromedriver-py/releases.xml')

    # Get the second latest release version
    version = feed.entries[1].title.split()[-1]

    # Install the chromedriver-py package using pip
    subprocess.run(['pip', 'install', f'chromedriver-py=={version}'])
