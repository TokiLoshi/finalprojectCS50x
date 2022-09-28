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

# Factors measured by weight
# Waste
waste_activity_ids_by_weight = {"plastics_recycled":"waste_type_mixed_plastics-disposal_method_landfilled",
"recycled_mixed_plastics":"waste_type_mixed_plastics-disposal_method_recycled",
"mixed_waste_landfill":"waste_type_mixed_msw-disposal_method_landfilled",
"recycled_waste_landfill":"waste_type_mixed_recyclables-disposal_method_landfilled",
"mixed_waste_combusted":"waste_type_mixed_msw-disposal_method_combusted",
"mixed_waste_recycled":"waste_type_mixed_recyclables-disposal_method_recycled"
}

# Factors by energy 
# Electricity 
# Grid_mix_by State 

grid_mix_by_state_activities_by_energy = {"grid_mix_electricity-energy_source_grid_mix" : "electricity-energy_source_grid_mix" }

# Calculate grid mix by state 
states = { "Alabama" : "AL", "Alaska": "AKGD", "Arkansas": "AR", "Arizona" : "AZ", "California": "CA","Colorado" : "CO", "Connecticut": "CT", "DC" : "DC", 
"Delaware" : "DE", "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Iowa": "IA", "Idaho": "ID",
"Illinois": "IL", "Indiana": "IN", "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA", "Massachusetts": "MA", "Maryland": "MD", "Maine": "ME", 
"Michigan": "MI", "Minnesota": "MN", "Missouri": "MO", "Mississippi": "MS", "Montana": "MT", "North_Carolilna": "NC", "North_Dakota": "ND", "Nebraska": "NE", 
"New_England": "NEWE", "New_Hampshire": "NH", "New_Jersey": "NJ", "New_Mexico": "NM", "Nevada": "NV", "New_York": "NY", "Ohio": "OH", "Oklahoma": "OK",
"Oregon":"OR", "Pennsylvania":"PA", "Peurto_Rico":"PR", "Rhode_Island":"RI", "South_Carolina":"SC", "South_Dakota":"SD", "Tennessee":"TN", "Texas":"TX", "Utah":"UT",
"Virginia":"VA", "Vermont":"VT", "Washington":"WA", "West_Virginia": "WV", "Wisconsin":"WI", "Wyoming":"WY",
}

# Factors by volume
fuel_activity_ids_by_volume = {"light_weight_100_biodiesel":"fuel_type_biodiesel_100percent-fuel_use_biodiesel_light_duty_vehicles", 
"medium_to_heavy_duty_100_biodiesel":"fuel_type_biodiesel_100percent-fuel_use_biodiesel_medium_and_heavy_duty_vehicles_5.9_fuel_efficiency",
"passenger_biodiesel":"fuel_type_biodiesel_100percent-fuel_use_biodiesel_passenger_cars",
"compressed_natural_gas_light_duty_vehicles":"fuel_type_compressed_natural_gas-fuel_use_cng_light_duty_vehicles",
"compressed_natural_gas_heavy_duty_vehicles":"fuel_type_compressed_natural_gas-fuel_use_cng_medium_and_heavy_duty_vehicles",
"diesel_light_duty_trucks":"fuel_type_diesel-fuel_use_diesel_light_duty_trucks",
"diesel_heavy_duty_trucks":"fuel_type_diesel-fuel_use_diesel_medium_and_heavy_duty_vehicles",
"diesel_passenger_cars":"fuel_type_diesel-fuel_use_diesel_passenger_cars",
"electric_vehicle":"fuel_type_electricity-fuel_use_electric_vehicle",
"gas_vehicle":"fuel_type_fuel_gas-fuel_use_stationary_combustion",
"gasoline_heavy_duty_vehicles":"fuel_type_motor_gasoline-fuel_use_gasoline_heavy_duty_vehicles",
"gasoline_light_duty_trucks_vans_suvs":"fuel_type_motor_gasoline-fuel_use_gasoline_light_duty_trucks",
"gasoline_motorcycle":"fuel_type_motor_gasoline-fuel_use_gasoline_motorcycles",
"gasoline_passenger_car":"fuel_type_motor_gasoline-fuel_use_gasoline_passenger_cars",
"ships_boats_gasoline":"fuel_type_motor_gasoline-fuel_use_gasoline_ships_and_boats",
"hybrid_gasoline_car":"fuel_type_motor_gasoline-fuel_use_hybrid_gasoline_passenger_cars",
}


# Activities by money $usd
# Buildings
building_types_and_infrastructure = { "commercial_and_farms":"construction-type_commercial_structures_incl_farm_structures", 
"multifamily_residential":"construction-type_multifamily_residential_structures",
"singlefamily_residential":"construction-type_single_family_residential_structures", 
"owner_occupied_housing":"housing-type_owner_occupied_housing", 
"tenant_occupied_housing":"housing-type_tenant_occupied_housing", 
}

# Consumer goods by money
clothing_consumer_goods_activity_ids_by_money = {"clothing":"consumer_goods-type_clothing", "accessories":"consumer_goods-type_clothing_clothing_accessories_stores", 
"drycleaning":"consumer_goods-type_dry_cleaning_laundry", "leather":"consumer_goods-type_leather", "wearing_apparel_furs":"consumer_goods-type_wearing_apparel_furs"
}

building_material_gardening_diy_consumer_goods_activity_ids_by_money = {"diy":"equipment_gardening_diy-type_building_material_garden_equipment_supplies_dealers"
}

food_beverages_tobacco_consumer_goods_activity_ids_by_money = { "fresh_fruits_and_tree_nuts":"arable_farming-type_fresh_fruits_tree_nuts",
  "soybeans_canola_oils":"arable_farming-type_fresh_soybeans_canola_flaxseeds_other_oilseeds", 
  "fresh_vegetables_melons_potatoes":"arable_farming-type_fresh_vegetables_melons_potatoes", 
  "wheat_corn_rice_other_grains":"arable_farming-type_fresh_wheat_corn_rice_other_grains", 
  "greenhouse_mushrooms_nurseries_flowers":"arable_farming-type_greenhouse_crops_mushrooms_nurseries_flowers", 
  "tobacco_cotton_sugarcane_peanuts_sugar_beets_herbs_spices":"arable_farming-type_tobacco_cotton_sugarcane_peanuts_sugar_beets_herbs_spices_other_crops", 
  "other_foods":"consumer_goods-type_all_other_foods", 
  "beverages":"consumer_goods-type_beverages", 
  "bread_baked_goods":"consumer_goods-type_bread_other_baked_goods", 
  "breakfast_cereals":"consumer_goods-type_breakfast_cereals", "breweries_beers":"consumer_goods-type_breweries_beer", 
  "cheese":"consumer_goods-type_cheese", 
  "coffee_and_tea":"consumer_goods-type_coffee_tea", "coffee_crackers_pastas_tortillas":"consumer_goods-type_cookies_crackers_pastas_tortillas", 
  "corn_products":"consumer_goods-type_corn_products", "dairy_products":"consumer_goods-type_dairy_products",
  "distilleries_and_spirits":"consumer_goods-type_distilleries_spirits", "condensed_evaporated_dairy":"consumer_goods-type_dry_condensed_evaporated_dairy", 
  "fish_products":"consumer_goods-type_fish_products", "flavored_drink_concentrates":"consumer_goods-type_flavored_drink_concentrates", 
  "flours_malts":"consumer_goods-type_flours_malts", "milk_butter":"consumer_goods-type_fluid_milk_butter", "frozen_food":"consumer_goods-type_frozen_food", 
  "preserved_fruits_vegetables":"consumer_goods-type_fruit_vegetable_preservation", 
  "ice_cream_frozen_desserts":"consumer_goods-type_ice_cream_frozen_desserts", "meat_products_beef":"consumer_goods-type_meat_products_beef", 
  "meat_products_pork":"consumer_goods-type_meat_products_pork", "meat_products_poultry":"consumer_goods-type_meat_products_poultry", 
  "processed_rice":"consumer_goods-type_processed_rice", "refined_vegetable_and_seed_oils":"consumer_goods-type_refined_vegetable_olive_seed_oils", 
  "seafood":"consumer_goods-type_seafood", "seasonings_dressings":"consumer_goods-type_seasonings_dressings", "snack_foods":"consumer_goods-type_snack_foods", 
  "soft_drinks_bottled_water":"consumer_goods-type_soft_drinks_bottled_water_ice", "soybean_oilseed":"consumer_goods-type_soybean_other_oilseed_processing", 
  "sugar":"consumer_goods-type_sugar", "sugar_candy_chocolate":"consumer_goods-type_sugar_candy_chocolate", "tobacco":"consumer_goods-type_tobacco_products", 
  "vegetable_oils_fats":"consumer_goods-type_vegetable_oils_fats", "wineries_and_wine":"consumer_goods-type_wineries_wine"
}

furnishings_consumer_goods_activity_ids_by_money={"carpets_and_rugs":"consumer_goods-type_carpets_rugs",
"curtains_and_linens":"consumer_goods-type_curtains_linens", "fabrics":"consumer_goods-type_fabric", 
"furniture":"consumer_goods-type_furniture_other_manufactured_goods_not_elsewhere_specified", 
"musical_instruments_brushes_brooms_mops":"consumer_goods-type_gaskets_seals_musical_instruments_fasteners_brooms_brushes_mop_other_misc._goods",
"upholstered_furniture":"consumer_goods-type_home_furniture_upholstered", "non-upholstered_furniture":"consumer_goods-type_home_furniture_wood_nonupholstered", 
"mattresses_blinds_shades":"consumer_goods-type_mattresses_blinds_shades", 
"office_furniture":"consumer_goods-type_office_furniture_custom_architectural_woodwork_millwork", 
"other_nonupholstered_furniture":"consumer_goods-type_other_household_nonupholstered_furniture", 
"paint_coatings":"consumer_goods-type_paints_coatings", "plywood_and_veneer":"consumer_goods-type_plywood_veneer", 
"shelving_and_lockers":"consumer_goods-type_shelving_lockers", "soaps_cleaning_compounds":"consumer_goods-type_soap_cleaning_compounds", 
"wooden_cabinets":"consumer_goods-type_wood_kitchen_cabinets_countertops", "wooden_windows_doors":"consumer_goods-type_wooden_windows_door_flooring"
}

general_merchandise_consumer_goods_activity_ids_by_money={
"general_retail":"general_retail-type_general_merchandise_stores",
"retail_trade":"general_retail-type_retail_trade_except_of_motor_vehicles_motorcycles_repair_of_personal_household_goods_services"
}

paper_products_consumer_goods_activity_ids_by_money= {
 "napkins_diapers_tissues_sanitary_paper":"paper_products-type_sanitary_paper_tissues_napkins_diapers",
 "paper_stationary":"paper_products-type_stationery" 
}

personal_care_consumer_goods_activity_ids_by_money={"jewelry_silverware":"consumer_goods-type_jewelry_silverware",
"salons_barber_shops":"consumer_goods-type_salons_barber_shops",
"toiletries":"consumer_goods-type_toiletries"
}

recreational_consumer_goods_activity_ids_by_money = {"amusement_parks_arcades":"consumer_goods-type_amusement_parks_arcades", "books":"consumer_goods-type_books", 
"print_media":"consumer_goods-type_books_newspapers_magazines_other_print_media", "cable_subscription_programming":"consumer_goods-type_cable_subscription_programming", 
"directory_mailing_other_publishers":"consumer_goods-type_directory_mailing_list_other_publishers", "dog_cat_food":"consumer_goods-type_dog_cat_food", 
"dolls_toys_games":"consumer_goods-type_dolls_toys_games", "fertilizers":"consumer_goods-type_fertilizers", 
"gambling_establishments":"consumer_goods-type_gambling_establishments_except_casino_hotels", "golf_ski_marinas_rec_centers":"consumer_goods-type_golf_courses_marinas_ski_resorts_fitness_other_rec_centers_industries", 
"ink_cartridges":"consumer_goods-type_ink_ink_cartridges", "magazines_journals":"consumer_goods-type_magazines_journals", 
"movies_film":"consumer_goods-type_movies_film", "museums_parks":"consumer_goods-type_museums_historical_sites_zoos_parks", 
"newspapers":"consumer_goods-type_newspapers", "other_animal_food":"consumer_goods-type_other_animal_food", 
"performances":"consumer_goods-type_performances", "pesticides":"consumer_goods-type_pesticides", 
"radio_and_television":"consumer_goods-type_radio_television", "recreationa_cultural_sporting":"consumer_goods-type_recreational_cultural_sporting_services", 
"scenic_sightseeing":"consumer_goods-type_scenic_sightseeing_transportation_support_activities_for_transportation", 
"software":"consumer_goods-type_software", "sound_recording":"consumer_goods-type_sound_recording", 
"sports_athletic_goods":"consumer_goods-type_sporting_athletic_goods", "trailers_campers":"consumer_goods-type_travel_trailer_campers"
}

# Electrical in the home 
electrical_activity_ids_by_money = { "electrical_appliances": "electrical_equipment-type_small_electrical_appliances",
"major_appliances":"electrical_equipment-type_major_home_appliances_except_ovens_stoves_refrigerators_laundry_machines",
"light_bulbs":"electrical_equipment-type_light_bulbs",
"fridges":"electrical_equipment-type_home_refrigerators_freezers",
"laundry_machines":"electrical_equipment-type_home_laundry_machines",
"cooking_appliances":"electrical_equipment-type_home_cooking_appliances",
"gasoline_fuels_by_petroleum_refining" : "fuel_type_gasoline_fuels_by_products_of_petroleum_refining-fuel_use_na",
}

# Financial Institutions
financial_activity_ids_by_money = { "funds/trusts_financial_vehicles":"financial_services-type_funds_trusts_financial_vehicles",
"investment_banking_portfolio_management":"financial_services-type_investment_advice_portfolio_management_other_financial_advising_services",
"securities_commodities":"financial_services-type_securities_commodities_brokerage_exchanges",
"insurance_pension_excluding_social_security":"insurance-type_insurance_pension_funding_services_except_compulsory_social_security_services",
"insurance_agencies_brokerages":"insurance-type_insurance_agencies_brokerages",    
}

# Restaurants and Hotels
restaurant_activity_ids_by_money = {"full_restaurant":"consumer_services-type_full_service_restaurants",
"camping":"accommodation_type_hotels_campgrounds",
"hotels":"accommodation_type_hotel_stay",
}

# Transport 
transport_activity_ids_by_money = {"consumer_goods-type_clothing": "consumer_goods-type_clothing",
"passenger_ground_transport":"passenger_vehicle-vehicle_type_passenger_ground_transport-fuel_source_na-distance_na-engine_size_na",
"passenger_bus":"passenger_vehicle-vehicle_type_bus-fuel_source_na-distance_na-engine_size_na",
# Short haul is under 300 miles
"air_travel_short_haul":"passenger_flight-route_type_na-aircraft_type_na-distance_lt_300mi-class_na-rf_na",
# Medium haul is between 30 and 2300 miles 
"air_travel_medium_haul":"passenger_flight-route_type_na-aircraft_type_na-distance_gt_300mi_lt_2300mi-class_na-rf_na",  
"air_travel_long_haul":"passenger_flight-route_type_na-aircraft_type_na-distance_gt_2300mi-class_na-rf_na",
"subway_tram":"passenger_train-route_type_urban-fuel_source_na",
"intercity_rail":"passenger_train-route_type_intercity_other_routes-fuel_source_na",
"intercity_rail_northeast":"passenger_train-route_type_intercity_northeast_corridor-fuel_source_na",
"intercity_amtrack":"passenger_train-route_type_intercity-fuel_source_na",
"intercity_national_average":"passenger_train-route_type_intercity-fuel_source_na",
"commuter_rail":"passenger_train-route_type_commuter_rail-fuel_source_na"   
}

# Activities by miles
activity_ids_by_miles = {"domestic_flight": "passenger_flight-route_type_domestic-aircraft_type_jet-distance_na-class_na-rf_included",
"":"",
"":"",
"":"",
"":"",    
}
activity_ids_by_people = {"staying_in_hotel":"accommodation_type_hotel_room",
"":"",
"":"",
"":"",
"":"",  
}

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


# Calculate the impact of mixedplastics waste
def impact_by_weight(activity_ids):
  """Calculate the impact of not recycling"""
  api_key = os.getenv('CLIMATIQ_API')
  
  # Get estimate URL
  estimate_url = "https://beta3.api.climatiq.io/estimate"
  
  # Activity ID from Data Explorer 
  activity_id = activity_ids
  
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
# An estimated 80% of indirect GHG emissions come from households (5.43 gigatons) - 82.3% are produced domestically (https://www.pbs.org/newshour/science/5-charts-show-how-your-household-drives-up-global-greenhouse-gas-emissions)
# Housing accounts for 33.5%, Transportation 29.8%, Services 19.3% and Food 16.7% (Domestic)
# Housing - the biggest contributor is Utilities (25%)
# Transporation - the biggest contributor is Fuels (23%)
# Food - the biggest contributors are not buying locally and sourcing foods from overseas (17.4%)
# Fuel
# Look into the impact of financial institutions and how they invest in fossil fuels
