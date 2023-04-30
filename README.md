# IMDb-Trakt-Syncer
This script will sync user ratings for Movies and TV Shows both ways between Trakt and IMDb. Currently season and episode ratings are not supported. Ratings already set will not be overwritten. This script should work on an OS where python and chromedriver are supported (Windows, Linux, Mac, and ChromeOS).
## Install Instructions:
1. Install [Python](https://www.python.org/downloads/) and [Google Chrome](https://www.google.com/chrome/). _If these are already installed on your machine you can ignore this step. Please note this script does not effect Chrome in anyway it is simply required in order for chromedriver to work._
2. Run `python -m pip install IMDbTraktSyncer` in command line.
3. Login to [Trakt](https://trakt.tv/oauth/applications) and create a new API application. We will name it `IMDbTraktSyncer`. In the Redirect uri field enter `urn:ietf:wg:oauth:2.0:oob` then Save. 
4. Run the script by calling `IMDbTraktSyncer` in command line. 
5. Follow the prompts on first run. It will ask you to fill in your Trakt client id and client secret from step 3. It will also ask you to enter your IMDb username and password. Please note that these details are saved insecurely as credentials.txt in the same folder as the script. Recommended to change your password to something unique beforehand.
6. Done, setup complete. The script will continue to run and sync your ratings. This may take some time, you can follow its progress in the command line.

## Run:
`IMDbTraktSyncer` in command line.

## Update:
`python -m pip install IMDbTraktSyncer --upgrade` in command line.

## Uninstall:
`python -m pip uninstall IMDbTraktSyncer` in command line.

## Alternative manual no install method:
1. Download the latest .zip from the [releases page](https://github.com/RileyXX/IMDb-Trakt-Syncer/releases) and move it to the file directory of your choice.
2. Run `IMDbTraktSyncer.py` OR open terminal and navigate to folder where `IMDbTraktSyncer.py` is located. Run `IMDbTraktSyncer.py` in terminal. 
3. Follow the prompts on first run. It will ask you to fill in your Trakt client id and client secret from step 3. It will also ask you to enter your IMDb username and password. Please note that these details are saved insecurely as credentials.txt in the same folder as the script. Recommended to change your password to something unique beforehand.
4. Done. The script will continue to run and sync your ratings. This may take some time, you can follow its progress in the command line.

## Troubleshooting, known issues, workarounds & future outlook:
* IMDb may require a captcha on login. If you see "Not signed in" appear in the script then the script will fail and the captcha is likely to be the cause. To fix this, navigate to IMDb website in your browser, preferably Chrome and from the same computer. If logged in, logout, and log back in. It may ask you to fill in a captch, complete it and finish logging in. After logging in succesfully on your browser run the script again and it should work. You may need to repeat this step once or twice if it still gives you issues. I'm looking into adding a captcha solver into the script to solve this problem, but it is currently not implemented. 
* If you see an error about having the incorrect version of Chrome driver. Uninstall it by running `python -m pip uninstall chromedriver-py` in command line. In your Chrome browser navigate to Settings > About Chrome and check your version (112... or 111 etc). This would indicate you are on Chrome version 112. Navigate to [chromedriver-py releases page](https://pypi.org/project/chromedriver-py/#history) and find the latest version that is the same Chrome version (112) already on your machine. Copy the version number you need. Then in command line run `python -m pip install chromedriver-py==VERSION_NUMBER`. Replace `VERSION_NUMBER` with the version you copied and press enter. This will install the correct chromedriver version. Run the script again and it should work.
* Due to IMDb's lack of API and lack of rating import ability, this script uses a rather unconventional method that mimics using a web browser to set ratings on IMDB. So there are many points of failure that could arise. I will try my best to keep the script updated as best possible.
* If any of your details change, passwords, logins, api keys etc, just delete credentials.txt and that will reset the script. It will prompt you to enter your new details on next run.

## Screenshot:
![Demo](https://i.imgur.com/uydTDcg.png)


## Sponsorships, Donations and Custom Projects:
Like my scripts? Become a [sponsor](https://github.com/sponsors/RileyXX) and support my projects! See below for other donation options. Need help with a project? Open an issue and I will try my best to help! For other inquiries and custom projects contact me on [Twitter](https://twitter.com/RileyxBell).

#### More donation options:
- Cashapp: `$rileyxx`
- Venmo: `@rileyxx`
- Bitcoin: `bc1qrjevwqv49z8y77len3azqfghxrjmrjvhy5zqau`
- Amazon Wishlist: [Link ↗](https://www.amazon.com/hz/wishlist/ls/WURF5NWZ843U)

## Also posted on:
* [Reddit](https://www.reddit.com/r/trakt/comments/132heo0/imdb_trakt_rating_syncer_tool_sync_both_ways/)

<br>

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
