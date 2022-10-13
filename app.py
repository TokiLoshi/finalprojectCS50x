
from audioop import avg
from crypt import methods
from curses import use_default_colors
import email
from gc import garbage
from hashlib import new
from http.client import ResponseNotReady
import os
import string
import random
from dataclasses import is_dataclass
from re import template
import re
from webbrowser import get
from cs50 import SQL 
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import apology, formatfloat, login_required, lookup, random_leaderboardname, generate_temp_password, co2, co2lifetime, formatfloat, customicon
from helpers import impact_by_weight, impact_by_energy, estimate, impact_by_volume, impact_by_money, impact_by_distance, impact_by_number, impact_by_flights, impact_by_road
from flask_mail import Mail, Message
from flask_mail_sendgrid import MailSendGrid
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# Configure application (adapted from CS50 PSET 9 and Stackoverflow https://stackoverflow.com/questions/31002890/how-to-reference-a-html-template-from-a-different-directory-in-python-flask)
app = Flask(__name__, template_folder="./templates")


# Ensure templates are auto-reloaded (from CS50 PSET 9)
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Custom filter (adapted from CS50 PSET 9)
# app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of cookies) (from CS50 PSET 9)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure Email
# https://cs50.harvard.edu/college/2022/spring/notes/9/
# app.config["MAIL_DEFAULT_SENDER"] = os.environ["MAIL_DEFAULT_SENDER"]
# app.config["MAIL_PASSWORD"] = os.environ["MAIL_PASSWORD"]
# app.config["MAIL_PORT"] = 587
# app.config["MAIL_SERVER"] = "smtp.gmail.com"
# app.config["MAIL_USE_TLS"] = True
# app.config["MAIL_USERNAME"] = os.environ["MAIL_USERNAME"]
# mail = Mail(app)

app.config['MAIL_SENDGRID_API_KEY'] = os.environ['SENDGRID_API']
mail = MailSendGrid(app)

# Configure CS50 Library to use SQLite and adapt to tranfer to PostGres for Heroku deployment
# https://cs50.readthedocs.io/heroku/
# uri = os.getenv("DATABASE_URL")
# if uri.startswith("postgres:"):
#   uri = uri.replace("postgress://", "postgresql://")
db = SQL("sqlite:///carbon.db")

# Handle cache (from CS50 PSET 9)
@app.after_request
def after_request(response):
  """Ensure responses aren't cached"""
  response.headers["Cache-control"] = "no-cache, no-store, must-revalidate"
  response.headers["Expires"] = 0
  response.headers["Pragma"] = "no-cache"
  return response

# About page
@app.route("/about", methods=["GET", "POST"])
def about():
  """Provides information about the site and why it was created"""
  return render_template("/about.html")

# Users account page
@app.route("/account", methods=["GET", "POST"])
@login_required
def account():
  """Users account page with their username information"""
  get_user_info = db.execute("SELECT name, leaderboardname, email, datejoined FROM users WHERE id=?", session.get("user_id"))
  print("User's info: ", get_user_info)
  if len(get_user_info) == 0:
      name = "unknown"
      leaderboardname = "unknown"
      emailaddy =  "unknown"
      datejoined = "unknown"
  else:
    for info in get_user_info:
      name = info['name']
      leaderboardname = info['leaderboardname']
      emailaddy = info['email']
      datejoined = info['datejoined']
  print("USER INFO: ", get_user_info)
  if request.method == "POST":
    print("We're in post")
    return render_template("/changepassword.html")
  else:
    print("We're in get")
  return render_template("/account.html", name=name, leaderboardname=leaderboardname, emailaddy=emailaddy, datejoined=datejoined)

# Users activity page
@app.route("/activity", methods=["GET", "POST"])
@login_required
def activity():
  """Allows users to track their activities and see how that affects their carbon score"""
  return render_template("/activity.html")

# Calculator page for instructions and household calculations
@app.route("/calculator", methods=["GET", "POST"])
@login_required
def calculator():
  """Quiz user takes to tally up their carbon score"""
  if request.method == "POST":
    # Get information from form
    building = request.form.get("building")
    state = request.form.get("state")
    household_occupants = request.form.get("household_occupants")
    recycling = int(request.form.get("recycling"))
    waste_frequency = request.form.get("rubbish")
    utility_bill = float(request.form.get("utilitybill"))
    drycleaning = float(request.form.get("drycleaning"))
    region = "US"

    # HACK: 
    # This is a once off we might want to factor into a lifetime footprint
    # Buildings multifamily is 0.113kg/USD median cost per unit is $64,500 0 $86,000 https://www.multifamily.loans/apartment-finance-blog/multifamily-construction-costs-an-investor-guide#:~:text=According%20to%20the%20most%20recent,%2464%2C500%20to%20%2486%2C000%20per%20unit. 
    multifamily_median = (64500 + 86000)/2
    singlefamily_median = 428700
    # Single family home is 0.226kgs/USD according to a service by the Motley Fool https://www.fool.com/the-ascent/research/average-house-price-state/#:~:text=Average%20home%20price%20in%20the%20United%20States%3A%20%24428%2C700&text=That's%20a%2030%25%20increase%20from,when%20the%20median%20was%20%24329%2C000.&text=Median%20sales%20price%20of%20homes,of%20homes%20in%20the%20U.S.&text=Data%20source%3A%20Federal%20Reserve%20Bank%20of%20St
    
    if building is None: 
      building = "Info not provided"
      building_emissions = "Need more info to calculate"
      building_impact = "Unknown"
    elif building == "construction-type_multifamily_residential_structures":
      building_emissions = impact_by_money(building, region, multifamily_median)
      building_impact = building_emissions['Carbon_emissions']
    elif building == "construction-type_single_family_residential_structures":
      building_emissions = impact_by_money(building, region, singlefamily_median)
      building_impact = building_emissions['Carbon_emissions']
    else:
      print("Dunno what happend but they got something through")

    # Work out impact by electricity
    electricity_activity_id = "electricity-energy_source_grid_mix"
    if state is None:
      state = "Info not provided"
      impact_electricity = "Need more info to calculate"
    elif utility_bill == 0:
      impact_electricity = 0
    else:  
      region = state
      energy = utility_bill
      electricity_emissions = impact_by_energy(electricity_activity_id, region, energy)
      # Estimating waste per month so multiply by 12 to get the estimation for the year
      impact_electricity = (electricity_emissions['Carbon_emissions'] * 12)
      electricity_emissions_unit = electricity_emissions['Carbon_unit']

    # HACK:
    # Impact by waste typical kitchen bag can hold up to 15lbs so we will estimate with 12lbs https://westerndisposalservices.com/how-much-does-it-weigh-household-trash/ 
    landfill_id = "waste_type_mixed_msw-disposal_method_landfilled"
    recycling_id = "waste_type_mixed_recyclables-disposal_method_recycled"
    if waste_frequency is None:
      waste_frequency = "Info not provided"
      impact_landfill = "Need more info to calculate"
      impact_recycling = "Need more info to calculate"
    else:
      total_weight_pounds =  12 * int(waste_frequency)
      # Convert to kg by dividing pounds by 2.2045 https://www.wikihow.com/Convert-Pounds-to-Kilograms
      kg = (total_weight_pounds / 2.2046)
      weight_kg = float("{:.2f}".format(kg))
      
      # Convert to percentage
      percentage_recycled = recycling / 100
      percentage_landfil = (100 - recycling)
      weight_recycled = weight_kg * percentage_recycled
      weight_landfill = float(weight_kg - weight_recycled)
      landfill_emissions = impact_by_weight(landfill_id, weight_landfill)
      
      # Waste is asked per week so multiply by 52 for landfil and recycling to get estimated emissions per year
      impact_landfill = (landfill_emissions['Carbon_emissions']) * 52
      landfill_unit = landfill_emissions['Carbon_unit'] 
      recycling_emissions = impact_by_weight(recycling_id, weight_recycled)
      impact_recycling = (recycling_emissions['Carbon_emissions']) * 52
      recycling_unit = recycling_emissions['Carbon_unit']
    
    # Impact of drycleaning per person in house:
    if drycleaning == 0 :
      drycleaning_impact = 0
      print("Drycleaning impact: ", drycleaning_impact)
    else:
      drycleaning_cost_per_person = float(drycleaning) * 12
      drycleaning_region = "US"
      drycleaning_activity_id = "consumer_goods-type_dry_cleaning_laundry"
      drycleaning_emissions = impact_by_money(drycleaning_activity_id, drycleaning_region, drycleaning_cost_per_person)
      drycleaning_impact = drycleaning_emissions['Carbon_emissions']
      drycleaning_unit = drycleaning_emissions['Carbon_unit']

    # Calculate Total General Footprint for house and for individual and update DB
    total_footprint_general = co2(impact_electricity + impact_landfill + impact_recycling + drycleaning_impact)
    individual_footprint = co2((impact_electricity + impact_landfill + impact_recycling + drycleaning_impact) / float(household_occupants))
    update_db_general_footprint = db.execute("INSERT INTO footprint (user_id, building, building_impact, state, electricity, electricity_impact, household_occupants, waste_frequency, recycling, landfill_impact, recycling_impact, drycleaning, drycleaning_impact, total_footprint_general) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", session.get("user_id"), building, building_impact, state, utility_bill, impact_electricity, household_occupants, waste_frequency, recycling, impact_landfill, impact_recycling, drycleaning, drycleaning_impact, total_footprint_general)
    return render_template("/calculatortransport.html")
  else:
    check_not_answered = db.execute("SELECT user_id FROM footprint")
    if check_not_answered is None:
      return render_template("/calculator.html")
    else:
      user_check = 0
      for id in check_not_answered:
        user_check = id['user_id']
      if user_check == session.get("user_id"):
        their_stuff = db.execute("SELECT * FROM consumption_footprint WHERE user_id=?", user_check)
        flash("You've already answered this, but you can update your answers in consumption")
        return render_template("/calculatorconsumptionupdate.html")
      else:
        return render_template("/calculator.html")

# Calculator page for transport
@app.route("/calculatortransport", methods=["GET", "POST"])
@login_required
def calculatortransport():
  """Quiz user takes to tally up their carbon score"""
  if request.method == "POST":
    work_situation = request.form.get("work_situation")
    commuter_days = request.form.get("commuter_days")
    commuter_distance = request.form.get("commuter_distance")
    transport_mode = request.form.get("transport_mode")
    short_haul = request.form.get("short_haul")
    medium_haul = request.form.get("medium_haul")
    long_haul = request.form.get("long_haul")
    transport_cost = int(request.form.get("transport_cost"))
    region = "US"

    # HACK:
    # Impact of total number of short_haul_flights 0.22701067kg/passengermile
    short_haul_id = "passenger_flight-route_type_na-aircraft_type_na-distance_lt_300mi-class_na-rf_na"
    short_distance = 300
    short_haul_emissions = impact_by_flights(short_haul_id, short_distance)
    short_haul_impact = short_haul_emissions['Carbon_emissions']
   
    # Impact of total_number of long haul flights
    medium_haul_id = "passenger_flight-route_type_na-aircraft_type_na-distance_gt_300mi_lt_2300mi-class_na-rf_na" 
    medium_distance = 2300
    medium_haul_emissions = impact_by_flights(medium_haul_id, medium_distance)
    medium_haul_impact = medium_haul_emissions['Carbon_emissions']
   
    # Impact of total number of long haul flights
    long_haul_id = "passenger_flight-route_type_na-aircraft_type_na-distance_gt_2300mi-class_na-rf_na"
    long_distance = 3500
    long_haul_emissions = impact_by_flights(long_haul_id, long_distance)
    long_haul_impact = long_haul_emissions['Carbon_emissions']
    
    # Work out total commuter distance per week
    distance_commute = (float(commuter_distance) * 2) * int(commuter_days)
    commuter_emissions = impact_by_road("passenger_vehicle-vehicle_type_passenger_ground_transport-fuel_source_na-distance_na-engine_size_na", transport_cost)
    commuter_impact = commuter_emissions['Carbon_emissions'] * 12

    # Calculate transport footprint total and insert into DB
    total_transport_emissions = co2(short_haul_impact + medium_haul_impact + long_haul_impact + commuter_impact)
                                                                                                                                                                                                                                                                                                                                   
    update_transport_footprint = db.execute("INSERT into transport_footprint (user_id, work_situation, commuter_days, commuter_distance, transport_mode, transport_cost, commuter_impact, short_haul, short_haul_impact, medium_haul, medium_haul_impact, long_haul, long_haul_impact, transport_footprint_total) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", session.get("user_id"), work_situation, commuter_days, commuter_distance, transport_mode, transport_cost, commuter_impact, short_haul, short_haul_impact, medium_haul, medium_haul_impact, long_haul, long_haul_impact, total_transport_emissions)
    return render_template("/calculatorconsumption.html")
  else: 
    print("Nope")
    return render_template("/calculatortransport.html")

# Calculator page for consumption
@app.route("/calculatorconsumption", methods=["GET", "POST"])
@login_required
def calculatorconsumption():
  """Quiz user takes to tally up their carbon score"""
  if request.method == "POST":
    beef = request.form.get("beef")
    pork = request.form.get("pork")
    chicken = request.form.get("chicken")
    flexitarian = request.form.get("flexitarian")
    new_clothes = request.form.get("new_clothes")
    restaurants = request.form.get("restaurants")
    accessories = request.form.get("accessories")
    appliances = request.form.get("appliances")
    hotels = request.form.get("hotels")
    region = "US"
    # Work out impact from food consumption
    # Impact by beef consumption 2021 3.7609kg/EUR 
    # We might need to look further into this guessing each person eats half a pound per adult
    beef_activity_id = "consumer_goods-type_meat_products_beef"
    beef_frequency = int(beef)
    beef_price = (5.12 / 2)
    # To get the spend we need to figure out how many times a week the person is eating it multiplied by the average cost per serving and then by number of weeks in a year
    beef_spend = (beef_price * beef_frequency * 52)
    beef_emissions = impact_by_money(beef_activity_id, region, beef_spend)
    beef_impact = beef_emissions['Carbon_emissions']
    
    
    # We might want to look at port as well which is 2021 and higher 0.4543 kg/USD
    pork_activity_id = "consumer_goods-type_meat_products_pork"
    pork_frequency = int(pork)
    # Average price obtained from USDA https://www.ams.usda.gov/mnreports/lsmnprpork.pdf
    pork_prices = [1.21, 11.21, 9.64, 11.26, 8.89, 9.04, 16.22, 9.56, 8.20, 7.92, 8.83, 9.04, 8.79, 8.76, 11.25]
    sum_pork_prices = sum(pork_prices)
    average_pork_prices = sum(pork_prices) / len(pork_prices)
    # We might want to weight this by popularity at a later stage
    # To get the spend we need to figure out how many times a week the person is eating it multiplied by the average cost per serving and then by number of weeks in a year
    pork_spend = (int(pork_frequency) * average_pork_prices) * 52
    pork_emissions = impact_by_money(pork_activity_id, region, pork_spend)
    pork_impact = pork_emissions['Carbon_emissions']
    
    
    # Chicken is 2021 at 0.6325 USD/kg
    chicken_activity_id = "consumer_goods-type_meat_products_poultry"
    # To get the spend we need to figure out how many times a week the person is eating it multiplied by the average cost per serving and then by number of weeks in a year
    chicken_frequency = int(chicken)
    # Stats for chicken spend https://www.bls.gov/regions/mid-atlantic/data/averageretailfoodandenergyprices_usandmidwest_table.htm
    chicken_spend = (1.87 / 2) * 52
    chicken_emissions = impact_by_money(chicken_activity_id, region, chicken_spend)
    chicken_impact = chicken_emissions['Carbon_emissions']
    
    # Hotel impact at 16.1kg (default 2022) per night 
    hotel_activity_id = "accommodation_type_hotel_stay"
    if len(hotels) == 0: 
      hotels = "No info given"
      hotels_impact = "Need more information to calculate"
      hotel_add = 0
    else:
      hotels = int(hotels)
      hotels_emissions = impact_by_number(hotel_activity_id, hotels, region)
      hotels_impact = hotels_emissions['Carbon_emissions']
      hotels_add = hotels_impact

    # Impact by clothes 2020 - 1.947kg/usd 
    clothing_activity_id = "consumer_goods-type_clothing"
    if len(new_clothes) == 0:
      clothing_spend = "No info given"
      clothing_impact = "Need more information to calculate"
      clothing_add = 0 
    else:
      clothing_spend = int(new_clothes)
      clothing_emissions = impact_by_money(clothing_activity_id, region, clothing_spend)
      clothing_impact = clothing_emissions['Carbon_emissions']
      clothing_add = clothing_impact
    
    # Impact by accessories 2020 - 0.215kg/USD
    accessories_activity_id = "consumer_goods-type_clothing_clothing_accessories_stores"
    if len(accessories) == 0:
      accessories_spend = "No info given"
      accessories_impact = "Need more information to calculate"
      accessories_add = 0
    else:
      accessories_spend = int(accessories)
      accessories_emissions = impact_by_money(accessories_activity_id, region, accessories_spend)
      accessories_impact = accessories_emissions['Carbon_emissions']
      accessories_add = accessories_impact

    # Impact by electronics 2020 - 1.083kg/USD
    # electronics_activity_id = "electrical_equipment-type_small_electrical_appliances"
    # if electronics is None:
    #   electronics_spend = "No info given"
    #   electronics_impact = "Need more information to calculate"
      
    # else:
    #   electronics_spend = int(electronics)
    #   electronics_emissions = impact_by_money(electronics_activity_id, region, electronics_spend)
    #   electronics_impact = electronics_emissions['Carbon_emissions']
      

    # Impact by appliances (cooking) 2020 - 0.524kg/USD
    appliances_activity_id = "electrical_equipment-type_home_cooking_appliances"
    if len(appliances) == 0: 
      appliances_spend = "No info given"
      appliances_impact = "Need more information to calculate"
      appliances_add = 0 
    else:
      appliances_spend = float(appliances)
      appliances_emissions = impact_by_money(appliances_activity_id, region, appliances_spend)
      appliances_impact = appliances_emissions['Carbon_emissions']
      appliances_add = appliances_impact

    # Impact by restaurants 2020 - 0.261kg/USD
    restaurants_activity_id = "consumer_services-type_full_service_restaurants"
    if len(restaurants) == 0:
      restaurants_spend = "No info given"
      restaurants_impact = "Need more information to calculate"
      restaurants_add = 0 
    else:
      restaurants_spend = (float(restaurants) * 12)
      restaurants_emissions= impact_by_money(restaurants_activity_id, region, restaurants_spend)
      restaurants_impact = restaurants_emissions['Carbon_emissions']
      restaurants_add = restaurants_impact

    # Calculate total and update database
    total_consumption_footprint = co2(beef_impact + pork_impact + chicken_impact + restaurants_add + accessories_add + clothing_add + hotel_add + appliances_add)
    update_consumption_footprint = db.execute("INSERT INTO consumption_footprint (user_id, beef_consumption, beef_impact, pork_consumption, pork_impact, chicken_consumption, chicken_impact, dietary_attitude, new_clothes, new_clothes_impact, restaurants, restaurants_impact, accessories, accessories_impact, hotels, hotels_impact, appliances, appliances_impact, consumption_footprint_total) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", session.get("user_id"), beef_frequency, beef_impact, pork_frequency, pork_impact, chicken_frequency, chicken_impact, flexitarian, clothing_spend, clothing_impact, restaurants_spend, restaurants_impact, accessories_spend, accessories_impact, hotels, hotels_impact, appliances_spend, appliances_impact, total_consumption_footprint)
    return redirect("/results")
  else: 
    print("I know this is confusing but we're here")
    return render_template("/calculatorconsumption.html")

@app.route("/iconcolor", methods=["GET", "POST"])
@login_required
def iconcolor():
  """Allows user to change colors"""
  if request.method == "POST":
    animal = "horse"
    color = "fade"
    display_icon = customicon(animal, color)
    print("We're in post in icon color")
    icon = request.form.get("value")
    print("Icon: ", icon)
    if "pepper" in request.form:
      print("Finally!")
    elif request.form.get("honey") == "honey":
      print("Oh sugar sugar")
    return render_template("/iconcolor.html", displayicon=display_icon)
  else: 
    print("Hello get")
    return render_template("/iconcolor.html")

@app.route("/leaderboardicon", methods=["GET", "POST"])
@login_required
def leaderboardicon():
  """Update Leadearboard and user icons"""
  if request.method == "POST":
    if "pepper" in request.form:
      print("It's pepper")
    else:
      print("why doesn't this work?")
    icon = request.form.get("name")
    print("name of icon is: ", icon)
    print("We're here in post")
    return render_template("leaderboardicon.html")
  else:
    print("We're here in get")
    return render_template("leaderboardicon.html")

# Calculator page for consumption
@app.route("/calculatorconsumptionupdate", methods=["GET", "POST"])
@login_required
def calculatorconsumptionupdate():
  """Quiz user can update certain fields of their carbon score if they didn't do that already"""
  if request.method == "POST":
    new_clothes = request.form.get("new_clothes")
    restaurants = request.form.get("restaurants")
    accessories = request.form.get("accessories")
    appliances = request.form.get("appliances")
    hotels = request.form.get("hotels")
    region = "US"
    
    # Hotel impact at 16.1kg (default 2022) per night 
    check_hotels = db.execute("SELECT hotels, hotels_impact FROM consumption_footprint WHERE user_id=?", session.get("user_id"))
    hotel_activity_id = "accommodation_type_hotel_stay"
    for answer in check_hotels:
      db_hotels_impact = answer['hotels_impact']
      db_hotels_spend = answer['hotels']
    if db_hotels_impact == "Need more information to calculate":
      if len(hotels) == 0: 
        hotels = "No info given"
        hotel_impact = "Need more information to calculate"
        hotel_add = 0
      else:
        hotel_number = int(hotels)
        hotel_emissions = impact_by_number(hotel_activity_id, hotel_number, region)
        hotel_impact = hotel_emissions['Carbon_emissions']
        hotel_add = hotel_impact
        hotel_impact_formatted = co2(hotel_impact)
    else:
      hotel_add = 0
      hotels = db_hotels_spend
      hotel_impact = db_hotels_impact

    # Impact by clothes 2020 - 1.947kg/usd 
    check_clothes = db.execute("SELECT new_clothes, new_clothes_impact FROM consumption_footprint WHERE user_id=?", session.get("user_id"))
    clothing_activity_id = "consumer_goods-type_clothing"
    for answer in check_clothes:
      db_clothes_impact = answer['new_clothes_impact']
      db_clothes_spend = answer['new_clothes']
    if db_clothes_impact == "Need more information to calculate":
      if len(new_clothes) == 0:
        clothing_spend = "No info given"
        clothing_impact = "Need more information to calculate"
        clothing_add = 0
      else:
        clothing_spend = float(new_clothes)
        clothing_emissions = impact_by_money(clothing_activity_id, region, clothing_spend)
        clothing_impact = clothing_emissions['Carbon_emissions']
        clothing_add = clothing_impact
        clothing_impact_formatted = co2(clothing_impact)
    else:
      clothing_add = 0
      clothing_spend = db_clothes_spend
      clothing_impact = db_clothes_impact

    # Impact by accessories 2020 - 0.215kg/USD
    check_accessories = db.execute("SELECT accessories, accessories_impact FROM consumption_footprint WHERE user_id=?", session.get("user_id"))
    accessories_activity_id = "consumer_goods-type_clothing_clothing_accessories_stores"
    for answer in check_accessories:
      db_accessories_spend = answer['accessories']
      db_accessories_impact = answer['accessories_impact']
    if db_accessories_impact == "Need more information to calculate":
      if len(accessories) == 0:
        accessories_spend = "No info given"
        accessories_impact = "Need more information to calculate"
        accessories_add = 0
      else:
        accessories_spend = float(accessories)
        accessories_emissions = impact_by_money(accessories_activity_id, region, accessories_spend)
        accessories_impact = accessories_emissions['Carbon_emissions']
        accessories_add = accessories_impact
        accessories_impact_formatted = co2(accessories_impact)
    else:
      accessories_add = 0
      accessories_spend = db_accessories_spend
      accessories_impact = db_accessories_impact

    # Impact by appliances (cooking) 2020 - 0.524kg/USD
    check_appliances = db.execute("SELECT appliances, appliances_impact FROM consumption_footprint WHERE user_id=?", session.get("user_id"))
    appliances_activity_id = "electrical_equipment-type_home_cooking_appliances"
    for answer in check_appliances:
      db_appliances_spend = answer['appliances']
      db_appliances_impact = answer['appliances_impact']
    if db_appliances_impact == "Need more information to calculate":
      if len(appliances) == 0: 
        appliances_spend = "No info given"
        appliances_impact = "Need more information to calculate"
        appliances_add = 0
      else:
        appliances_spend = float(appliances)
        appliances_emissions = impact_by_money(appliances_activity_id, region, appliances_spend)
        appliances_impact = appliances_emissions['Carbon_emissions']
        appliances_add = appliances_impact
        appliances_impact_formatted = co2(appliances_impact)
    else: 
      appliances_add = 0
      appliances_spend = db_appliances_spend
      appliances_impact = db_appliances_impact

    # Impact by restaurants 2020 - 0.261kg/USD
    check_restaurants = db.execute("SELECT restaurants, restaurants_impact FROM consumption_footprint WHERE user_id=?", session.get("user_id"))
    restaurants_activity_id = "consumer_services-type_full_service_restaurants"
    for answer in check_restaurants:
      db_restaurants_impact = answer['restaurants_impact']
      db_restaurants_spend = answer['restaurants']
    if db_restaurants_impact == "Need more information to calculate":
      if len(restaurants) == 0:
        restaurants_spend = "No info given"
        restaurants_impact = "Need more information to calculate"
        restaurants_add = 0
      else:
        restaurants_spend = (float(restaurants) * 12)
        restaurants_emissions= impact_by_money(restaurants_activity_id, region, restaurants_spend)
        restaurants_impact = restaurants_emissions['Carbon_emissions']
        restaurants_add = restaurants_impact
        restaurants_impact_formatted = co2(restaurants_impact)
    else:
      restaurants_add = 0
      restaurants_spend = db_restaurants_spend
      restaurants_impact = db_restaurants_impact

    # Calculate total and update database
    get_current_total = db.execute("SELECT consumption_footprint_total FROM consumption_footprint WHERE user_id=?", session.get("user_id"))
    for answer in get_current_total:
      # Convert back from tons to kgs
      if "tons of cO2 per year" in get_current_total:
        current = float((answer['consumption_footprint_total']).replace("tons of cO2 per year", "")) * 1000
      elif "ton of cO2 per year" in get_current_total:
        current = float((answer['consumption_footprint_total']).replace("ton of cO2 per year", "")) * 1000
    consumption_sum = (hotel_add + clothing_add + accessories_add + appliances_add + restaurants_add)
    total_consumption_footprint = current + hotel_add + clothing_add + accessories_add + restaurants_add + appliances_add
    total_consumption_formatted = co2(total_consumption_footprint)
    update_consumption_footprint = db.execute("UPDATE consumption_footprint SET new_clothes=?, new_clothes_impact=?, restaurants=?, restaurants_impact=?, accessories=?, accessories_impact=?, hotels=?, hotels_impact=?, appliances=?, appliances_impact=?, consumption_footprint_total=? WHERE user_id=?", clothing_spend, clothing_impact, restaurants_spend, restaurants_impact, accessories_spend, accessories_impact, hotels, hotel_impact, appliances_spend, appliances_impact, total_consumption_formatted, session.get("user_id"))
    show_update = db.execute("SELECT * FROM consumption_footprint WHERE user_id=?", session.get("user_id"))
    flash("Results are ready")
    return redirect("/results")
  else: 
    print("What on earth is happening here? ")
    return render_template("/calculatorconsumptionupdate.html")

@app.route("/changename", methods=["GET", "POST"])
@login_required
def changename():
  """Allows user to change their leaderbaord name"""
  randomname = random_leaderboardname()
  
  # Handle POST request
  if request.method == "POST":

    # Check to see if user has entered a leaderboard name
    new_leaderboard_name = request.form.get("leaderboardname")
    if new_leaderboard_name is None:
      return render_template("/changename.html", randomname=randomname)

    # Check that field isn't blank
    elif len(new_leaderboard_name) == 0:
      flash("Please pick a leaderboard name")
      return render_template("/changename.html", randomname=randomname)

    # Check that leaderboard name is unique 
    checkdb = db.execute("SELECT * FROM users WHERE leaderboardname=?", new_leaderboard_name)
    if len(checkdb) != 0:
      flash("It looks like that names been taken, please try again")

    # Update leaderboard name in db and return to accoutns page
    else:
        flash("Update successful")
        updateleaderboardname = db.execute("UPDATE users SET leaderboardname=? WHERE id=?", new_leaderboard_name, session.get("user_id"))
        return redirect("/account")
  
  # Handle GET request 
  else:
    print("We're in get")
    randomname = random_leaderboardname()

    if new_leaderboard_name is None:
       flash("Enter your new name into the form below")
       randomname = random_leaderboardname()
    return render_template("/changename.html", randomname=randomname)
  
  return render_template("/changename.html", randomname=randomname)

@app.route("/changepassword", methods=["GET", "POST"])
@login_required
def changepassword():
  """Allow users to change their password"""

  # Handle Post request
  if request.method == "POST":
    print("We're here in post")
    
    # Get password and confirmation from form
    newpassword = request.form.get("password")
    confirmpassword = request.form.get("confirmpassword")

    # Check password and confirmation aren't blank 
    if len(newpassword) == 0:
      return apology("No password")
    elif len(confirmpassword) == 0:
      return apology("No confirmation")

    # Check password meets minimum requirements
    elif len(newpassword) < 8:
      return apology("Password is less than 8 char")
    
    # Check password and confirmation match
    elif newpassword != confirmpassword:
      return apology("Passwords dn't match")
    else:
      
      # Generate a hash of the temp password and add to DB
      new_hash = generate_password_hash(newpassword, method="pbkdf2:sha256", salt_length=8) 
      update_hash = db.execute("UPDATE users SET hash=? WHERE id=?", new_hash, session.get("user_id"))

      flash("You password has been updated")
    return redirect("/account")

  else:
    return render_template("/changepassword.html")
      

# Challenges page
@app.route("/challenges", methods=["GET", "POST"])
@login_required
def challenges():
  """Allows the user to enroll in challenges that will promote a lower carbon footprint"""
  return render_template("/challenges.html")

# Contact page
@app.route("/contact", methods=["GET", "POST"])
def contact():
  """Allows the user to submit a request or feedback"""
  if request.method == "POST":
    visitor_name = request.form.get("name")
    vistor_email = request.form.get("email")
    visitor_message = request.form.get("message")
    print("Visitor's name is: ", visitor_name)
    print("Vistor's email is: ", vistor_email)
    print("Vistor's message is: ", visitor_message)
    # Use sendgrid to send an email with the temporary password
    # https://pypi.org/project/Flask-Mail-SendGrid/
    message = Mail(
      from_email='beelineprograms@gmail.com',
      to_emails='beelineprograms@gmail.com',
      subject='Carbon Tracker Password Reset',
      html_content=('You received a message in the contact form: Name: {} Email: {} Message: {} ...Ends.'.format(visitor_name, vistor_email, visitor_message)))
    try:
      sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
      response = sg.send(message)
      print(response.status_code)
      print(response.body)
      print(response.headers)
    except Exception as e:
      message = "oops"
      print(e)
    return render_template("/contact.html")
  else: 
    flash("Oopsie, it happens")
    return render_template("/contact.html")

# Footprint page
@app.route("/footprint", methods=["GET", "POST"])
@login_required
def footprint():
  """Shows user their current footprint and which areas are impacting their score the most"""

  return render_template("/footprint.html")

# History page
@app.route("/history", methods=["GET", "POST"])
@login_required
def route():
  """User can view all of their history on the app"""
  return render_template("/history.html")

# Main home page
@app.route("/", methods=["GET"])
def home():
  """Information about the web app and what it does"""
  return render_template("home.html")

# Page user sees after they return
@app.route("/homeuser", methods=["GET", "POST"])
@login_required
def homeuser():
  """Displays information for returning user"""
  return render_template("homeuser.html")

# Leaderboard page
@app.route("/leaderboard", methods=["GET", "POST"])
@login_required
def leaderboard():
  """Shows user how their consumption and actions rank compared to other users"""
  return render_template("/leaderboard.html")

# Login page adapted from PSET 9 finance distribution code
@app.route("/login", methods=["GET", "POST"])
def login():
  """Logs user in if they have registered"""
  
  # Forgets user_id
  session.clear()

  # Handle POST request
  if request.method == "POST":

    # Get user's email 
    useremail = request.form.get("email")
    # Get user's password
    password = request.form.get("password")
    print(f"Password: ", password)

    # Check for email render apology
    if not request.form.get("email"):
      return apology("Please enter your email", 403)

    # Check for password if no password render apology
    elif not request.form.get("password"):
      return apology("Please enter your password", 403)
    
    email_in_db = db.execute("SELECT * FROM users WHERE email=?", request.form.get("email"))
    if len(email_in_db) == 0:
      return apology("No account is associated with that email")
    
    for detail in email_in_db:
      emailadd = detail['email']
      print("emailadd", emailadd)
    len_email = len(email_in_db)
    print("Lenth email in db", len_email)
    password_hash = db.execute("SELECT * FROM users WHERE email=?", request.form.get("email"))
    password_check = check_password_hash(password_hash[0]["hash"], password)
    print(f"Password check: ", password_check)
    
    # Check email exists and password is correct
    print("Email in database: ", email_in_db)
    if useremail != emailadd:
      return apology("No account for that email")
    
    elif len(email_in_db) != 1 or not check_password_hash(email_in_db[0]["hash"], password):
      return apology("Oops! Either your username or password are incorrect", 403)

    # Remember which user has logged in
    session["user_id"] = email_in_db[0]["id"]
    return render_template("/homeuser.html")
  
  else:
    return render_template("/login.html")

# Logout page Adapted from Pset 9 Finance
@app.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
  """Logs user out"""
  session.clear()
  return render_template("/login.html")

# Registration page
@app.route("/register", methods=["GET", "POST"])
def register():
  """Allows user to register so they can login"""
  random_leaderboard = random_leaderboardname()

  # Handle post request
  if request.method == "POST":
    # Get username, first name, password, confirmation and leaderboard name
    name = request.form.get("name")
    password = request.form.get("password")
    confirmation = request.form.get("confirmpassword")
    leaderboardname = request.form.get("leaderboardname")
    email = request.form.get("email")
    goback = request.form.get("goback")

    if goback is not None:
      return render_template("/register.html", randomname=random_leaderboard) 
    
    # Check name isn't blank
    if name is None:
      return apology("Please enter your name", 403)
    
    # Check password isn't blank
    elif password is None:
      return apology("Oops! Password cannot be blank", 403)
    
    elif confirmation is None:
      return apology("Confirmation is blank")
    
    # Check password and confirmation match
    elif password != confirmation:
      return apology("Oops! Your passwords don't match", 403)
    
    elif len(password) < 8:
      return apology("Password should be at least 8 char long for your security")

    # Check leaderboard name isn't blank
    elif len(leaderboardname) == 0:
      return apology("Please choose a leaderboard name", 403)
    
    # Check leaderboard name is unique
    leaderboard_check = db.execute("SELECT * FROM users WHERE leaderboardname=?", request.form.get("leaderboardname"))
    count = db.execute("SELECT count(email) FROM users WHERE email=?", email)
    
    if len(leaderboard_check) != 0:
      flash("Oops, that leaderboard name has already been claimed. Try our random leaderboard name generator for more ideas")
      random_name = random_leaderboardname()
      leaderboard_check = db.execute("SELECT * FROM users WHERE leaderboardname=?", random_name)
      leaderboard_suggestion = ""
      print(len(leaderboard_suggestion))
      while len(leaderboard_check) !=0: 
        leaderboard_suggestion = random_leaderboardname
        print(leaderboard_suggestion)
      if leaderboard_suggestion:
        flash("Oops, that leaderboard name has already been claimed. Try our random leaderboard name generator for more ideas")
        return render_template("/register.html", randomname=leaderboard_suggestion)
      else:
        return render_template("/register.html", randomname=random_name)
    
    # Check email isn't blank an email
    elif len(email) == 0:
      return apology("Please enter your email")
    # TO DO: 
    # FIX ISSUE WITH EMAILS being the same - need to check for that email and issue apology that an account already exists 
    # BUG HERE
    elif (len(count) > 1):
      return apology("An account already exists")
    
    else:
      # TO DO: 
      # FIND OUT WHY AUTOINCREMENT DOESN'T GO FROM THE LAST USER BUT THE LAST NUMBER, AND IS THERE A WAY TO RESET IT
      # INSERT new user and store a hash of the password, update tracker_scores:
      # **** Should look at ways to make this password more secure
      hash = generate_password_hash(request.form.get("password"), method="pbkdf2:sha256", salt_length=8)
      new_user = db.execute("INSERT INTO users (name, email, leaderboardname, hash) VALUES(?, ?, ?, ?)", name, email, leaderboardname, hash)
      print("NEW USERS: ")
      find_id = db.execute("SELECT id FROM users WHERE leaderboardname=?", leaderboardname)
      print("find id: ", find_id)
      for id in find_id:
        get_id = id['id']
      print("get id: ", get_id)
      green_tariffs = "No"
      solar_panels = "No"
      set_tracker_scores_db = db.execute("INSERT INTO trackers (user_id, added_friends, planted_trees, helped_community, vintage_clothing, sustainable_clothing, saved_plastic, saved_money, saved_energy, bought_local, vacationed_local, less_beef, less_chicken, less_pork, more_compost, green_tariff, solar_panels, saved_water, less_waste, more_recycling, fewer_flights, fewer_hotels, more_direct_flights, miles_walk_bike, carbon_offset, carbon_savings, total_score) VALUES(?, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, ?, ?, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)", get_id, green_tariffs, solar_panels)
      return render_template("/login.html")

  # Handle GET request 
  else:
    return render_template("/register.html", randomname=random_leaderboard)

# Reset password page
@app.route("/reset", methods=["GET", "POST"])
def reset():
  """Allows user to reset password"""
  # Following this for mail extensions https://pythonbasics.org/flask-mail/
  # https://www.youtube.com/watch?v=48Eb8JuFuUI
  
  if request.method == "POST":
    flash("Please Check Your Email, if you don't see it please check your spam folder and then add us to your address book")
    email = request.form.get("email")
    print("Person's email is ", email)
    # Check that person is in fact in db
    account_check = db.execute("SELECT * FROM users WHERE email=?", email)
    print("Account check: ", account_check)
    print(type(account_check))
    if len(account_check) == 0:
      return apology("We don't have an account with your name on it")
    
    # Handle reset password
    else:
      flash("Please check your email for a temporary password")
      # Generate random password from helpers
      temp_password = generate_temp_password()
      print("Your temporary password is", temp_password)

      # Generate a hash of the temp password and add to DB
      temp_hash = generate_password_hash(temp_password, method="pbkdf2:sha256", salt_length=8) 
      update_hash = db.execute("UPDATE users SET hash=? WHERE email=?", temp_hash, email)

      # Use sendgrid to send an email with the temporary password
      # https://pypi.org/project/Flask-Mail-SendGrid/
      message = Mail(
        from_email='beelineprograms@gmail.com',
        to_emails=email,
        subject='Carbon Tracker Password Reset',
        html_content=('Hi there, We received a request to reset your password and have generated a random temporary one: {} Please use this to login and change your password. If you did not request this please let us know and update your password as soon as possible. Thank you.'.format(temp_password)))
      try:
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        response = sg.send(message)
        print(response.status_code)
        print(response.body)
        print(response.headers)
      except Exception as e:
        message = "oops"
        print(e)
      return render_template("/login.html")
  else: 
    flash("Oopsie, it happens")
  return render_template("/reset.html")

# Results page user sees after quiz
@app.route("/results", methods=["GET", "POST"])
@login_required
def results():
  """Shows user the results from their carbon footprint quiz"""
  if request.method == "POST":
    return render_template("/results.html")
  else:
    # get user:
    user = session.get("user_id")
    # Get footprint scores from db
    db_footprint = db.execute("SELECT * FROM footprint WHERE user_id=?", session.get("user_id"))
    total_footprint_general_formatted = 0
    for score in db_footprint: 
      building = score['building']
      # TO DO: 
      # Tell user this is not part of their final score and why - create a hover question mark with more information and implement JS for this
      impact_of_construction = float(score['building_impact'])
      # TO DO: 
      # Tell user why their state matters: 
      state = score['state']
      electricity = score['electricity']
      electricity_impact = (score['electricity_impact'])
      # TO DO: 
      # Tell user why we asked for occupants 
      household_occupants = score['household_occupants']
      waste_frequency = score['waste_frequency']
      recycling = score['recycling']
      landfill_impact = co2(float(score['landfill_impact']))
      recycling_impact = co2(float(score['recycling_impact']))
      drycleaning_spend = ((float(score['drycleaning']) * 12))
      drycleaning_impact = co2(float(score['drycleaning_impact']))
      total_footprint_general = score['total_footprint_general']
    if "tons of cO2 per year" in total_footprint_general:
      individual_score = ((float(total_footprint_general.replace("tons of cO2 per year", ""))) / (int(household_occupants)))
    elif "ton of cO2 per year" in total_footprint_general:
      individual_score = ((float(total_footprint_general.replace("ton of cO2 per year", ""))) / (int(household_occupants)))
    individual_score_formatted = co2(individual_score * 1000)
    if "tons of cO2 per year" in total_footprint_general:
      total_footprint_general_formatted = co2(float(total_footprint_general.replace("tons of cO2 per year", "")) * 1000)
    elif "ton of cO2 per year" in total_footprint_general:
      total_footprint_general_formatted = co2(float(total_footprint_general.replace("ton of cO2 per year", "")) * 1000)
    impact_of_construction_formatted = co2lifetime(impact_of_construction)
    drycleaning_formatted = "{:.2f}".format(drycleaning_spend)

    # Get transport footprint scores from db
    db_transport = db.execute("SELECT * FROM transport_footprint WHERE user_id=?", user)
    for score in db_transport:
      work_situation = score['work_situation']
      commuter_days = score['commuter_days']
      commuter_distance = score['commuter_distance']
      
      # TO DO:
      # Translate all the transport modes back into normal language maybe a key of tables in db
      transport_mode = score['transport_mode']
      transport_cost = score['transport_cost']
      impact_of_commute = co2(float(score['commuter_impact']))
      short_haul_flights = score['short_haul']
      short_haul_flights_impact = co2(float(score['short_haul_impact']))
      medium_haul_flights = score['medium_haul']
      medium_haul_flights_impact = co2(float(score['medium_haul_impact']))
      long_haul_flights = score['long_haul']
      long_haul_flights_impact = co2(float(score['long_haul_impact']))
      total_footprint_transport = score['transport_footprint_total']
      if "tons of cO2 per year" in total_footprint_transport:
        total_footprint_transport_formatted = co2(float(total_footprint_transport.replace("tons of cO2 per year", "")) * 1000)
      else:
        total_footprint_transport_formatted = co2(float(total_footprint_transport.replace("ton of cO2 per year", "")) * 1000)
    if int(commuter_days) > 1:
      commuter_days = str(commuter_days) + "days of the week"
    else:
      commuter_days = str(commuter_days) + "day of the week"

    # Get consumption footprint scores from db 
    db_consumption = db.execute("SELECT * FROM consumption_footprint WHERE user_id=?", user)
    for score in db_consumption:
      
      beef_consumption = int(score['beef_consumption'])
      if beef_consumption > 1:
        beef_consumption = str(beef_consumption) + " times"
      else:
        beef_consumption = str(beef_consumption) + " time"
      beef_impact = co2(float(score['beef_impact']))
      beef_add = float(score['beef_impact'])
      
      pork_consumption = int(score['pork_consumption'])
      if pork_consumption > 1:
        pork_consumption = str(pork_consumption) + " times"
      else:
        pork_consumption = str(pork_consumption) + " times"
      pork_impact = co2(float(score['pork_impact']))
      pork_add = float(score['pork_impact'])

      chicken_consumption = int(score['chicken_consumption'])
      if chicken_consumption > 1:
        chicken_consumption = str(chicken_consumption) + " times"
      else:
        chicken_consumption= str(chicken_consumption) + "time"
      chicken_impact = co2(float(score['chicken_impact']))
      chicken_add = float(score['chicken_impact'])

      # TO DO:
      # Tell user why we asked this 
      willingness_to_adjust_diet = (score['dietary_attitude']).replace("_", " ")
      new_clothing_spend = score['new_clothes']
      
      # Manage empty fields in clothing
      if new_clothing_spend == "No info given":
        new_clothing_spend = score['new_clothes']
        new_clothing_impact = "Unknown, we need more information from you to calculate this."
        new_clothing_add = 0
      else:
        new_clothing_spend = formatfloat(float(score['new_clothes']))
        new_clothing_impact = co2(float(score['new_clothes_impact']))
        new_clothing_add = new_clothing_impact

      # Manage empty fields in restaurants:
      restaurants_spend = score['restaurants']
      if restaurants_spend == "No info given":
        restaurants_spend = "No info given"
        restaurants_impact = "Unknown, we need more information from you to calculate this."
        restaurants_add = 0
      else:
        restaurants_spend = formatfloat(float(restaurants_spend))
        restaruants_impact = co2(float(score['restaurants_impact']))
        restaurants_add = restaurants_impact

      # Manage empty fields in accessories 
      accessories_spend = score['accessories']
      if accessories_spend == "No info given":
        accessories_spend = "No info given"
        accessories_impact = "Unknown, we need more information from you to calculate this."
        accessories_add = 0
      else:
        accessories_spend = format(float(accessories_spend))
        accessories_impact = co2(float(score['accessories_impact']))
        accessories_add = accessories_impact

      # Manage empty fields in appliances 
      appliances_spend = score['appliances']
      if appliances_spend == "No info given":
        appliances_spend = "No info given"
        appliances_impact = "Unknown, we need more information from you to calculate this."
        appliances_add = 0
      else:
        appliances_spend = format(float(appliances_spend))
        appliances_impact = co2(float(score['appliances_impact']))
        appliances_add = appliances_impact
      
      # Manage empty fields in hotels
      hotels = score['hotels']
      if hotels == "No info given":
        hotels = "No info given"
        hotels_impact = "Unknown, we need more information from you to calculate this."
        hotels_add = 0
      else:
        hotels = format(float(hotels))
        hotels_impact = co2(float(score['hotels_impact']))
        hotels_add = 0

      total_footprint_consumption = hotels_add + appliances_add + accessories_add + restaurants_add + new_clothing_add + beef_add + chicken_add + pork_add
      date_completed = score['datetime']
    # Format General Footprint for sum
    sum_total_footprint_general = total_footprint_general

    if "tons of cO2 per year" in total_footprint_general:
      sum_total_footprint_general = float(total_footprint_general.replace("tons of cO2 per year", "")) * 1000
    elif "ton of cO2 per year" in total_footprint_general:
      sum_total_footprint_general = float(total_footprint_general.replace("ton of cO2 per year", "")) * 1000
    else:
      print("Something else is going on")

    # Format Transport Footprint for sum
    sum_total_footprint_transport = total_footprint_transport
    if "tons of cO2 per year" in total_footprint_transport:
      sum_total_footprint_transport = float(total_footprint_transport.replace("tons of cO2 per year", "")) * 1000
    elif "ton of cO2 per year" in total_footprint_transport:
      sum_total_footprint_transport = float(total_footprint_transport.replace("ton of cO2 per year", "")) * 1000
    else:
      print("Something else is going on")

    # Format Consumption Footprint for sum
    sum_total_footprint_consumption = float(total_footprint_consumption)

    total = sum_total_footprint_general + sum_total_footprint_transport + sum_total_footprint_consumption
    grand_total = co2(total)

    total_footprint_consumption = co2(float(total_footprint_consumption))
    # TO DO:
    # Get stats for averagage american to show how they compare 
    # Get stats from how much this translates to in forests
    # Create table in for leaderboard that stores benchmark scores for users
    # Update total score into leaderboard score
    return render_template("/results.html", total=grand_total, datetime=date_completed, household=total_footprint_general, transport=total_footprint_transport, consumption=total_footprint_consumption, building=building, buildingimpact=impact_of_construction_formatted, state=state, electricity=electricity, electrictyimpact=electricity_impact, wastefrequency=waste_frequency, landfill=landfill_impact, recycling=recycling, recyclingimpact=recycling_impact, drycleaning=drycleaning_formatted, drycleaningimpact=drycleaning_impact, totalfootprint=total_footprint_general_formatted, individualfootprint=individual_score_formatted, worksituation=work_situation, commuterdays=commuter_days, commuterdistance=commuter_distance, transportmode=transport_mode, transportcost=transport_cost, commuterimpact=impact_of_commute, shorthaul=short_haul_flights, shorthaulimpact=short_haul_flights_impact, mediumhaul=medium_haul_flights, mediumhaulimpact=medium_haul_flights_impact, longhaul=long_haul_flights, longhaulimpact=long_haul_flights_impact, totaltransportfootprint=total_footprint_transport_formatted, beef=beef_consumption, beefimpact=beef_impact, pork=pork_consumption, porkimpact=pork_impact, chicken=chicken_consumption, chickenimpact=chicken_impact, willingness=willingness_to_adjust_diet, newclothing=new_clothing_spend, newclothingimpact=new_clothing_impact, restaurants=restaurants_spend, restaurantsimpact=restaurants_impact, accesories=accessories_spend, accessories=accessories_spend, accessoriesimpact=accessories_impact, appliances=appliances_spend, appliancesimpact=appliances_impact, hotels=hotels, hotelsimpact=hotels_impact, totalconsumptionfootprint=total_footprint_consumption)

# Tracker page to track carbon footprint
@app.route("/trackercommunity", methods=["GET", "POST"])
@login_required
def trackercommunity():
  """Allows user to track their progress"""
  if request.method == "POST":
    print("We're in post")
    # Get relevant info from DB
    get_db = db.execute("SELECT added_friends, planted_trees, helped_community, total_score FROM trackers WHERE user_id=?", session.get("user_id"))
    print("GET DB: ", get_db)
    for info in get_db:
      added_friends = info['added_friends']
      planted_trees = info['planted_trees']
      helped_community = info['helped_community']
      total_score = info['total_score']
    print("FROM DB added friends: ", added_friends)
    print("FROM DB planted trees: ", planted_trees)
    print("FROM DB helped community: ", helped_community)
    print("FROM DB total score: ", total_score)

    # Get values from forms:
    friends = request.form.get("added_friend")
    trees = request.form.get("planted_trees")
    community_garden = request.form.get("community_garden")
    mentor = request.form.get("mentor")
    
    # Manage empty fields and tally score 
    if friends is None:
      print("They didn't bring any friends")
      friends_add = 0
    else:
      print("They brought friends: ", friends)
      friends_add = int(friends)
    print("Friends added: ", friends_add)
    if trees is None:
      print("They didn't plant any trees")
      trees_add = 0
    else:
      print("They planted trees: ", trees)
      trees_add = int(trees)
    if community_garden is None:
      print("They didn't help at their community garden")
      community_garden_add = 0
    else: 
      print("They helped at their community garden:", community_garden)
      community_garden_add = int(community_garden)
    if mentor is None: 
      print("They didn't mentor")
      mentor_add = 0
    else: 
      print("They mentored and did: ", mentor)
      mentor_add = int(mentor)
    
    # Set new totals:
    friends_total = int(added_friends) + friends_add
    trees_total = int(planted_trees) + trees_add
    community_total = int(helped_community) + community_garden_add + mentor_add
    new_total_score = int(total_score) + friends_total + trees_total + community_total

    print("Friends total: ", friends_total)
    print("Trees total: ", trees_total)
    print("Community total: ", community_total)
    print("New grandtotal: ", new_total_score)

    # Update DB: 
    update_db = db.execute("UPDATE trackers SET added_friends=?, planted_trees=?, helped_community=?, total_score=? WHERE user_id=?", friends_total, trees_total, community_total, new_total_score, session.get("user_id"))
    updated_db = db.execute("SELECT * FROM trackers WHERE user_id=?", session.get("user_id"))
    print("Updated DB: ", updated_db)
    return render_template("/trackercommunity.html")
  else:
    print("We're here in get")
  return render_template("/trackercommunity.html")

@app.route("/trackerelectricity", methods=["GET", "POST"])
@login_required
def trackerelectricity():
  """Allows user to track their progress"""
  if request.method == "POST":
    print("We're in post")
    
    # Get benchmark values from db: 
    get_db_electricity = db.execute("SELECT state, electricity, electricity_impact, waste_frequency, recycling FROM footprint WHERE user_id=?", session.get("user_id"))
    for info in get_db_electricity:
      energy_usage_db = float(info['electricity'])
      waste_frequency = int(info['waste_frequency'])
      recycling_amount = float(info['recycling'])
      state = info['state']
      previous_emissions = float(info['electricity_impact']) / 12

    # Get tracker info from db:
    get_db = db.execute("SELECT saved_plastic, saved_money, saved_energy, more_compost, green_tariff, solar_panels, saved_water, less_waste, more_recycling, carbon_savings, total_score FROM trackers WHERE user_id=?", session.get("user_id"))
    for info in get_db: 
      saved_plastic = info['saved_plastic']
      monetary_savings = info['saved_money']
      energy_savings = info['saved_energy']
      compost_total = info['more_compost']
      green_tariff_status = info['green_tariff']
      solar_panels_status = info['solar_panels']
      water_savings = info['saved_water']
      less_waste_total = info['less_waste']
      more_recycling_total = info['more_recycling']
      carbon_savings = info['carbon_savings'] 
      db_total_score = info['total_score']
    
    # Get necessary values for looking up electricity
    electricity_activity_id = "electricity-energy_source_grid_mix"
    region = state

    # Get values from form
    reduced_utility_bill = request.form.get("reduced_utility_bill")
    composting = request.form.get("composting")
    green_tariff = request.form.get("green_tariff")
    solar_panels = request.form.get("solar_panels")
    short_shower = request.form.get("short_shower")
    saved_electricity = request.form.get("saved_electricity")
    less_plastic = request.form.get("less_plastic")
    less_waste = request.form.get("less_waste")
    more_recycling = request.form.get("more_recycling")
    
    # Handle empty fields and calculate adds
    # Utilitiy bill
    if reduced_utility_bill is None:
      energy_savings_add = 0
      carbon_savings_utilities = 0
    else:
      reduced_utility_bill = float(reduced_utility_bill)
      if reduced_utility_bill > energy_usage_db:
        flash("You used more electricity than usual this month")
        energy_savings_add = 0
        carbon_savings_utilities = 0
      elif reduced_utility_bill == energy_usage_db:
        flash("You used the same amount of electricity as usual")
        energy_savings_add = 0
        carbon_savings_utilities = 0
      else:
        # HACK: 
        # Points should be proportional to savings but in the magnitude of 100 so the score doesn't inflate too quickly
        energy_savings_add = (energy_usage_db - reduced_utility_bill) / 100
        electricity_lookup = impact_by_energy(electricity_activity_id, region, reduced_utility_bill)
        electricity_emissions = float(electricity_lookup['Carbon_emissions'])
        carbon_savings_utilities = previous_emissions - electricity_emissions
    
    # Composting
    if composting is None:
      composting_add = 0
    else:
      composting_add = int(composting)
    
    # Green tariff
    if green_tariff is None: 
      if green_tariff_status == "Yes":
        green_tariff_status = "Yes"
        points_for_going_green = 0
      else:
        green_tariff_status = "No"
        points_for_going_green = 0
    else:
      # If the user has entered something their green tariff status should be updated to yes in db
      green_tariff_status = "Yes"
      points_for_going_green = 10
    
    # Solar panels
    if solar_panels is None:
      if solar_panels_status == "Yes":
        solar_panels_status = "Yes"
        points_for_solar_panels = 0
      else:
        solar_panels_status = "No"
        points_for_solar_panels = 0
    else: 
      # If the user has entered something their solar panels status should be updated to yes in db
      solar_panels_status = "Yes"
      points_for_solar_panels = 20
    
    
    # Short shower
    if short_shower is None:
      water_savings_add = 0
    else: 
      # HACK:
      # Average shower uses 2.5 Gallons of water per minute https://green.harvard.edu/tools-resources/green-tip/4-ways-measure-5-minute-shower#:~:text=Did%20you%20know%20the%20average,water%20for%20the%20average%20shower!
      water_savings_add = float(short_shower) * 2.5
    
    # Electricity savings
    if saved_electricity is None: 
      energy_savings_add_bulbs = 0
      money_savings_add_bulbs = 0
      added_points_bulbs = 0
      carbon_savings_bulbs = 0
    else:
      # HACK:
      # Save (3.05 - 1.34) in $ switching https://blog.constellation.com/2016/03/25/led-vs-cfl-bulbs/
      # LED lights are 75% more efficient https://www.energy.gov/energysaver/led-lighting
      # Incandescent bulbs use 60 watts per hour vs LED which uses 7 - 10 https://www.familyhandyman.com/list/how-much-electricity-items-in-your-house-use/
      saved_electricity = float(saved_electricity)
      money_savings_add_bulbs = float((3.05 - 1.34) * (saved_electricity))
      
      # Estimating savings of 50 watts per hour from switching to LED the equivalent in kWh
      # kWh=(watts * hrs) / 1,000 https://justenergy.com/blog/kilowatts-and-calculations/#:~:text=Here's%20the%20Formula%20for%20Calculating,watts%20%C3%97%20hrs)%20%C3%B7%201%2C000
      energy_savings_add_bulbs = (50 * saved_electricity) / 1000
      carbon_savings_lookup = impact_by_energy(electricity_activity_id, region, energy_savings_add)
      carbon_savings_bulbs = (float(carbon_savings_lookup['Carbon_emissions']))
     
     # Offered the user double points for this - add to score
      added_points_bulbs = 2
    
    # Less plastic
    if less_plastic is None:
      less_plastic_add = 0
    else:
      less_plastic_add = float(less_plastic)
    
    # less waste
    if less_waste is None: 
      less_waste_add = 0
    else: 
      less_waste_add = float(less_waste)
    
    # more recycling 
    if more_recycling is None:
      more_recycling_add = 0
    else: 
      more_recycling_add = float(more_recycling) / 100
    
    # Print totals to tally 
    energy_savings_total = float(energy_savings) + energy_savings_add + energy_savings_add_bulbs
    carbon_savings_total = formatfloat(float(carbon_savings) + carbon_savings_utilities + carbon_savings_bulbs)
    money_savings_total = formatfloat(float(monetary_savings) + money_savings_add_bulbs)
    compost_new_total = int(float(compost_total) + composting_add)
    green_tariff_status_end = green_tariff_status
    solar_panels_status_end = solar_panels_status
    water_savings_total = float(water_savings) + water_savings_add
    plastic_savings = int(float(saved_plastic) + less_plastic_add)
    total_waste_savings = float(less_waste_total) + float(less_waste_add)
    total_recycling_score = float(more_recycling_total) + more_recycling_add
    starting_score = float(db_total_score)
    stuff_to_add = float(formatfloat(energy_savings_add + energy_savings_add_bulbs + carbon_savings_bulbs + carbon_savings_utilities + composting_add + money_savings_add_bulbs + points_for_going_green + points_for_solar_panels + water_savings_add + less_plastic_add + less_waste_add + more_recycling_add))
    new_added_score =  float(formatfloat(energy_savings_add + energy_savings_add_bulbs + carbon_savings_utilities + carbon_savings_bulbs + money_savings_add_bulbs + composting_add + points_for_going_green + points_for_solar_panels + water_savings_add + less_plastic_add + less_waste_add + more_recycling_add))
    new_total_score = float(db_total_score) + new_added_score
   
    # Update db
    updatedb = db.execute("UPDATE trackers SET saved_plastic=?, saved_money=?, saved_energy=?, more_compost=?, green_tariff=?, solar_panels=?, saved_water=?, less_waste=?, more_recycling=?, carbon_savings=?, total_score=? WHERE user_id=?", plastic_savings, money_savings_total, energy_savings_total, compost_new_total, green_tariff_status_end, solar_panels_status_end, water_savings_total, total_waste_savings, total_recycling_score, carbon_savings_total, new_total_score, session.get("user_id"))
    return render_template("/trackerelectricity.html", garbage=waste_frequency, recycling=recycling_amount, kwh=energy_usage_db)
  else:
    print("We're here in get")
    # TO DO: 
    # Display values from bench mark here 
    get_db_electricity = db.execute("SELECT electricity, waste_frequency, recycling FROM footprint WHERE user_id=?", session.get("user_id"))
    print("USER's electricity and home details in the db: ", get_db_electricity)
    for info in get_db_electricity:
      energy_usage_db = info['electricity']
      waste_frequency = info['waste_frequency']
      recycling_amount = info['recycling']
    print("Energy usage: ", energy_usage_db)
    print("Waste Frequency: ", waste_frequency)
    print("Recycling amount: ", recycling_amount)
    energy_usage = int(float(energy_usage_db))
  return render_template("/trackerelectricity.html", garbage=waste_frequency, recycling=recycling_amount, kwh=energy_usage)

@app.route("/trackershopping", methods=["GET", "POST"])
@login_required
def trackershopping():
  """Allows user to track their progress"""
  if request.method == "POST":
    print("We're in post in shopping")
    
    # Get necessary items to render the page on refresh: 
    getdrycleaning = db.execute("SELECT drycleaning, drycleaning_impact FROM footprint WHERE user_id=?", session.get("user_id"))
    for info in getdrycleaning:
      drycleaning_spend_db = info['drycleaning']
      drycleaning_impact = info['drycleaning_impact']

    spending_impact = db.execute("SELECT beef_consumption, pork_consumption, chicken_consumption, dietary_attitude, restaurants, accessories, hotels FROM consumption_footprint WHERE user_id=?", session.get("user_id"))
    for item in spending_impact:
      beef_consumption = item['beef_consumption']
      pork_consumption = item['pork_consumption']
      chicken_consumption = item['chicken_consumption']
      dietary_attitude = item['dietary_attitude']
      restaurants = item['restaurants']
      accessories = item['accessories']

    if restaurants == "No info given":
      restaurants_spend = "You didn't mention when you started how much you were spending on restaurants. You can update that at any point. How much did you spend this month?"
    else:
      restaurants_spend = "When you got started you said you were spending $" + restaurants + "each month. How much did you spend this month?"
      
    if accessories == "No info given":
      accessories_spend = "You didn't mention when you started how much you were spending on accessories. You can update that at any point. How much did you spend this month?"
    else:
      accessories_spend = "When you got started you said you were spending $" + accessories + "each month. How much did you spend this month?"
      
    # Get items from form 
    vintage_clothes = request.form.get("vintage_clothes")
    sustainable_clothes = request.form.get("sustainable_clothes")
    paper_bags = request.form.get("paper_bags")
    own_bags = request.form.get("own_bags")
    water_bottle = request.form.get("water_bottle")
    local_groceries = request.form.get("local_groceries")
    beef = request.form.get("beef")
    chicken = request.form.get("chicken")
    pork = request.form.get("pork")
    drycleaning_form = request.form.get("drycleaning")
    restaurants_form = request.form.get("restaurants")
    accessories_form = request.form.get("accessories")
    
    # region for calculations:
    region = "US"

    # Manage empty fields and tally up scores
    if vintage_clothes is None:
      vintage_clothes_add = 0
    else:
      vintage_clothes_add = 1
    
    if sustainable_clothes is None: 
      sustainable_clothes_add = 0
    else: 
      sustainable_clothes_add = 1

    if paper_bags is None: 
      plastic_saved_by_paper = 0
    else: 
      plastic_saved_by_paper = int(paper_bags)
    
    if own_bags is None:
      plastic_saved_by_reusable = 0
    else:
      plastic_saved_by_reusable = int(own_bags)

    if water_bottle is None:
      money_savings_plastic = 0
    else: 
      money_savings_plastic = int(water_bottle)

    if local_groceries is None:
      local_points = 0
    else: 
      # HACK:
      # Points awarded for the percentage of groceries bough locally (10%)
      local_points = float(local_groceries) / 10

    # Calculate how many fewer times each meat was consumed, and carbon savings
    if beef is None or chicken is None or pork is None:
      less_beef_add = 0
      carbon_savings_beef = 0
      less_chicken_add = 0 
      carbon_savings_chicken = 0
      less_pork_add = 0 
      carbon_savings_pork = 0
    else:
      beef = int(beef)
      beef_consumption_weekly = int(beef_consumption) 
      chicken = int(chicken)
      chicken_consumption_weekly = chicken_consumption 
      pork = int(pork)
      pork_consumption_weekly = int(pork_consumption) 
      
      # API activity id from calculator
      beef_activity_id = "consumer_goods-type_meat_products_beef"
      chicken_activity_id = "consumer_goods-type_meat_products_poultry"
      pork_activity_id = "consumer_goods-type_meat_products_pork"
      # prices from calculator 
      beef_price = 5.12 / 2
      chicken_prices = (1.87 / 2) 
      pork_prices = [1.21, 11.21, 9.64, 11.26, 8.89, 9.04, 16.22, 9.56, 8.20, 7.92, 8.83, 9.04, 8.79, 8.76, 11.25]
      sum_pork_prices = sum(pork_prices)
      average_pork_prices = sum(pork_prices) / len(pork_prices)
      if beef > beef_consumption_weekly or beef == beef_consumption_weekly:
        less_beef_add = 0
        carbon_savings_beef = 0
        if chicken > chicken_consumption_weekly or chicken == chicken_consumption_weekly:
          less_chicken_add = 0 
          carbon_savings_chicken = 0
          if pork > pork_consumption_weekly or pork == pork_consumption_weekly:
            less_pork_add = 0
            carbon_savings_pork = 0
          else:
            less_pork_add = pork_consumption_weekly - pork
            pork_spend = average_pork_prices * less_pork_add
            pork_lookup = impact_by_money(pork_activity_id, region, pork_spend)
            carbon_savings_pork = pork_lookup['Carbon_emissions']
        else:
          less_chicken_add = chicken_consumption_weekly - chicken
          chicken_spend = chicken_prices * less_chicken_add
          chicken_lookup = impact_by_money(chicken_activity_id, region, chicken_spend)
          carbon_savings_pork = chicken_lookup['Carbon_emissions']
          if pork > pork_consumption_weekly or pork == pork_consumption_weekly:
            less_pork_add = 0
            carbon_savings_pork = 0
          else:
            less_pork_add = pork_consumption_weekly - pork
            pork_spend = average_pork_prices * less_pork_add
            pork_lookup = impact_by_money(pork_activity_id, region, pork_spend)
            carbon_savings_pork = pork_lookup['Carbon_emissions']
      else:
        less_beef_add = beef_consumption_weekly - beef
        beef_spend = beef_price * less_beef_add
        beef_lookup = impact_by_money(beef_activity_id, region, beef_spend)
        carbon_savings_beef = beef_lookup['Carbon_emissions']
        if chicken > chicken_consumption_weekly or chicken == chicken_consumption_weekly:
          less_chicken_add = 0 
          carbon_savings_chicken = 0
          if pork > pork_consumption_weekly or pork == pork_consumption_weekly:
            less_pork_add = 0
            carbon_savings_pork = 0
          else:
            less_pork_add = pork_consumption_weekly - pork
            pork_spend = average_pork_prices * less_pork_add
            pork_lookup = impact_by_money(pork_activity_id, region, pork_spend)
            carbon_savings_pork = pork_lookup['Carbon_emissions']
        else:
          less_chicken_add = chicken_consumption_weekly - chicken
          chicken_spend = chicken_prices * less_chicken_add
          chicken_lookup = impact_by_money(chicken_activity_id, region, chicken_spend)
          carbon_savings_chicken = chicken_lookup['Carbon_emissions']
          if pork > pork_consumption_weekly or pork == pork_consumption_weekly:
            less_pork_add = 0
            carbon_savings_pork = 0
          else:
            less_pork_add = pork_consumption_weekly - pork
            pork_spend = average_pork_prices * less_pork_add
            pork_lookup = impact_by_money(pork_activity_id, region, pork_spend)
            carbon_savings_pork = pork_lookup['Carbon_emissions']

    if drycleaning_form is None: 
      drycleaning_savings = 0
      carbon_savings_drycleaning = 0
    else: 
      drycleaning_form = float(drycleaning_form)
      if drycleaning_form > float(drycleaning_spend_db) or drycleaning_form == float(drycleaning_spend_db):
        flash("Oops you it looks like you didn't save on drycleaning this month")
        drycleaning_savings = 0
        carbon_savings_drycleaning = 0
      else:
        drycleaning_savings = float(drycleaning_spend_db) - drycleaning_form
        # From calculator
        drycleaning_activity_id = "consumer_goods-type_dry_cleaning_laundry"
        drycleaning_lookup = impact_by_money(drycleaning_activity_id, region, drycleaning_savings)
        carbon_savings_drycleaning = drycleaning_lookup['Carbon_emissions']

    if restaurants_form is None: 
      restaurants_savings = 0
      carbon_savings_restaurants = 0
    else:
      # from calculator
      restaurants_activity_id = "consumer_services-type_full_service_restaurants"
      if restaurants == "No info given":
        restaurants = 0
        restaurants_savings = 0
        carbon_savings_restaurants = 0
      else: 
        restaurants_form = float(restaurants_form)
        restaurants = float(restaurants)
        if restaurants_form > restaurants or restaurants_form == restaurants:
          flash("Oops looks like you didn't save on restaurants this month")
          restarants_savings = 0
          carbon_savings_restaurants = 0
        else: 
          restaurants_savings = restaurants - restaurants_form
          restaurants_lookup = impact_by_money(restaurants_activity_id, region, restarants_savings)
          carbon_savings_restaurants = restaurants_lookup['Carbon_emissions']

    if accessories_form is None: 
      accessories_savings = 0
      carbon_savings_accessories = 0
    else: 
      accessories_activity_id = "consumer_goods-type_clothing_clothing_accessories_stores"
      if accessories == "No info given":
        accessories = 0
        accessories_savings = 0
        carbon_savings_accessories = 0
      else:
        accessories_form = float(accessories_form)
        accessories = float(accessories) 
        if accessories_form > accessories_spend or accessories_form == accessories_spend:
          flash("Looks like you actually spent more than usual on accessories")
          accessories_savings = 0
          carbon_savings_accessories = 0
        else: 
          accessories_savings = accessories - accessories_form
          accessories_lookup = impact_by_money(accessories_activity_id, region, accessories_savings)
          carbon_savings_accessories = accessories_lookup['Carbon_emissions']

    # Tally totals based on previous values in trackers form
    get_db_tracker = db.execute("SELECT vintage_clothing, sustainable_clothing, saved_plastic, saved_money, bought_local, less_beef, less_chicken, less_pork, total_score FROM trackers WHERE user_id=?", session.get("user_id"))
    print("GET DB shopping: ", get_db_tracker)
    for info in get_db_tracker: 
      vintage_clothes = info['vintage_clothing']
      sustainable_clothes = info['sustainable_clothing']
      saved_plastic = info['saved_plastic']
      saved_money = info['saved_money']
      bought_local = info['bought_local']
      less_beef = info['less_beef']
      less_chicken = info['less_chicken']
      less_pork = info['less_pork']
      total_score = info['total_score']
    
    vintage_clothes_total = int(vintage_clothes) + vintage_clothes_add
    sustainable_clothes_total = int(sustainable_clothes) + sustainable_clothes_add
    saved_plastic_total = int(saved_plastic) + plastic_saved_by_paper + plastic_saved_by_reusable
    saved_money_total = float(saved_money) + money_savings_plastic + drycleaning_savings + accessories_savings 
    bought_local_total = int(bought_local) + local_points
    new_beef_total = int(less_beef) + less_beef_add
    new_chicken_total = int(less_chicken) + less_chicken_add
    new_pork_total = int(less_pork) + less_pork_add
    carbon_savings_total = carbon_savings_beef + carbon_savings_chicken + carbon_savings_pork + carbon_savings_drycleaning + carbon_savings_restaurants + carbon_savings_accessories
    new_total_score = float(total_score) + vintage_clothes_add + sustainable_clothes_add + plastic_saved_by_paper + plastic_saved_by_reusable + local_points + less_beef_add + less_chicken_add + less_pork_add + carbon_savings_beef + carbon_savings_chicken + carbon_savings_pork + money_savings_plastic + drycleaning_savings + accessories_savings 

    # Update DB
    update_db = db.execute("UPDATE trackers SET vintage_clothing=?, sustainable_clothing=?, saved_plastic=?, saved_money=?, bought_local=?, less_beef=?, less_chicken=?, less_pork=?, carbon_savings=?, total_score=? WHERE user_id=?", vintage_clothes_total, sustainable_clothes_total, saved_plastic_total, saved_money_total, bought_local_total, new_beef_total, new_chicken_total, new_pork_total, carbon_savings_total, new_total_score, session.get("user_id"))
    check_db = db.execute("SELECT vintage_clothing, sustainable_clothing, saved_plastic, saved_money, bought_local, less_beef, less_chicken, less_pork, carbon_savings, total_score FROM trackers WHERE user_id=?", session.get("user_id")) 

    return render_template("/trackershopping.html", dietaryattitude=dietary_attitude, beefconsumption = beef_consumption, chickenconsumption=chicken_consumption, porkconsumption=pork_consumption, drycleaningspend=drycleaning_spend_db, restaurantsspend=restaurants_spend, accessories=accessories_spend)
  
  # Handle GET request
  else:
    print("We're here in get")
    check_footprint = db.execute("SELECT * FROM footprint WHERE user_id=?", session.get("user_id"))
    print("Check if footprint exists", check_footprint)
    if len(check_footprint) == 0:
      flash("Please calculate your carbon footprint to start")
      return redirect("/calculator")
    else:
      getdrycleaning = db.execute("SELECT drycleaning, drycleaning_impact FROM footprint WHERE user_id=?", session.get("user_id"))
      print("Drycleaning db: ", getdrycleaning)
      for info in getdrycleaning:
        drycleaning_spend_db = info['drycleaning']
        drycleaning_impact = info['drycleaning_impact']
      spending_impact = db.execute("SELECT beef_consumption, pork_consumption, chicken_consumption, dietary_attitude, restaurants, accessories, hotels FROM consumption_footprint WHERE user_id=?", session.get("user_id"))
      print("spending_impact", spending_impact)
      for item in spending_impact:
        beef_consumption = item['beef_consumption']
        pork_consumption = item['pork_consumption']
        chicken_consumption = item['chicken_consumption']
        dietary_attitude = item['dietary_attitude']
        restaurants = item['restaurants']
        accessories = item['accessories']
      print("Restaruants", restaurants)
      if restaurants == "No info given":
        print("Yup no info given")
        restaurants_spend = "You didn't mention when you started how much you were spending on restaurants. You can update that at any point. How much did you spend this month?"
      else:
        print("We're stuck in else over here")
        restaurants_spend = "When you got started you said you were spending $" + restaurants + "each month. How much did you spend this month?"
      
      if accessories == "No info given":
        accessories_spend = "You didn't mention when you started how much you were spending on accessories. You can update that at any point. How much did you spend this month?"
      else:
        accessories_spend = "When you got started you said you were spending $" + accessories + "each month. How much did you spend this month?"
      return render_template("/trackershopping.html", dietaryattitude=dietary_attitude, beefconsumption = beef_consumption, chickenconsumption=chicken_consumption, porkconsumption=pork_consumption, drycleaningspend=drycleaning_spend_db, restaurantsspend=restaurants_spend, accessories=accessories_spend)

@app.route("/trackertransport", methods=["GET", "POST"])
@login_required
def trackertransport():
  """Allows user to track their progress"""
  if request.method == "POST":
    print("We're in post")
    # Set region
    region = "US"
    
    # Get db values to repopulate fields on load 
    get_db_transport = db.execute("SELECT short_haul, medium_haul, long_haul FROM transport_footprint WHERE user_id=?", session.get("user_id"))
    get_db_spending = db.execute("SELECT hotels FROM consumption_footprint WHERE user_id=?", session.get("user_id"))
    print("GET TRANSPORT FROM DB: ", get_db_transport)
    for info in get_db_transport:
      short_haul = info['short_haul']
      medium_haul = info['medium_haul']
      long_haul = info['long_haul']
    total_flights = int(short_haul) + int(medium_haul) + int(long_haul)
    for info in get_db_spending: 
      hotel_nights = info['hotels']
    if hotel_nights == "No info given":
      hotel_nights = "You didn't mention how many nights you spend on average in hotels. You can change this at anytime to track your changes here."
      fewer_hotels_db = 0
    else:
      fewer_hotels_db = hotel_nights
    
    # Get current values from form
    get_db = db.execute("SELECT saved_money, saved_energy, vacationed_local, green_tariff, solar_panels, fewer_flights, fewer_hotels, more_direct_flights, miles_walk_bike, carbon_savings, total_score FROM trackers WHERE user_id=?", session.get("user_id"))
    print("GET DB: ", get_db)
    fewer_flights = request.form.get("fewer_flights")
    fewer_hotels = request.form.get("fewer_hotels")
    direct_flights = request.form.get("direct_flights")
    train_over_plane = request.form.get("train_over_plane")
    local_vacation = request.form.get("local_vacation")
    bike_walk = request.form.get("bike_walk")
    transport_savings = request.form.get("transport_savings")
    local_vacation = request.form.get("local_vacation")
    carbon_offset = request.form.get("carbon_offset")

    # Get values from tracker database
    tracker_db = db.execute("SELECT saved_money, vacationed_local, fewer_flights, fewer_hotels, more_direct_flights, miles_walk_bike, carbon_offset, carbon_savings, total_score FROM trackers WHERE user_id=?", session.get("user_id"))
    print("GET tracker for transport: ", tracker_db)
    for info in tracker_db:
      saved_money_db = info['saved_money']
      vacationed_local_db = info['vacationed_local']
      fewer_flights_db = info['fewer_flights']
      fewer_hotels_db = info['fewer_hotels']
      more_direct_flights_db = info['more_direct_flights']
      miles_walked_biked_db = info['miles_walk_bike']
      carbon_offset_db = info['carbon_offset']
      carbon_savings_db = info['carbon_savings']
      total_score_db = info['total_score']
        
    # Manage empty fields and start tally
    print("total flights: ", total_flights)
    print("fewer flights: ", fewer_flights)
    if fewer_flights is None:
      print("no fewer flights")
      flights_saved = 0
    else: 
      print("Took fewer flights; ", fewer_flights)
      if int(fewer_flights) > total_flights or int(fewer_flights) == total_flights:
        flights_saved = 0
      else:
        flights_saved = total_flights - int(fewer_flights)
    
    if fewer_hotels is None or fewer_hotels_db == 0:
      print("no fewer nights in hotels")
      hotel_nights_saved = 0 
      carbon_savings_hotel = 0
    else: 
      print("Fewer nights in hotels:", fewer_hotels)
      hotel_nights_saved = int(fewer_hotels_db) - int(fewer_hotels)
      # From calculator
      hotel_activity_id = "accommodation_type_hotel_stay"
      hotel_lookup = impact_by_number(hotel_activity_id, hotel_nights_saved, region)
      carbon_savings_hotel = hotel_lookup['Carbon_emissions']
      print("Hotels savings; ", hotel_nights_saved)
      print("Carbon Emissions saved: ", carbon_savings_hotel)
    
    if direct_flights is None:
      print("No more direct flights")
      direct_flights_add = 0
    else: 
      print("More direct flights: ", direct_flights)
      direct_flights_add = int(direct_flights)
    
    if train_over_plane is None:
      print("Didn't choose trains over planes")
      more_trains_add = 0 
    else: 
      print("Chose train over plane", train_over_plane)
      more_trains_add = int(train_over_plane)
    
    if local_vacation is None:
      print("No local vacations: ", local_vacation)
      local_vacation_add = 0
    else: 
      print("Took local vacation: ", local_vacation)
      local_vacation_add = int(local_vacation)
    
    if bike_walk is None: 
      print("No bike or walk over car")
      biked_miles_add = 0 
    else: 
      print("Chose to bike or walk: ", bike_walk)
      biked_miles_add = float(bike_walk)
    
    if transport_savings is None:
      print("No transport savings")
      money_savings_transport = 0
    else: 
      print("Transport Savings: ", transport_savings)
      money_savings_transport = float(transport_savings)
    
    if carbon_offset is None:
      print("No offsets")
      carbon_offset_status = 0
    else:
      print("Offsets: ", carbon_offset)
      carbon_offset_status = float(carbon_offset)
    
    # New scores totals
    total_flights_saved = int(fewer_flights_db) + flights_saved + more_trains_add
    carbon_savings_total = carbon_savings_hotel + float(carbon_savings_db)
    direct_flights_total = direct_flights_add + int(more_direct_flights_db)
    local_vacation_total = int(vacationed_local_db) + local_vacation_add
    total_hotel_nights_saved = int(fewer_hotels_db) + int(fewer_hotels)
    total_bike_walk = float(miles_walked_biked_db) + biked_miles_add
    money_savings_total = money_savings_transport + float(saved_money_db)
    carbon_offset_total = float(carbon_offset_db) + carbon_offset_status
    new_total_score = float(total_score_db) + flights_saved + int(fewer_hotels) + more_trains_add  + carbon_savings_hotel + direct_flights_add + local_vacation_add + biked_miles_add + money_savings_transport + carbon_offset_status

    print("Total flights saved: ", total_flights_saved)
    print("Carbon savings: ", carbon_savings_total)
    print("Total direct flights: ", direct_flights_total)
    print("locat vacation total: ", local_vacation_total)
    print("Total_bike_walk: ", total_bike_walk)
    print("Money savings total: ", money_savings_total)
    print("carbon offset total: ", carbon_offset_total)
    print("total carbon savings: ", carbon_offset_total)
    print("New total score: ", new_total_score)

    # Add new scores to db
    update_db = db.execute("UPDATE trackers SET saved_money=?, vacationed_local=?, fewer_flights=?, fewer_hotels=?, more_direct_flights=?, miles_walk_bike=?, carbon_offset=?, carbon_savings=?, total_score=? WHERE user_id=?", money_savings_total, local_vacation_total, total_flights_saved, total_hotel_nights_saved, direct_flights_total, total_bike_walk, carbon_offset_total, carbon_savings_total, new_total_score, session.get("user_id"))
    check_db = db.execute("SELECT saved_money, vacationed_local, fewer_flights, fewer_hotels, more_direct_flights, miles_walk_bike, carbon_offset, carbon_savings, total_score FROM trackers WHERE user_id=?", session.get("user_id"))
    print("Check db for update: ", check_db)
    return render_template("/trackertransport.html", totalflights=total_flights, hotelnights=hotel_nights)
  else:
    print("We're here in get")
    # Get values from db to populate fields:
    get_db_transport = db.execute("SELECT short_haul, medium_haul, long_haul FROM transport_footprint WHERE user_id=?", session.get("user_id"))
    get_db_spending = db.execute("SELECT hotels FROM consumption_footprint WHERE user_id=?", session.get("user_id"))
    print("GET TRANSPORT FROM DB: ", get_db_transport)
    for info in get_db_transport:
      short_haul = info['short_haul']
      medium_haul = info['medium_haul']
      long_haul = info['long_haul']
    total_flights = int(short_haul) + int(medium_haul) + int(long_haul)
    for info in get_db_spending: 
      hotel_nights = info['hotels']
    if hotel_nights == "No info given":
      hotel_nights = "You didn't mention how many nights you spend on average in hotels. You can change this at anytime to track your changes here."
    else:
      hotel_nights = hotel_nights
  return render_template("/trackertransport.html", totalflights=total_flights, hotelnights=hotel_nights)



# References sourced to build random username generator:
# https://grammar.yourdictionary.com/parts-of-speech/adjectives/list-of-adjective-words.html
# https://www.grammarly.com/blog/adjective/
# https://a-z-animals.com/animals/
# https://stackoverflow.com/questions/4319236/remove-the-newline-character-in-a-list-read-from-a-file 
