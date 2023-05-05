import os
import time
import csv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from chromedriver_py import binary_path
try:
    from IMDbTraktSyncer import verifyCredentials
except:
    import verifyCredentials

#Get IMDb Ratings
print('Getting IMDB Ratings')

imdb_username = verifyCredentials.imdb_username
imdb_password = verifyCredentials.imdb_password

directory = os.path.dirname(os.path.realpath(__file__))

#Start web driver
options = Options()
options.add_argument("--headless=new")
options.add_argument('--disable-notifications')
options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3')
options.add_experimental_option("prefs", {"download.default_directory": directory, "download.directory_upgrade": True, "download.prompt_for_download": False})


service = Service(executable_path=binary_path)
driver = webdriver.Chrome(service=service, options=options)

wait = WebDriverWait(driver, 10)

driver.get('https://www.imdb.com/registration/signin')

sign_in_link = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.auth-provider-text')))
if sign_in_link.text == 'Sign in with IMDb':
    sign_in_link.click()

email_input = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "input[type='email']")))[0]
password_input = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "input[type='password']")))[0]

email_input.send_keys(imdb_username)
password_input.send_keys(imdb_password)

submit_button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='submit']")))
submit_button.click()
time.sleep(3)

driver.get('https://www.imdb.com/list/ratings')

# Check if signed in
element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".nav__userMenu.navbar__user")))
if "Sign In" in element.text:
    print("Not signed in")
else:
    print("Signed in")
    

dropdown = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".circle")))
dropdown.click()

csv_link = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".pop-up-menu-list-items a.pop-up-menu-list-item-link")))
csv_link.click()

#Wait for csv download to complete and close web driver
time.sleep(10)
driver.quit()
service.stop()

imdb_ratings = []

# Read the ratings from the CSV file
here = os.path.abspath(os.path.dirname(__file__))
ratings_path = os.path.join(here, 'ratings.csv')
try:
    with open(ratings_path, 'r') as file:
        reader = csv.reader(file)
        header = next(reader)  # skip the header row
        for row in reader:
            title = row[3]
            year = row[8]
            rating = row[1]
            imdb_id = row[0]
            if "tv" in row[5]:
                type = "show"
            else:
                type = "movie"
            imdb_ratings.append({'Title': title, 'Year': year, 'Rating': rating, 'ID': imdb_id, 'Type': type})
except FileNotFoundError:
    print('Ratings file not found')
    
# Delete csv files
for file in os.listdir(directory):
    if file.endswith('.csv'):
        os.remove(os.path.join(directory, file))

print('Getting IMDB Ratings Complete')


