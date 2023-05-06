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

def getImdbRatings(imdb_username, imdb_password, driver, directory, wait):
    #Get IMDb Ratings
    print('Getting IMDB Ratings')

    driver.get('https://www.imdb.com/list/ratings')

    dropdown = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".circle")))
    dropdown.click()

    csv_link = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".pop-up-menu-list-items a.pop-up-menu-list-item-link")))
    csv_link.click()

    #Wait for csv download to complete
    time.sleep(10)

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
    
    return imdb_ratings


