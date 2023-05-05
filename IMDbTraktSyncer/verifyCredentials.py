import os
try:
    from IMDbTraktSyncer import authTrakt
except:
    import authTrakt

# Define the file path
here = os.path.abspath(os.path.dirname(__file__))
file_path = os.path.join(here, 'credentials.txt')

# Check if the file exists
if not os.path.isfile(file_path):
    # If the file does not exist, create it with default values
    with open(file_path, "w") as f:
        f.write("trakt_client_id=empty\n")
        f.write("trakt_client_secret=empty\n")
        f.write("trakt_access_token=empty\n")
        f.write("imdb_username=empty\n")
        f.write("imdb_password=empty\n")

# Load the values from the file
with open(file_path, "r") as f:
    lines = f.readlines()

# Create a dictionary of the values
values = {}
for line in lines:
    key, value = line.strip().split("=")
    values[key] = value

# Check if any of the values are "empty" and prompt the user to enter them
for key in values.keys():
    if values[key] == "empty" and key != "trakt_access_token":
        values[key] = input(f"Please enter a value for {key}: ")
        with open(file_path, "w") as f:
            for key, value in values.items():
                f.write(f"{key}={value}\n")

# Get the trakt_access_token value if it exists, or run the authTrakt.py function to get it
trakt_access_token = None
if "trakt_access_token" in values and values["trakt_access_token"] != "empty":
    trakt_access_token = values["trakt_access_token"]
else:
    client_id = values["trakt_client_id"]
    client_secret = values["trakt_client_secret"]
    trakt_access_token = authTrakt.authenticate(client_id, client_secret)
    values["trakt_access_token"] = trakt_access_token
    with open(file_path, "w") as f:
        for key, value in values.items():
            f.write(f"{key}={value}\n")

# Save the credential values as variables
trakt_client_id = values["trakt_client_id"]
trakt_client_secret = values["trakt_client_secret"]
trakt_access_token = values["trakt_access_token"]
imdb_username = values["imdb_username"]
imdb_password = values["imdb_password"]