# IMDB-Trakt-Syncer
This Python script syncs user watchlist, ratings and comments for Movies, TV Shows and Episodes both ways between [Trakt](https://trakt.tv/) and [IMDB](https://imdb.com/). Existing items will not be overwritten. Ratings, watchlist and comment/review sync are all optional. The user will be prompted to enter their settings and credentials on first run.

The script is compatible with operating systems that support Python (v3.6 or later) and Chromedriver (Windows, Linux and Mac). If you're interested in syncing ratings between Trakt, Plex, IMDB, and TMDB, I recommend the following projects: [PlexTraktSync](https://github.com/Taxel/PlexTraktSync), [IMDB-Trakt-Syncer](https://github.com/RileyXX/IMDB-Trakt-Syncer), and [TMDB-Trakt-Syncer](https://github.com/RileyXX/TMDB-Trakt-Syncer). See below for my other [recommended projects](https://github.com/RileyXX/IMDB-Trakt-Syncer#other-recommended-projects).

## Installation Instructions
1. Install [Python](https://www.python.org/downloads/) (v3.6 or later) and [Google Chrome](https://www.google.com/chrome/). _If these are already installed, you can skip this step. Please note this script does not affect Chrome in anyway, it is simply required in order for chromedriver to work._
2. Install the script by executing `python -m pip install IMDBTraktSyncer` in command line.
3. Login to [Trakt](https://trakt.tv/oauth/applications) and create a new API application named `IMDBTraktSyncer`. In the "Redirect uri" field, enter `urn:ietf:wg:oauth:2.0:oob`, then save the application.
4. Run the script by executing `IMDBTraktSyncer` in the command line.
5. Follow the prompts during the first run. You will need to enter your Trakt `client ID` and `client secret` from step 3, as well as your IMDB `username` and `password`. Please note that these details are saved insecurely as `credentials.txt` in the same folder as the script. It is recommended to change your IMDB password to something unique beforehand.
6. Setup is complete. The script will continue running and syncing your ratings. You can monitor its progress in the command line. See below for [setting up automation](https://github.com/RileyXX/IMDB-Trakt-Syncer#for-setting-up-automation-see-the-following-wiki-pages).

## Installing the Script:
```
python -m pip install IMDBTraktSyncer
```
_Run in your operating system's native command line._
## Running the Script:
```
IMDBTraktSyncer
```
_Run in your operating system's native command line._
## Updating the Script:
```
python -m pip install IMDBTraktSyncer --upgrade
```
_Run in your operating system's native command line._
## Uninstalling the Script:
```
python -m pip uninstall IMDBTraktSyncer
```
_Run in your operating system's native command line._

## Installing a Specific Version:
```
python -m pip install IMDBTraktSyncer==VERSION_NUMBER
```
_Replace `VERSION_NUMBER` with your [desired version](https://github.com/RileyXX/IMDB-Trakt-Syncer/releases) (e.g. 1.1.6) and run in your operating system's native command line._

## Alternative Manual Installation Method (without pip install)
1. Install [Python](https://www.python.org/downloads/) (v3.6 or later) and [Google Chrome](https://www.google.com/chrome/).  _If these are already installed, you can skip this step. Please note this script does not affect Chrome in anyway, it is simply required in order for chromedriver to work._
2. Download the latest .zip from the [releases page](https://github.com/RileyXX/IMDB-Trakt-Syncer/releases) and extract it to the desired directory.
3. Login to [Trakt](https://trakt.tv/oauth/applications) and create a new API application named `IMDBTraktSyncer`. In the "Redirect uri" field, enter `urn:ietf:wg:oauth:2.0:oob`, then save the application.
4. Run `IMDBTraktSyncer.py` or open the terminal and navigate to the folder where `IMDBTraktSyncer.py` is located. Run `IMDBTraktSyncer.py` in the terminal.
5. Follow the prompts during the first run. You will need to enter your Trakt `client ID` and `client secret` from step 3, as well as your IMDB `username` and `password`. Please note that these details are saved insecurely as `credentials.txt` in the same folder as the script. It is recommended to change your IMDB password to something unique beforehand.
6. Setup is complete. The script will continue running and syncing your ratings. You can monitor its progress in the command line. See below for [setting up automation](https://github.com/RileyXX/IMDB-Trakt-Syncer#for-setting-up-automation-see-the-following-wiki-pages).

## For Setting Up Automation See the Following Wiki Pages:
- Setup Automation for:
   - [Windows](https://github.com/RileyXX/IMDB-Trakt-Syncer/wiki/Setting-Up-Automation-on-Windows)
   - [Linux](https://github.com/RileyXX/IMDB-Trakt-Syncer/wiki/Setting-Up-Automation-on-Linux)
   - [macOS](https://github.com/RileyXX/IMDB-Trakt-Syncer/wiki/Setting-Up-Automation-on-macOS)
- Python Script to Update all Packages with Pip (Windows, Linux, Mac, ChromeOS, etc.) [Link #1](https://github.com/RileyXX/IMDB-Trakt-Syncer/wiki/Python-Script-to-Update-all-Packages-with-Pip-\(Windows,-Linux,-Mac,-ChromeOS,-etc\))

## Troubleshooting, Known Issues, Workarounds & Future Outlook
- If IMDB requires a captcha on login, and you see "Not signed in" appear in the script, the captcha is likely the cause. To fix this, navigate to the IMDB website in your browser (preferably Chrome) from the same computer. If you're already logged in, log out and log back in. It may ask you to fill in a captcha. Complete the captcha and finish logging in. After successfully logging in on your browser, run the script again, and it should work. You may need to repeat this step once or twice if the issue persists. Adding a captcha solver to the script is being considered but not currently implemented. [Issue #2](https://github.com/RileyXX/IMDB-Trakt-Syncer/issues/2)
- If you see an error about having the incorrect version of Chromedriver, uninstall it by running the following command in the command line: `python -m pip uninstall chromedriver-py`. In your Chrome browser, go to Settings > About Chrome and check the prefix for your version (e.g., 112... or 111). If the prefix matches your Chrome version, navigate to the [chromedriver-py releases page](https://pypi.org/project/chromedriver-py/#history) and find the latest version that matches the prefix for your Chrome version. Copy the version number you need (e.g 113.0.5672.63), then run the following command in the command line: `python -m pip install chromedriver-py==VERSION_NUMBER`. Replace `VERSION_NUMBER` with the version you copied and press enter. This will install the correct version of Chromedriver. Run the script again, and it should work. [Issue #16](https://github.com/RileyXX/IMDB-Trakt-Syncer/issues/16)
- If any of your details change (passwords, logins, API keys, etc.), simply open `credentials.txt`, modify your details, save it and then run the script again. Alternatively, delete `credentials.txt` to reset the script and it will prompt you to enter your new details on the next run.
- Due to IMDB's lack of API and rating import ability, this script uses an unconventional method that mimics using a web browser to set ratings on IMDB. Therefore, there are many points of failure that could arise. The script will be updated as best as possible.

## Screenshot
![Demo](https://i.imgur.com/QXCtGrr.png)

## Sponsorships, Donations, and Custom Projects
If you find my scripts helpful, you can become a [sponsor](https://github.com/sponsors/RileyXX) and support my projects! If you need help with a project, open an issue, and I'll do my best to assist you. For other inquiries and custom projects, you can contact me on [Twitter](https://twitter.com/RileyxBell).

#### More Donation Options:
- Cashapp: `$rileyxx`
- Venmo: `@rileyxx`
- Bitcoin: `bc1qrjevwqv49z8y77len3azqfghxrjmrjvhy5zqau`
- Amazon Wishlist: [Link ↗](https://www.amazon.com/hz/wishlist/ls/WURF5NWZ843U)

## Also Posted On
- [PyPi](https://pypi.org/project/IMDBTraktSyncer/)
- [Reddit](https://www.reddit.com/r/trakt/comments/132heo0/IMDB_trakt_rating_syncer_tool_sync_both_ways/)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Other Recommended Projects:

| Project Name | Description |
|--------------|-------------|
| [PlexTraktSync](https://github.com/Taxel/PlexTraktSync) | A script that syncs user watch history and ratings between Trakt and Plex (without needing a PlexPass or Trakt VIP subscription). |
| [IMDB-Trakt-Syncer](https://github.com/RileyXX/IMDB-Trakt-Syncer) | A script that syncs user watchlist, ratings, and comments both ways between Trakt and IMDB. |
| [TMDB-Trakt-Syncer](https://github.com/RileyXX/TMDB-Trakt-Syncer) | A script that syncs user watchlist and ratings both ways between Trakt and TMDB. |
| [PlexPreferNonForcedSubs](https://github.com/RileyXX/PlexPreferNonForcedSubs) | A script that sets all movies and shows in your local Plex library to English non-forced subtitles by default. |
| [Casvt / AudioSubChanger](https://github.com/Casvt/Plex-scripts/blob/main/changing_settings/audio_sub_changer.py) | A script with advanced options for changing audio & subtitle tracks in Plex. |
| [Casvt / PlexAutoDelete](https://github.com/Casvt/Plex-scripts/blob/main/changing_settings/plex_auto_delete.py) | A script for automatically deleting watched content from Plex. |
| [universal-trakt-scrobbler](https://github.com/trakt-tools/universal-trakt-scrobbler) | An extension that automatically scrobbles TV shows and Movies from several streaming services to Trakt. |
| [Netflix-to-Trakt-Import](https://github.com/jensb89/Netflix-to-Trakt-Import) | A tool to import your Netflix viewing history into Trakt. |
| [trakt-tv-backup](https://darekkay.com/blog/trakt-tv-backup/) | A command-line tool for backing up your Trakt.tv data. |
| [blacktwin / JBOPS](https://github.com/blacktwin/JBOPS) | A collection of scripts and tools for enhancing and automating tasks in Plex. |
| [Casvt / Plex-scripts](https://github.com/Casvt/Plex-scripts) | A collection of useful scripts for Plex automation and management. |
| [trakt---letterboxd-import](https://github.com/jensb89/trakt---letterboxd-import) | A tool to import your Letterboxd ratings and watchlist into Trakt. |
| [TraktRater](https://github.com/damienhaynes/TraktRater/) | A tool to help users transfer user episode, show, and movie user ratings and watchlists from multiple media database sites around the web. |
| [TvTimeToTrakt](https://github.com/lukearran/TvTimeToTrakt) | A tool to sync your TV Time watch history with Trakt.tv. |
| [Plex Media Server](https://www.plex.tv/media-server-downloads/#plex-app) | A media server software to organize and stream your personal media collection. |
| [Radarr](https://github.com/Radarr/Radarr) | A movie collection manager and downloader for various platforms. |
| [Sonarr](https://github.com/Sonarr/Sonarr) | A TV show collection manager and downloader for various platforms. |
| [Jackett](https://github.com/Jackett/Jackett) | A proxy server that provides API support for various torrent trackers commonly used with Radarr and Sonarr. |
| [qBittorrent](https://github.com/qbittorrent/qBittorrent) | A free and open-source BitTorrent client. |
| [AirVPN](https://airvpn.org/) | A VPN client with port forwarding support. Great VPN for torrents. |
| [Overseerr](https://github.com/sct/overseerr) | A request management and media discovery tool for your home media server. |
| [FlareSolverr](https://github.com/FlareSolverr/FlareSolverr) | A reverse proxy solution to bypass Cloudflare protection and access websites commonly used with Jackett. |
| [youtube-dl](https://github.com/ytdl-org/youtube-dl) | A command-line program to download videos from YouTube and other sites. |

