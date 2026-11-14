# IMDB-Trakt-Syncer
This Python script syncs user watchlist, ratings, reviews and watch history for Movies, TV Shows and Episodes both ways between [Trakt](https://trakt.tv/) and [IMDB](https://imdb.com/). Existing items will not be overwritten. Ratings, watchlist, comment/review & watch history sync are all optional. The user will be prompted to enter their settings and credentials on first run.

The script is compatible with operating systems that support Python (v3.6 or later) and Chromedriver (Windows, Linux and Mac). If you're interested in syncing ratings between Trakt, Plex, IMDB, and TMDB, I recommend the following projects: [PlexTraktSync](https://github.com/Taxel/PlexTraktSync), [IMDB-Trakt-Syncer](https://github.com/RileyXX/IMDB-Trakt-Syncer), and [TMDB-Trakt-Syncer](https://github.com/RileyXX/TMDB-Trakt-Syncer). See below for my other [recommended projects](https://github.com/RileyXX/IMDB-Trakt-Syncer?tab=readme-ov-file#other-recommended-projects).

## Installation Instructions
1. Install [Python](https://www.python.org/downloads/) (v3.6 or later). During Python installation, tick the box for adding Python to your PATH variable. _If Python is already installed, you can skip this step._
2. Install the script by executing `python -m pip install IMDBTraktSyncer` in command line.
3. Login to [Trakt](https://trakt.tv/oauth/applications) and create a new API application named `IMDBTraktSyncer`. Copy its client ID; this CLI uses Trakt's device authorization flow, which does not need a redirect URI for sign-in or a client secret.
4. Run the script by executing `IMDBTraktSyncer` in the command line.
5. Follow the prompts during the first run. Enter your Trakt `client ID` from step 3 and your IMDb or Amazon-linked `username` and `password`. The script generates a PKCE verifier for Trakt authorization and does not send the app's client secret. IMDb/Amazon credentials are saved as plain text in `credentials.txt` beside the package, so use a unique password.
6. Setup is complete. The script will continue running and syncing your ratings. You can monitor its progress in the command line. See below for [setting up automation](https://github.com/RileyXX/IMDB-Trakt-Syncer?tab=readme-ov-file#for-setting-up-automation-see-the-following-wiki-pages).

### Running from a cloned repository

From the repository root, create and activate a virtual environment, then install this checkout:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
IMDBTraktSyncer
```

On macOS or Linux, activate the environment with `source .venv/bin/activate` instead. On first run, follow the prompts to configure Trakt and IMDb; the script syncs only the categories you enable.

**Credential note:** Trakt tokens and IMDb/Amazon credentials are stored as plain text in `credentials.txt` beside the package. On macOS/Linux, the script restricts that file to the current user when it initializes the browser. This is not encryption; do not share the file or commit it to Git. On Windows, protect the installation folder with your account's filesystem permissions. Run the program as a regular user so Chrome's security sandbox remains enabled.

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
IMDBTraktSyncer --uninstall
```
_Clears cached browsers and drivers before uninstalling. Run in your operating system's native command line._
## Installing a Specific Version:
```
python -m pip install IMDBTraktSyncer==VERSION_NUMBER
```
_Replace `VERSION_NUMBER` with your [desired version](https://github.com/RileyXX/IMDB-Trakt-Syncer/releases) (e.g. 3.1.0) and run in your operating system's native command line._
## Performing a Clean Uninstall:
```
IMDBTraktSyncer --clean-uninstall
```
_Clears all cached data, inluding user credentials, cached browsers and drivers before uninstalling. Run in your operating system's native command line._
## Uninstall With Native Python Method:
```
python -m pip uninstall IMDBTraktSyncer
```
_Not recommended unless other uninstall methods failed. This method leaves behind any cached data such as user entered credentials, cached browsers, and drivers which can be deleted manually from your install directory. Run in your operating system's native command line._

# Commands for IMDBTraktSyncer

Below is a list of available commands for this package, along with a brief description of their functionality. You can copy and paste them directly into your terminal.

## Available Commands

| **Command**               | **Description**                                                                                       |
|---------------------------|-------------------------------------------------------------------------------------------------------|
| `--help`                  | List available commands                                                                               |
| `--clear-user-data`       | Clears user-entered credentials.                                                                      |
| `--clear-cache`           | Clears cached browsers, drivers, Trakt data, exports, and logs.                                       |
| `--uninstall`             | Clears cached browsers and drivers before uninstalling.                                               |
| `--clean-uninstall`       | Clears all cached data, including user credentials, cached browsers, and drivers before uninstalling. |
| `--directory`             | Prints the package install directory.                                                                 |
| `--show-browser`          | Runs Chrome visibly instead of headless.                                                              |
| `--update-trakt-cache`    | Fetches fresh Trakt data and updates the local cache before syncing.                                  |
| `--use-existing-imdb-exports` | Uses local IMDb export CSVs instead of opening IMDb's export pages.                              |

## Usage Example

Run the following commands as needed:

```bash
# List available commands
IMDBTraktSyncer --help

# To clear user data
IMDBTraktSyncer --clear-user-data

# To clear cache
IMDBTraktSyncer --clear-cache

# To uninstall
IMDBTraktSyncer --uninstall

# To perform a clean uninstall
IMDBTraktSyncer --clean-uninstall

# To get the installation directory
IMDBTraktSyncer --directory

# To run with a visible Chrome window
IMDBTraktSyncer --show-browser

# To refresh cached Trakt data before syncing
IMDBTraktSyncer --update-trakt-cache

# To sync from IMDb exports downloaded manually
IMDBTraktSyncer --use-existing-imdb-exports --show-browser

# Use multiple commands at once
IMDBTraktSyncer --clear-user-data --clear-cache
```

Trakt watchlist, ratings, comments, and history data are cached locally in `trakt_data_cache.json` beside the package credentials. The watchlist fetch reads all pages Trakt returns. Normal runs use cached data; add `--update-trakt-cache` to fetch fresh Trakt data. The cache is associated with the authenticated Trakt account and only contains datasets enabled for the current run. It may contain private activity, so keep it private and do not commit or share it. `--clear-cache` removes the Trakt cache along with browser and export caches, while preserving credentials. Trakt may still enforce account or API limits when adding items; pagination only retrieves items already available in the account's watchlist.

If IMDb blocks automated access to its export pages, download the required CSV exports manually from IMDb. Place them in the package directory printed when the program starts, using the exact names `watchlist.csv`, `ratings.csv`, and `checkins.csv`. Run `IMDBTraktSyncer --use-existing-imdb-exports --show-browser`; this validates the required files and headers and skips IMDb's export pages. As the sync successfully adds an item to IMDb, its row is added or updated in the matching local CSV, so the files stay current if the run is interrupted. Watchlist removals are not written to the CSV. Only files needed for the enabled sync options are required. Zero-byte files are treated as empty IMDb lists; nonempty files must include the expected headers.

## Alternative Manual Installation Method (without pip install)
1. Install [Python](https://www.python.org/downloads/) (v3.6 or later). During Python installation, tick the box for adding Python to your PATH variable.  _If Python is already installed, you can skip this step._
2. Download the latest `.zip` directly from GitHub [here](https://github.com/RileyXX/IMDB-Trakt-Syncer/archive/refs/heads/main.zip) and extract it to the desired directory.
3. Open your operating system's native command line interface, use it to navigate to the extracted folder and run `python -m pip install -r requirements.txt`.
4. Login to [Trakt](https://trakt.tv/oauth/applications) and create a new API application named `IMDBTraktSyncer`. Copy its client ID; this CLI uses Trakt's device authorization flow, which does not need a redirect URI for sign-in or a client secret.
5. Run `IMDBTraktSyncer.py` or open the terminal and navigate to the folder where `IMDBTraktSyncer.py` is located. Run `IMDBTraktSyncer.py` in the terminal.
6. Follow the prompts during the first run. Enter your Trakt `client ID` from step 4 and your IMDb or Amazon-linked `username` and `password`. The script generates a PKCE verifier for Trakt authorization and does not send the app's client secret. IMDb/Amazon credentials are saved as plain text in `credentials.txt` beside the package, so use a unique password.
7. Setup is complete. The script will continue running and syncing your ratings. You can monitor its progress in the command line. See below for [setting up automation](https://github.com/RileyXX/IMDB-Trakt-Syncer#for-setting-up-automation-see-the-following-wiki-pages).

## For Setting Up Automation See the Following Wiki Pages:
- Setup Automation for:
   - [Windows](https://github.com/RileyXX/IMDB-Trakt-Syncer/wiki/Setting-Up-Automation-on-Windows)
   - [Linux](https://github.com/RileyXX/IMDB-Trakt-Syncer/wiki/Setting-Up-Automation-on-Linux)
   - [macOS](https://github.com/RileyXX/IMDB-Trakt-Syncer/wiki/Setting-Up-Automation-on-macOS)
- Python Script to Update all Packages with Pip (Windows, Linux, Mac, ChromeOS, etc.) [Link #1](https://github.com/RileyXX/IMDB-Trakt-Syncer/wiki/Python-Script-to-Update-all-Packages-with-Pip-\(Windows,-Linux,-Mac,-ChromeOS,-etc\))

## Troubleshooting, Known Issues, Workarounds & Future Outlook
- If any of your details change (passwords, logins, API keys, etc.), simply run `IMDBTraktSyncer --clear-user-data` to reset your credentials. Alternatively, open `credentials.txt`, modify your details, save it and then run the script again. You can also simply delete `credentials.txt` to reset the script and it will prompt you to enter your new details on the next run.
- If IMDB requires a captcha on login, and you see "Not signed in" appear in the script, the captcha is likely the cause. To fix this, navigate to the IMDB website in your browser (preferably Chrome) from the same computer. If you're already logged in, log out and log back in. It may ask you to fill in a captcha. Complete the captcha and finish logging in. After successfully logging in on your browser, run the script again, and it should work. You may need to repeat this step several times if the issue persists. Adding a captcha solver to the script is being considered but not currently implemented. [Issue #2](https://github.com/RileyXX/IMDB-Trakt-Syncer/issues/2)
- If IMDb returns HTTP 405 during a sync, the script keeps the browser open and retries the blocked page every 60 seconds. Run with `--show-browser`, complete any CAPTCHA while the script waits, and the sync continues automatically when the retry succeeds. Press Ctrl+C to cancel; items already synced are checked again if you rerun.
- Amazon-linked IMDb accounts: the script first tries IMDb sign-in, then automatically retries through "Sign in with Amazon" using the same email and password. Run `IMDBTraktSyncer --show-browser` to complete an Amazon CAPTCHA or verification code interactively. An HTTP 405 while loading IMDb's homepage happens before sign-in, so changing the account provider will not resolve that particular error.
- If Chrome startup reports an SSL or proxy error while checking Google's Chrome-for-Testing metadata, verify your internet connection and `HTTPS_PROXY` settings. When a matching cached Chrome and ChromeDriver are available, the script can continue using them; otherwise, it needs network access to download them.
- Due to IMDB's lack of API and rating import ability, this script uses an unconventional method that mimics using a web browser to set ratings on IMDB. Therefore, there are many points of failure that could arise. The script will be updated as best as possible.

## Screenshot
![Demo](https://i.imgur.com/QXCtGrr.png)

## Sponsorships, Donations, and Custom Projects
If you find my scripts helpful, you can become a [sponsor](https://github.com/sponsors/RileyXX) and support my projects! If you need help with a project, open an issue, and I'll do my best to assist you. For other inquiries and custom projects, you can contact me on [Twitter](https://twitter.com/RileyxBell).

#### More Donation Options:
- Cashapp: [$rileyxx](https://cash.app/$rileyxx/)
- Venmo: [@rileyxx](https://account.venmo.com/u/rileyxx)
- Bitcoin: `bc1qrjevwqv49z8y77len3azqfghxrjmrjvhy5zqau`

## Also Posted On
- [PyPi](https://pypi.org/project/IMDBTraktSyncer/)
- [Reddit](https://www.reddit.com/r/trakt/comments/17xd8ic/imdb_trakt_watchlistrating_syncer_tool_sync_both/)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Other Recommended Projects:

| Project Name | Description |
|--------------|-------------|
| [PlexTraktSync](https://github.com/Taxel/PlexTraktSync) | A script that syncs user watch history and ratings between Trakt and Plex (without needing a PlexPass or Trakt VIP subscription). |
| [IMDB-Trakt-Syncer](https://github.com/RileyXX/IMDB-Trakt-Syncer) | A script that syncs user watchlist, ratings, reviews and watch history both ways between Trakt and IMDB. |
| [TMDB-Trakt-Syncer](https://github.com/RileyXX/TMDB-Trakt-Syncer) | A script that syncs user watchlist and ratings both ways between Trakt and TMDB. |
| [PlexPreferNonForcedSubs](https://github.com/RileyXX/PlexPreferNonForcedSubs) | A script that sets all movies and shows in your local Plex library to English non-forced subtitles by default. |
| [Casvt / AudioSubChanger](https://github.com/Casvt/Plex-scripts/blob/main/media_management/audio_sub_changer.py) | A script with advanced options for changing audio & subtitle tracks in Plex. |
| [Casvt / PlexAutoDelete](https://github.com/Casvt/Plex-scripts/blob/main/media_management/plex_auto_delete.py) | A script for automatically deleting watched content from Plex. |
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
| [th-ch/youtube-music](https://github.com/th-ch/youtube-music) | A lightweight and feature-rich desktop client for YouTube Music, offering additional features like ad-blocking, sponsorblock and customizable themes. |
| [ReVanced](https://github.com/revanced) | A community-driven project to modify and enhance YouTube and other apps on Android, offering features such as ad-blocking, background playback, and other advanced customization options. |
| uBlock Origin [Chrome](https://chromewebstore.google.com/detail/ublock-origin-lite/ddkjiahejlhfcafbddmgiahcphecmpfh) / [Firefox](https://addons.mozilla.org/en-US/firefox/addon/ublock-origin/) | A powerful, open-source browser extension for blocking ads, trackers, and other unwanted content. |
| SponsorBlock [Chrome](https://chromewebstore.google.com/detail/sponsorblock-for-youtube/mnjggcdmjocbbbhaepdhchncahnbgone) / [Firefox](https://addons.mozilla.org/en-US/firefox/addon/sponsorblock/) | A browser extension that automatically skips sponsored segments in YouTube videos. |
| Enhancer for YouTube [Chrome](https://chromewebstore.google.com/detail/enhancer-for-youtube/ponfpcnoihfmfllpaingbgckeeldkhle) / [Firefox](https://addons.mozilla.org/en-US/firefox/addon/enhancer-for-youtube/) | A browser extension that adds a wide range of customization options and playback enhancements for YouTube, including the ability to force playback resolution. |
| Return YouTube Dislike [Chrome](https://chromewebstore.google.com/detail/return-youtube-dislike/gebbhagfogifgggkldgodflihgfeippi) / [Firefox](https://addons.mozilla.org/en-US/firefox/addon/return-youtube-dislikes/) | A browser extension that restores the dislike count on YouTube videos. |
