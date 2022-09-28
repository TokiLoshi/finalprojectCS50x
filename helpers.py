import os
from urllib import response
import requests
import urllib.parse
import json
import string
import requests
import random
from dotenv import load_dotenv
from flask import redirect, render_template, request, session
from functools import wraps

# from symbol import parameters

load_dotenv()

# Adopted from code from CS50 Pset 9 - Finance
def apology(message, code=400):
  """Render apology message"""
  def escape(s):
    """
    Escape special characters.
    https://github.com/jacebrowning/memegen#special-characters
    """
    for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                      ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
        s = s.replace(old, new)
    return s
  return render_template("apology.html", top=code, bottom=escape(message)), code

# Adopted from code from CS50 Pset 9 - Finance
def login_required(f):
    """Decorate routes to require login.
    https://flask.palletsprojects.com/en/1.1.x/patters/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
      if session.get("user_id") is None:
        return redirect("/login")
      return f(*args, **kwargs)
    return decorated_function

# Adopted from CS50 Pset9 - Finance:
def usd(value):
  """Format value as USD"""
  return f"${value:,.2f}"

def random_leaderboardname():
  words = []
  with open("adjectives.txt", 'r') as file:
    data = file.read()
    word = (data.split(' '))
    words.append(word)
    # Resource for checking how to make a random choice https://www.geeksforgeeks.org/pulling-a-random-word-or-string-from-a-line-in-a-text-file-in-python/
    nouns = []
    with open("nouns.txt", 'r') as file: 
      info = file.read()
      noun = (data.split(' '))
      nouns.append(noun)
    random_adjective = random.choice(data.split())
    random_noun = random.choice(info.split())
    random_name = random_adjective + "-" + random_noun  
  return random_name

# Generate a random temporary password 
# https://geekflare.com/password-generator-python-code/    
def generate_temp_password():
  
  # Establish password length
  length = 8

  # Define characters to use when generating a password
  characters = list(string.ascii_letters + string.digits + "!@#$%^&*()")

  # Shuffle characters 
  random.shuffle(characters)
  
  # Choose random characters from the list
  password = []
  for i in range(length):
    password.append(random.choice(characters))

  # Shuffle password 
  random.shuffle(password)

  # Convert list to string and print
  password = ((" ".join(password)).replace(",", " ")).replace(" ", "")
  return password


# Making your first API call with Climatiq https://www.youtube.com/watch?v=jbx3q_A3yyo 
# How to use the climatiq API with Python https://www.climatiq.io/docs/guides/using-python
# Climatiq is an open API on creative commons https://github.com/climatiq/Open-Emission-Factors-DB/blob/main/LICENSE 
# *** Need to check how to attribute the data and display it 

def lookup():
  """Call API to search"""
  # API KEY 
  api_key = os.getenv('CLIMATIQ_API')
  print("API KEY For Climatique: ", api_key)
  search_url = 'https://beta3.api.climatiq.io/search'
  query = 'grid mix'
  region = 'AU'
  query_params = {
    # Free text query can be written as the "query" parameter 
    'query': query,
    # You can also filter on region, year, source and more
    # "AU" is Australia 
    'region': "AU"
  }
  # You must always specify your AUTH token in the "Authorization" header like this.
  authorization_headers = {'Authorization': f"Bearer: {api_key}"}

  # This performs the request and returns the result as JSON
  response = requests.get(search_url, params=query_params, headers=authorization_headers).json()

  # And here you can do whatever you want with the results
  print(response)

def estimate():
  """Calls on the API for and estimate"""
  
  # Get API key
  api_key = os.getenv('CLIMATIQ_API')
  
  # Get estimate URL
  estimate_url = 'https://beta3.api.climatiq.io/estimate'
  
  # The activity ID for the emission factor. You can find this via the search endpoint listed above
  # or via the Data Explorer 
  activity_id = "electricity-energy_source_grid_mix"
  
  # Climatiq has many regions with the same activity id, representing the power grid in different countries.
  # We'd like to get the power for Australia specifically, so we will need to specify a region. 
  # You can also see the region for different emission factors in the data explorer. 
  region = "AU"

  # We must also specify how much electricity generation we would like to make the estimate for. 
  # In this case we will do it for 100 kilowatt-hours. 
  # Different emission factors have different requirements as to what units they support 
  # You can see the units supported by an emission factor in the data explorer 
  # and find more documentation about units in the API documentation 
  parameters = {
    "energy": 100, 
    "energy_unit": "kWh"
  }
  json_body = {
    "emission_factor": {
      "activity_id": activity_id,
      "region": region,
    },
    # Specifically how much we are estimating for 
    "parameters": parameters
  } 

  # You must always specify your AUTH token in the "Authorization header like this."
  authorization_headers = {"Authorization": f"Bearer: {api_key}"}

  # We send a POST request to the estimate endpoint with a json body 
  # and the correct authorization headers. 
  # This line will send the request and retrieve the body as JSON. 
  response = requests.post(estimate_url, json=json_body, headers=authorization_headers).json()
  
  # You can now do anything you want with the response
  print(response)
  return {
    "Carbon_emissions" : response['co2e'],
    "Carbon_unit": response['co2e_unit'],
    "C02_calculation_source": response['co2e_calculation_origin'],
    "Emission id": response['emission_factor']['id'],
    "Year": response['emission_factor']['year'],
    "Region": response['emission_factor']['region'],
    "Category": response['emission_factor']['lca_activity'],
    "Data Quality": response['emission_factor']['data_quality_flags']

  }

def lifecycle():
  """Work out lifecycle activities"""
  life_cycle_activity = 'https://beta3.api.climatiq.io/emission-factors/lca-activities'


# Accomodation 
def accomodation():
  """Tracks footprint for accomodation"""
  api_key = os.getenv('CLIMATIQ_API')
  
  # Get estimate URL
  estimate_url = 'https://beta3.api.climatiq.io/estimate'

  emission_factor_id = 'baf85baa-478a-4579-8fce-12b90d061617'
  
  # Activity ID from Data Explorer 
  activity_id = "accommodation_type_hotel_room"
  
  # Set region and parameters
  region = "USA"
  parameters = {
    "number": 3 
  }
  json_body = {
    "emission_factor": {
      "activity_id": activity_id,
    },
    # Specifically how much we are estimating for 
    "parameters": parameters
  } 
  # You must always specify your AUTH token in the "Authorization header like this."
  authorization_headers = {"Authorization": f"Bearer: {api_key}"}
  response = requests.post(estimate_url, json=json_body, headers=authorization_headers).json()
  print(response)
  return {
    "Carbon_emissions" : response['co2e'],
    "Carbon_unit": response['co2e_unit'],
    "Emission id": response['emission_factor']['id'],
    "Year": response['emission_factor']['year'],
    "Region": response['emission_factor']['region'],
    "Category": response['emission_factor']['category'], 
    "LCA_ACTIVITY": response['emission_factor']['lca_activity'],
    "Data Quality": response['emission_factor']['data_quality_flags']
  }

# Air Travel
def air_travel():
  api_key = os.getenv('CLIMATIQ_API')
  
  # Get estimate URL
  estimate_url = "https://beta3.api.climatiq.io/estimate"
  
  # Activity ID from Data Explorer 
  activity_id = "passenger_flight-route_type_domestic-aircraft_type_jet-distance_na-class_na-rf_included"
  
  # Set region and parameters
  parameters = {
    "passengers": 4,
    "distance": 100,
    "distance_unit": "mi" 
  }
  json_body = {
    "emission_factor": {
      "activity_id": activity_id,
    },
    # Specifically how much we are estimating for 
    "parameters": parameters
  } 
  # You must always specify your AUTH token in the "Authorization header like this."
  authorization_headers = {"Authorization": f"Bearer: {api_key}"}
  response = requests.post(estimate_url, json=json_body, headers=authorization_headers).json()
  print(response)
  return {
    "Carbon_emissions" : response['co2e'],
    "Carbon_unit": response['co2e_unit'],
    "C02_calculation_source": response['co2e_calculation_origin'],
    "Emission id": response['emission_factor']['id'],
    "Year": response['emission_factor']['year'],
    "Region": response['emission_factor']['region'],
    "Category": response['emission_factor']['lca_activity'],
    "Data Quality": response['emission_factor']['data_quality_flags']
  }
 
# An estimated 80% of indirect GHG emissions come from households (5.43 gigatons) - 82.3% are produced domestically (https://www.pbs.org/newshour/science/5-charts-show-how-your-household-drives-up-global-greenhouse-gas-emissions)
# Housing accounts for 33.5%, Transportation 29.8%, Services 19.3% and Food 16.7% (Domestic)

# Housing - the biggest contributor is Utilities (25%)
def utilities():
  """Allows user to calculate their average impact""" 


# Transporation - the biggest contributor is Fuels (23%)
def transportation():
  """Allows user to calculate their transportation costs"""

# Food - the biggest contributors are not buying locally and sourcing foods from overseas (17.4%)
def food():
  """Allows user to calculate their impact based on their diet"""

# Clothing and Footwear
def clothing_and_footwear():
  """Allows user to calculate their impact based on their fashion in monetary terms"""
  api_key = os.getenv('CLIMATIQ_API')
  
  # Get estimate URL
  estimate_url = "https://beta3.api.climatiq.io/estimate"
  
  # Activity ID from Data Explorer 
  activity_id = "consumer_goods-type_clothing"
  
  # Set region and parameters
  parameters = {
    "money": 100,
    "money_unit": "usd",
  }
  json_body = {
    "emission_factor": {
      "activity_id": activity_id,
    },
    # Specifically how much we are estimating for 
    "parameters": parameters
  } 
  # You must always specify your AUTH token in the "Authorization header like this."
  authorization_headers = {"Authorization": f"Bearer: {api_key}"}
  response = requests.post(estimate_url, json=json_body, headers=authorization_headers).json()
  print(response)
  return {
    "Carbon_emissions" : response['co2e'],
    "Carbon_unit": response['co2e_unit'],
    "C02_calculation_source": response['co2e_calculation_origin'],
    "Emission id": response['emission_factor']['id'],
    "Year": response['emission_factor']['year'],
    "Region": response['emission_factor']['region'],
    "Category": response['emission_factor']['lca_activity'],
    "Data Quality": response['emission_factor']['data_quality_flags']
  }


# Food/Beverages/Tobacco
# Fuel 
# Heat and Steam
# Homeworking
# Paper and Cardboard Waste 
# Personal Care and Accessories
# Rail Travel 
# Recreation and Culture 
# Road Travel 
# Vehicles 

# Plastic usage
def mixedplastics_recycle():
  """Calculate the impact of recycling mixed plastics"""

def mixedplastics_landfill():
  """Calculate the impact of not recycling"""
  api_key = os.getenv('CLIMATIQ_API')
  
  # Get estimate URL
  estimate_url = "https://beta3.api.climatiq.io/estimate"
  
  # Activity ID from Data Explorer 
  activity_id = "waste_type_mixed_plastics-disposal_method_recycled"
  
  # Set region and parameters
  parameters = {
    "weight": 100,
    "weight_unit": "t",
  }
  json_body = {
    "emission_factor": {
      "activity_id": activity_id,
    },
    # Specifically how much we are estimating for 
    "parameters": parameters
  } 
  # You must always specify your AUTH token in the "Authorization header like this."
  authorization_headers = {"Authorization": f"Bearer: {api_key}"}
  response = requests.post(estimate_url, json=json_body, headers=authorization_headers).json()
  print(response)
  return {
    "Carbon_emissions" : response['co2e'],
    "Carbon_unit": response['co2e_unit'],
    "C02_calculation_source": response['co2e_calculation_origin'],
    "Emission id": response['emission_factor']['id'],
    "Source": response['emission_factor']['source'],
    "Year": response['emission_factor']['year'],
    "Region": response['emission_factor']['region'],
    "Categor": response['emission_factor']['category'],
    "LCA": response['emission_factor']['lca_activity'],
    "Data Quality": response['emission_factor']['data_quality_flags']
  }

# Convert kg to tonnes? 