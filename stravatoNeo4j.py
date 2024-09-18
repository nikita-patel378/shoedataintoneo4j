import requests
import json
import time
import configparser
import pandas as pd
from neo4j import GraphDatabase
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Function to convert hours to interval string
def hours_to_interval(hours_float):
    whole_hours = int(hours_float)
    fraction_hour = hours_float - whole_hours
    minutes = int(fraction_hour * 60)
    interval_string = f"{whole_hours} hours {minutes} minutes"
    return interval_string


# Neo4j connection setup
driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))


# Function to check if an activity exists in Neo4j
def activity_exists(tx, activity_id):
    query = """
    MATCH (a:Activity {activityid: $activity_id})
    RETURN a
    """
    result = tx.run(query, activity_id=activity_id)
    return result.single() is not None  # Returns True if the activity exists, False otherwise


# Function to create activity in Neo4j
def create_activity(tx, activity_id, shoe_id, activity_type, distance, elapsed_time, date):
    # Create Activity node, Shoe node, and set the relationships
    query = """
    MERGE (a:Activity {activityid: $activity_id})
    SET a.type = $activity_type, a.distance = $distance, a.time = $elapsed_time, a.date = $date

    MERGE (s:Shoe {shoeid: $shoe_id})

    MERGE (a)-[:USES]->(s)

    // Default to Laika for all activities with dog
    MERGE (d:Dog {name: 'Laika', type: 'My Dog'})
    MERGE (a)-[:COMPLETED_WITH]->(d)
    """
    tx.run(query, activity_id=activity_id, shoe_id=shoe_id, activity_type=activity_type,
           distance=distance, elapsed_time=elapsed_time, date=date)


# Function to insert activities into Neo4j
def insert_activities(df):
    with driver.session() as session:
        for index, row in df.iterrows():
            # Check if the activity already exists
            if session.execute_read(activity_exists, row['id']):
                logging.info(f"Activity with ID {row['id']} already exists in Neo4j. Skipping.")
            else:
                # If activity doesn't exist, insert it
                logging.info(f"Inserting activity with ID {row['id']}")
                session.execute_write(create_activity, row['id'], row['ShoeId'], row['type'],
                                      row['distance'], row['elapsed_time'], row['start_date_local'])


# Strava API connection details
config = configparser.ConfigParser()
config.read("config.cfg")

with open('strava_tokens.json') as json_file:
    strava_tokens = json.load(json_file)

# Refresh token if expired
if strava_tokens['expires_at'] < time.time():
    response = requests.post(
        url='https://www.strava.com/oauth/token',
        data={
            'client_id': config.get("CLIENT_ID", 'client_id'),
            'client_secret': config.get("CLIENT_SECRET", 'client_secret'),
            'grant_type': 'refresh_token',
            'refresh_token': strava_tokens['refresh_token']
        }
    )
    new_strava_tokens = response.json()
    with open('strava_tokens.json', 'w') as outfile:
        json.dump(new_strava_tokens, outfile)
    strava_tokens = new_strava_tokens

# Fetch activities from Strava API
logging.info("Fetching activities from Strava API...")

page = 1
url = "https://www.strava.com/api/v3/activities"
access_token = strava_tokens['access_token']
activities = pd.DataFrame(columns=["id", "start_date_local", "type", "distance", "elapsed_time"])

while True:
    response = requests.get(url + '?access_token=' + access_token + '&per_page=200' + '&page=' + str(page))

    if response.status_code != 200:
        logging.error(f"Error fetching activities for page {page}. Status code: {response.status_code}")
        break

    r = response.json()
    if not r:
        logging.info(f"Finished fetching activities. Total pages: {page - 1}")
        break

    new_data = pd.DataFrame(r)
    activities = pd.concat([activities, new_data], ignore_index=True)
    logging.info(f"Fetched {len(r)} activities from page {page}")
    page += 1

# Convert activities to DataFrame
logging.info(f"Converted {len(activities)} activities to a DataFrame.")
df = pd.DataFrame(activities)

# Filter out swimming activities and only keep activities after 9/7/2024
df['date'] = pd.to_datetime(df['start_date_local']).dt.date
df = df[(df['date'] > pd.to_datetime('2024-09-07').date()) & (df['type'] != 'Swim')]  # Exclude swims and filter by date

# Transformations
df['distance'] = df['distance'] * 0.000621371  # Convert meters to miles
df['elapsed_time'] = df['elapsed_time'].apply(lambda x: hours_to_interval(x / 3600))  # Convert to hours and minutes
df['ShoeId'] = df['type'].map({'Run': 8, 'Walk': 10, 'Hike': 7})  # Map activity type to ShoeId

# Reorder columns to match Neo4j
df = df[['id', 'ShoeId', 'type', 'distance', 'elapsed_time', 'start_date_local']]

# Insert activities into Neo4j
logging.info("Inserting data into Neo4j...")
insert_activities(df)

# Close the Neo4j connection
driver.close()

logging.info("Data insertion complete!")
