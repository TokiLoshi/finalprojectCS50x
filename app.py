
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

app.config['MAIL_SENDGRID_API_KEY'] = os.environ['SENDGRID_API_KEY']
mail = MailSendGrid(app)

# Configure CS50 Library to use SQLite and adapt to tranfer to PostGres for Heroku deployment
# https://cs50.readthedocs.io/heroku/
# uri = os.getenv("DATABASE_URL")
# if uri.startswith("postgres:"):
#   uri = uri.replace("postgress://", "postgresql://")

# db = SQL("sqlite:///carbon.db")

uri = os.getenv("DATABASE_URL")
if uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://")
db = SQL(uri)

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
  """Users' account page with their username information"""
  # Check if this is the user's first time on the account page 
  check_footprint = db.execute("SELECT user_id FROM footprint WHERE user_id=?", session.get("user_id"))
  if len(check_footprint) == 0: 
    flash("Please calculate your carbon footprint to get started.")
    return redirect("/calculator")
  
  # Get user information from database and extract elements for display
  get_user_info = db.execute("SELECT icon, name, leaderboardname, email, datejoined FROM users WHERE id=?", session.get("user_id"))
  if len(get_user_info) == 0:
      name = "unknown"
      leaderboardname = "unknown"
      emailaddy =  "unknown"
      datejoined = "unknown"
      print("We have unknowns in the account page, this is an error we haven't seen yet that needs to be explored")
  else:
    for info in get_user_info:
      icon = info['icon']
      name = info['name']
      leaderboardname = info['leaderboardname']
      emailaddy = info['email']
      datejoined = info['datejoined']

    # Manage instances where date has not been set by db, and pull date from caclulator 
    if datejoined is not None:
      datejoined = datejoined[:10]
    else:
      get_join_date = db.execute("SELECT datetime FROM consumption_footprint WHERE user_id=?", session.get("user_id"))
      for datapoint in get_join_date:
        datejoined = datapoint['datetime']
      if datejoined is None:
        datejoined = "Unknown"
      else:
        datejoined = datejoined[:10]
      
  if request.method == "POST":
    # This is to allower user to change their password
    return render_template("/changepassword.html")
  else:
    print("This GET request should show values on template")
  return render_template("/account.html", icon=icon, name=name, leaderboardname=leaderboardname, emailaddy=emailaddy, datejoined=datejoined)

# Calculator page for instructions and household calculations
@app.route("/calculator", methods=["GET", "POST"])
@login_required
def calculator():
  """Quiz user takes to tally up their carbon score"""
  if request.method == "POST":
    
    # Check the user hasn't already asked this: 
    check_not_answered = db.execute("SELECT * FROM footprint WHERE user_id=?", session.get("user_id"))
    len_footprint = len(check_not_answered)

    if len_footprint != 0:
      # Check if the user has completed the transport calculator
      users_transport_footprint = db.execute("SELECT * FROM transport_footprint WHERE user_id=?", session.get("user_id"))
      # If they have not completed the transport calculator then send them to it
      if len(users_transport_footprint) == 0: 
        return render_template("/calculatortransport.html")
      else: 
        
        # Check if user has completed the consumption calculator and if not send them to it
        users_consumption_footprint = db.execute("SELECT * FROM consumption_footprint WHERE user_id=?", session.get("user_id"))
        len_consumption = len(users_consumption_footprint)
        if len(users_consumption_footprint) == 0: 
          return render_template("/calculatorconsumption")
        else: 
          flash("You've already answered this, but you can update your answers in consumption.")
          return render_template("/calculatorconsumptionupdate.html")

    # Get information from form on template
    building = request.form.get("building")
    state = request.form.get("state")
    household_occupants = request.form.get("household_occupants")
    recycling = request.form.get("recycling")
    waste_frequency = request.form.get("rubbish")
    utility_bill = request.form.get("utilitybill")
    drycleaning = request.form.get("drycleaning")
    region = "US"

    # If all fields in the form are empty render the page as is
    if building is None and state is None and household_occupants is None and recycling is None and waste_frequency is None and utility_bill is None:
      return render_template("/calculator.html")

    # HACK: 
    # This is a once off we might want to factor into a lifetime footprint
    # Buildings multifamily is 0.113kg/USD median cost per unit is $64,500 0 $86,000 https://www.multifamily.loans/apartment-finance-blog/multifamily-construction-costs-an-investor-guide#:~:text=According%20to%20the%20most%20recent,%2464%2C500%20to%20%2486%2C000%20per%20unit. 
    multifamily_median = (64500 + 86000)/2
    singlefamily_median = 428700
    # Single family home is 0.226kgs/USD according to a service by the Motley Fool https://www.fool.com/the-ascent/research/average-house-price-state/#:~:text=Average%20home%20price%20in%20the%20United%20States%3A%20%24428%2C700&text=That's%20a%2030%25%20increase%20from,when%20the%20median%20was%20%24329%2C000.&text=Median%20sales%20price%20of%20homes,of%20homes%20in%20the%20U.S.&text=Data%20source%3A%20Federal%20Reserve%20Bank%20of%20St
    
    # Handle empty values for the building, otherwise calculate score and impact
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
      print("This is an error in the calculator page that shouldn't be occurring, need to look into this")

    # Work out impact by electricity and handle empty values
    electricity_activity_id = "electricity-energy_source_grid_mix"
    if state is None:
      state = "Info not provided"
      impact_electricity = "Need more info to calculate"
    elif utility_bill == 0:
      impact_electricity = 0
    else:  
      region = state
      energy = float(utility_bill)
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
      recycling = int(recycling)
      if recycling == 0:
        percentage_recycled = 0
      else:
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
    
    # Calculate impact of drycleaning per person in house and manage empty fields 
    if drycleaning == 0 :
      drycleaning_impact = 0
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
    return redirect("/calculatortransport")
  else:
    # Check to see which calculator questions the user has answered and send them to the missing ones in the appropriate order
    check_footprint = db.execute("SELECT * FROM footprint WHERE user_id=?", session.get("user_id"))
    len_footprint = len(check_footprint)
    if len(check_footprint) == 0:
      return render_template("/calculator.html")
    else: 
      check_transport = db.execute("SELECT * FROM transport_footprint WHERE user_id=?", session.get("user_id"))
      len_transport = len(check_transport)
      if len_transport == 0:
        return render_template("/calculatortransport.html")
      else:
        check_consumption = db.execute("SELECT * FROM consumption_footprint WHERE user_id=?", session.get("user_id"))
        len_consumption = len(check_consumption)
        if len_consumption == 0:
          return render_template("/calculatorconsumption.html")
        else:
          flash("You've already answered this, but you can update your answer.")
          return render_template("/calculatorconsumptionupdate.html")

# Calculator page for transport
@app.route("/calculatortransport", methods=["GET", "POST"])
@login_required
def calculatortransport():
  """Quiz user takes to tally up their carbon score"""
  if request.method == "POST":
    # Get values from form in template 
    work_situation = request.form.get("work_situation")
    commuter_days = request.form.get("commuter_days")
    commuter_distance = request.form.get("commuter_distance")
    transport_mode = request.form.get("transport_mode")
    short_haul = request.form.get("short_haul")
    medium_haul = request.form.get("medium_haul")
    long_haul = request.form.get("long_haul")
    transport_cost = float(request.form.get("transport_cost"))
    # Set region for impact calculations using API calls
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
    check_updates_db = db.execute("SELECT * FROM transport_footprint WHERE user_id=?", session.get("user_id"))
    return render_template("/calculatorconsumption.html")
  else: 
    # Check the database to see which calculator questions might be missing and redirect appropriately 
    check_footprint = db.execute("SELECT * FROM footprint WHERE user_id=?", session.get("user_id"))
    len_footprint = len(check_footprint)
    if len_footprint == 0:
      return render_template("/calculator.html")
    else:
      check_transport = db.execute("SELECT * FROM transport_footprint WHERE user_id=?", session.get("user_id"))
      len_transport = len(check_transport)
      if len_transport == 0:
        return render_template("/calculatortransport.html")
      else: 
        check_consumption = db.execute("SELECT * FROM consumption_footprint WHERE user_id=?", session.get("user_id"))
        len_consumption = len(check_consumption)
        if len_consumption == 0:
          return render_template("/calculatorconsumption.html")
        else:
          flash("It looks like we already have your answers saved, but you can update any of these you haven't answered and then view the updated results.")
          return render_template("/calculatorconsumptionupdate.html")

# Calculator page for consumption
@app.route("/calculatorconsumption", methods=["GET", "POST"])
@login_required
def calculatorconsumption():
  """Quiz user takes to tally up their carbon score"""
  if request.method == "POST":
    # Get values from the form
    beef = request.form.get("beef")
    pork = request.form.get("pork")
    chicken = request.form.get("chicken")
    flexitarian = request.form.get("flexitarian")
    new_clothes = request.form.get("new_clothes")
    restaurants = request.form.get("restaurants")
    accessories = request.form.get("accessories")
    appliances = request.form.get("appliances")
    hotels = request.form.get("hotels")
    # Set region for estimates using API calls 
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
    
    # Hotel impact at 16.1kg (default 2022).ex per night 
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
   # Check to see what user has answered and redirect appropriately 
    check_footprint = db.execute("SELECT * FROM footprint WHERE user_id=?", session.get("user_id"))
    len_footprint = len(check_footprint)
    if len_footprint == 0:
      return render_template("/calculator.html")
    else: 
      check_transport = db.execute("SELECT * FROM transport_footprint WHERE user_id=?", check_transport)
      len_transport = len(check_transport)
      if len_transport == 0: 
        return render_template("/calculatortransport.html")
      else: 
        check_consumption = db.execute("SELECT * FROM footprint WHERE user_id=?", session.get("user_id"))
        len_consumption = len(check_consumption)
        if len_consumption == 0: 
          return render_template("/calculatorconsumption.html")
        else: 
          flash("You've already answered that but you can update any answers you haven't filled out and review your updated results")
          return render_template("/caclulatorconsumptionupdate")

@app.route("/iconcolor", methods=["GET", "POST"])
@login_required
def iconcolor():
  """Allows user to change colors"""
  # TO DO:
  # Add this to a future GitHub project to allow user to change the color of their icons on display
  # Add these to the leaderboard to help make each user look more unique

  if request.method == "POST":
    animal = "horse"
    color = "fade"
    display_icon = customicon(animal, color)
    icon = request.form.get("value")
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
    # check which icon user chose via args 
    check_icon = request.args.get("animal")
    return render_template("leaderboardicon.html")
  else:
    # check which icon user chose via args 
    check_icon = request.args.get("animal")
    if check_icon is not None: 
      # Check which icon user had in db
      check_db_icon = db.execute("SELECT icon FROM users WHERE id=?", session.get("user_id"))
      for item in check_db_icon:
        old_icon = item['icon']
      
      # Handle case for new users not having an icon in the db
      if old_icon == None:
        icon = check_icon
        update_new_icon = db.execute("UPDATE users SET icon=? WHERE id=?", icon, session.get("user_id"))
        flash("You've got yourself a new icon. Looking good!")
        return redirect("/account")
      else:

        # Update icon where users had already selected an icon and it was saved to the database
        icon = check_icon
        update_new_icon = db.execute("UPDATE users SET icon=? WHERE id=?", icon, session.get("user_id"))
        flash("Nice new icon!")
        return redirect("/account")

    # Render tempate and display icon 
    return render_template("leaderboardicon.html", icon=icon)

# Calculator page for consumption
@app.route("/calculatorconsumptionupdate", methods=["GET", "POST"])
@login_required
def calculatorconsumptionupdate():
  """Quiz user can update certain fields of their carbon score if they didn't do that already"""
  if request.method == "POST":
    # Get information from form in template 
    new_clothes = request.form.get("new_clothes")
    restaurants = request.form.get("restaurants")
    accessories = request.form.get("accessories")
    appliances = request.form.get("appliances")
    hotels = request.form.get("hotels")
    # Set region for estimates using API calls
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
    
    # Extract values from list of dictionaries db returned 
    for answer in get_current_total:
      # Convert tons to kgs
      if "tons of cO2 per year" in answer['consumption_footprint_total']:
        current = float((answer['consumption_footprint_total']).replace("tons of cO2 per year", "")) * 1000
      else:
        current = float((answer['consumption_footprint_total']).replace("ton of cO2 per year", "")) * 1000
    
    # Calculate consumption totals
    consumption_sum = (hotel_add + clothing_add + accessories_add + appliances_add + restaurants_add)
    total_consumption_footprint = current + hotel_add + clothing_add + accessories_add + restaurants_add + appliances_add
    total_consumption_formatted = co2(total_consumption_footprint)
    update_consumption_footprint = db.execute("UPDATE consumption_footprint SET new_clothes=?, new_clothes_impact=?, restaurants=?, restaurants_impact=?, accessories=?, accessories_impact=?, hotels=?, hotels_impact=?, appliances=?, appliances_impact=?, consumption_footprint_total=? WHERE user_id=?", clothing_spend, clothing_impact, restaurants_spend, restaurants_impact, accessories_spend, accessories_impact, hotels, hotel_impact, appliances_spend, appliances_impact, total_consumption_formatted, session.get("user_id"))
    show_update = db.execute("SELECT * FROM consumption_footprint WHERE user_id=?", session.get("user_id"))
    flash("Results are ready 🤩")
    return redirect("/results")
  else: 
    
    # Get the values from the calculator db
    check_footprint = db.execute("SELECT * FROM footprint WHERE user_id=?", session.get("user_id"))
    # Check to see what users have answered and redirect if needed
    len_footprint = len(check_footprint)
    if len_footprint == 0: 
      return render_template("/calculator.html")
    else: 
      check_transport = db.execute("SELECT * FROM transport_footprint WHERE user_id=?", session.get("user_id"))
      len_transport = len(check_transport)
      if len_transport == 0:
        return render_template("/calculatortransport.html")
      else:
        check_consumption = db.execute("SELECT * FROM consumption_footprint WHERE user_id=?", session.get("user_id"))
        len_consumption = db.execute("SELECT * FROM consumption_footprint WHERE user_id=?", session.get("user_id"))
        if len_consumption == 0:
          return render_template("/calculatorconsumption.html")
        else:
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
      flash("Please pick a leaderboard name.")
      return render_template("/changename.html", randomname=randomname)

    # Check that leaderboard name is unique 
    checkdb = db.execute("SELECT * FROM users WHERE leaderboardname=?", new_leaderboard_name)
    if len(checkdb) != 0:
      flash("It looks like that names been taken, please try again.")

    # Update leaderboard name in db and return to accoutns page
    else:
        flash("Update successful 👌")
        updateleaderboardname = db.execute("UPDATE users SET leaderboardname=? WHERE id=?", new_leaderboard_name, session.get("user_id"))
        updateleaderboardname_lb = db.execute("UPDATE leaderboard SET leaderboardname=? WHERE user_id=?", new_leaderboard_name, session.get("user_id"))
        return redirect("/account")
  
  # Handle GET request 
  else:
    # Check leaderboardname from helpers 
    randomname = random_leaderboardname()
    
    # Get leaderboardname from form on template
    new_leaderboard_name = request.form.get("leaderboardname")

    # Handle case if leaderboardname is blank
    if new_leaderboard_name is None:
      return render_template("/changename.html", randomname=randomname)

    if new_leaderboard_name is None:
       flash("Enter your new name into the form below.")
       randomname = random_leaderboardname()
    return render_template("/changename.html", randomname=randomname)
  
  return render_template("/changename.html", randomname=randomname)

@app.route("/changepassword", methods=["GET", "POST"])
@login_required
def changepassword():
  """Allow users to change their password"""
  if request.method == "POST":
    
    # Get password and confirmation from form
    newpassword = request.form.get("password")
    confirmpassword = request.form.get("confirmpassword")

    # Check password and confirmation aren't blank 
    if len(newpassword) == 0:
      return apology("No password entered, please enter a password")
    elif len(confirmpassword) == 0:
      return apology("No confirmation entered")

    # Check password meets minimum requirements
    elif len(newpassword) < 8:
      return apology("Password must be 8 or more characters long")
    
    # Check password and confirmation match
    elif newpassword != confirmpassword:
      return apology("Passwords dn't match")
    else:
      
      # Generate a hash of the temp password and add to DB
      new_hash = generate_password_hash(newpassword, method="pbkdf2:sha256", salt_length=8) 
      update_hash = db.execute("UPDATE users SET hash=? WHERE id=?", new_hash, session.get("user_id"))

      flash("You password has been updated 👍")
    return redirect("/account")

  else:
    return render_template("/changepassword.html")
      

# Challenges page
@app.route("/challenges", methods=["GET", "POST"])
@login_required
def challenges():
  """Allows the user to enroll in challenges that will promote a lower carbon footprint"""
  check_footprint = db.execute("SELECT user_id FROM footprint WHERE user_id=?", session.get("user_id"))
  if len(check_footprint) == 0: 
    flash("Please calculate your carbon footprint to get started 👣")
    return redirect("/calculator")
  else:
    if request.method=="POST":
      # Inital pledge value set to zero
      new_pledge = 0
      # Check if there are completed challenges: 
      check_lb = db.execute("SELECT challenges FROM leaderboard WHERE user_id=?", session.get("user_id"))

      for challenge in check_lb:
        challenges = int(challenge['challenges'])
      if challenges == 0:
        counter = "You haven't completed any challenges yet. You can mark challenges you've enrolled in as 'done' on your home page."
      elif challenges == 1:
        counter = "You have completed 1 challenge so far. Great start, don't stop! We're rooting for you."
      else: 
        challenges = str(challenges)
        counter = "You have completed " + challenges + " challenges so far. Keep going!"

      # Get values from form and set scores 
      flexitarian = request.form.get("flexitarian")
      lightbulbs = request.form.get("LED")
      green_miles = request.form.get("green-miles")
      fashion = request.form.get("fashion")
      plastics = request.form.get("plastics")
      bags = request.form.get("bags")

      if flexitarian is None: 
        print("They didn't choose flexitarian")
      else:
        challenge_accepted = "Flexitarian"
        new_pledge = str(flexitarian) + " days"

      if lightbulbs is None: 
        print("They didn't choose lightbulbs")
      else: 
        challenge_accepted = "LEDs"
        new_pledge = str(lightbulbs) + " bulbs"
      
      if green_miles is None: 
        print("They didn't choose green miles")
      else: 
        challenge_accepted = "Green Miles"
        new_pledge = str(green_miles) + " miles"
      
      if fashion is None: 
        print("They didn't choose fashion")
      else:
        challenge_accepted = "Sustainable Fashion"
        new_pledge = str(fashion) + " garments"

      if plastics is None: 
        print("They didn't choose plastics")
      else: 
        challenge_accepted = "Save Plastic"
        new_pledge = str(plastics) + " plastics"

      if bags is None: 
        print("They didn't choose bags")
      else: 
        challenge_accepted = "Use own bags"
        new_pledge = str(bags) + " bags"
      
      # Handle case for someone visiting challenges and has no challenges selected or in the DB:
      if flexitarian is None and lightbulbs is None and green_miles is None and fashion is None and plastics is None and bags is None:
        challenge_accepted = "None Accepted"
        pledge = 0

      # Check challenges in DB
      pledge = 0
      challenge_selected= "None"
      check_db = db.execute("SELECT * FROM challenges WHERE user_id=?", session.get("user_id"))
      
      # Extract values from list of dictionaries returned by db
      for item in check_db:
        challenge_selected = item['challenge']
        pledge = item['pledge']
        if challenge_selected in challenge_accepted:
          if flexitarian is None and lightbulbs is None and green_miles is None and fashion is None and plastics is None and bags is None and challenge_accepted == "None Accepted":
            flash("Let's get you started with a challenge")
            return render_template("/challenges.html")
          else:
            # Notify user if they have already selected that challenge (can't select the same challenge twice)
            flash("You've already selected that. If you've finished it please mark it as done in your account ✅")
            return redirect("/challenges")
      
      # Get leaderboard info
      get_leaderboard_name = db.execute("SELECT leaderboardname FROM users WHERE id=?", session.get("user_id"))
      for name in get_leaderboard_name: 
        lb_name =  name['leaderboardname']
      
      # Update DB and overwrite the none value that gets passed in at register
      if pledge == 0 and challenge_selected == 'None Accepted':
        update_db = db.execute("UPDATE challenges SET challenge=?, pledge=? WHERE user_id=?", challenge_accepted, new_pledge, session.get("user_id"))
        return render_template("/challenges.html", counter=counter)
      else:

        # If user already has an active challenge, insert new challenge into db
        insert_new_challenge = db.execute("INSERT INTO challenges (user_id, leaderboardname, challenge, pledge) VALUES(?, ?, ?, ?)", session.get("user_id"), lb_name, challenge_accepted, new_pledge)
        check_for_none = db.execute("SELECT * FROM challenges WHERE user_id=?", session.get("user_id"))
        for current_challenges in check_for_none: 
          old_current_challenges = current_challenges['challenge']
          if 'None Accepted' in old_current_challenges:
            remove_old_none = db.execute("DELETE FROM challenges WHERE challenge='None Accepted' AND user_id=?", session.get("user_id"))
        check_updates = db.execute("SELECT * FROM challenges WHERE user_id=?", session.get("user_id"))
        flash("You got it!")
        
        # Check if there are completed challenges: 
        check_lb = db.execute("SELECT challenges FROM leaderboard WHERE user_id=?", session.get("user_id"))
        for challenge in check_lb:
          challenges = int(challenge['challenges'])
        if challenges == 0:
          counter = "You haven't completed any challenges yet. You can mark challenges you've enrolled in as 'done' on your home page."
        else: 
          challenges = str(challenges)
          counter = "You have completed " + challenges + " so far. Keep going!"
          return render_template("/challenges.html", counter=counter)
        return render_template("/challenges.html", counter=counter)

    else: 
      # Check if there are completed challenges: 
      check_lb = db.execute("SELECT challenges FROM leaderboard WHERE user_id=?", session.get("user_id"))
      # Extract values and manage counter with empty challenges, 1 challenge or multiple challenges 
      for challenge in check_lb:
        challenges = int(challenge['challenges'])
      if challenges == 0:
        counter = "You haven't completed any challenges yet. You can mark challenges you've enrolled in as 'done' on your home page."
        return render_template("/challenges.html", counter=counter)
      elif challenges == 1:
        counter = "You have completed 1 challenge so far. Great start, don't stop! We're rooting for you."
        return render_template("/challenges.html", counter=counter)
      else: 
        challenges = str(challenges)
        counter = "You have completed " + challenges + " challenges so far. Keep going!"
        return render_template("/challenges.html", counter=counter)

# Contact page
@app.route("/contact", methods=["GET", "POST"])
def contact():
  """Allows the user to submit a request or feedback"""
  if request.method == "POST":
    visitor_name = request.form.get("name")
    vistor_email = request.form.get("email")
    visitor_message = request.form.get("message")

    # Use sendgrid to send an email to admin with the users message
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
    flash("🙌 Questions? Would love to hear them. Leave a message below.")
    return render_template("/contact.html")

# Main home page
@app.route("/", methods=["GET"])
def home():
  """Information about the web app and what it does"""
  if request.method == "POST":
    print("This is a POST request in the home page which should not be happening")
    return render_template("/home.html")
  else: 
    flash("Welcome!")
    return render_template("home.html")

# Page user sees after they return 
@app.route("/homeuser", methods=["GET", "POST"])
@login_required
def homeuser():
  """Displays information for returning user"""
  # Handle POST request
  if request.method == "POST":
    flash("👋")
    return redirect("/homeuser")
  
  # Handle GET request
  else:
    # Check if this is the user's first time on the home page: 
    check_footprint = db.execute("SELECT user_id FROM footprint WHERE user_id=?", session.get("user_id"))
    if len(check_footprint) == 0: 
      flash("Please calculate your carbon footprint to get started.")
      return redirect("/calculator")

    # Get Challenges from DB and handle cases where users haven't completed any challenges
    challenges_db = db.execute("SELECT challenge, pledge FROM challenges WHERE user_id=?", session.get("user_id"))
    if len(challenges_db) == 0:
        pledged_amount = 0
        get_leaderboardname = db.execute("SELECT leaderboardname FROM users WHERE id=?", session.get("user_id"))
        for name in get_leaderboardname:
          user_leaderboardname = name['leaderboardname']
        challenge_to_add = "None Accepted"
        update_from_empty = db.execute("INSERT INTO challenges (user_id, leaderboardname, challenge, pledge) VALUES(?, ?, ?, ?)", session.get("user_id"), user_leaderboardname, challenge_to_add, pledged_amount)
        return redirect("/homeuser") 
    else:
      # Initialize pledges to zero and extract challenge information from the list of dictionaries returned by DB
      amounts_pledged = 0
      for challenge in challenges_db:
        challenges_accepted = challenge['challenge']
        amounts_pledged = challenge['pledge']

    # Get list of current challenges for user to check off when one is done
    challenge_completed = db.execute("SELECT challenge FROM challenges WHERE user_id=?", session.get("user_id"))
    challenge_updated = request.args.get("challengecompleted")
    
    if challenge_updated is not None: 
      # Updated Database 
      update_challenges_database = db.execute("DELETE FROM challenges WHERE challenge=? AND user_id=?", challenge_updated, session.get("user_id"))
      no_challenges = 0
      check_challenges = db.execute("SELECT * FROM challenges WHERE user_id=?", session.get("user_id"))
      
      # Handling case where there are no challenges left
      if check_challenges is None:
        update_pledge = 0
        update_challenges = db.execute("UPDATE challenges SET challenge=?, pledge=?", update_challenges, update_pledge)
      
      # Update Leaderboard to increase number of challenges completed
      get_no_challenges_from_lb = db.execute("SELECT challenges FROM leaderboard WHERE user_id=?", session.get("user_id"))
      for challenges in get_no_challenges_from_lb:
        old_no_challenges = challenges['challenges']
      updated_challenges = int(old_no_challenges) + 1
      lb_challenge_update = db.execute("UPDATE leaderboard SET challenges=? WHERE user_id=?", updated_challenges, session.get("user_id"))

      # Update points in trackers: 
      get_original_points = db.execute("SELECT total_score FROM trackers WHERE user_id=?", session.get("user_id"))
      
      # Extract elements from the list of dictionaries returned by the db
      for score in get_original_points:
        old_score = score['total_score']
      if "," in old_score:
        old_score = old_score.replace(",", "")
      old_score = float(old_score)
      new_score = old_score + 1.00
      # Update the trackers table with the new scores 
      update_trackers = db.execute("UPDATE trackers SET total_score=? WHERE user_id=?", new_score, session.get("user_id"))
      return redirect("/homeuser")
    
    # Get footprint Data
    footprint_db = db.execute("SELECT electricity, waste_frequency, recycling, landfill_impact, recycling_impact, total_footprint_general FROM footprint WHERE user_id=?", session.get("user_id"))

    # Get transport data 
    transport_footprint_db = db.execute("SELECT transport_cost, short_haul, medium_haul, long_haul, transport_footprint_total FROM transport_footprint WHERE user_id=?", session.get("user_id"))
    # Get consumption data 
    consumption_footprint_db = db.execute("SELECT beef_consumption, pork_consumption, chicken_consumption, hotels, consumption_footprint_total FROM consumption_footprint WHERE user_id=?", session.get("user_id"))
    # Get information from trackers table 
    trackers_db = db.execute("SELECT added_friends, planted_trees, helped_community, vintage_clothing, sustainable_clothing, saved_plastic, saved_money, saved_energy, bought_local, vacationed_local, less_beef, less_chicken, less_pork, more_compost, green_tariff, solar_panels, saved_water, less_waste, more_recycling, fewer_flights, fewer_hotels, more_direct_flights, miles_walk_bike, carbon_offset, carbon_savings, total_score FROM trackers WHERE user_id=?", session.get("user_id"))
    # Get date the user joined from users table 
    get_date_joined = db.execute("SELECT leaderboardname, datejoined FROM users WHERE id=?", session.get("user_id"))
    
    # Extract date joined and format into month
    months_in_year = {1 : "January", 2 : "February", 3 : "March", 4 : "April", 5 : "May", 6 : "June", 7 : "July", 8 : "August", 9 : "September", 10: "October", 11 : "November", 12 : "December"}
    for item in get_date_joined:
      leaderboardname = item['leaderboardname']
      date_joined = item['datejoined']

    # If the date joined is not filled in on the users table we look to the consumption footprint for the date of completion and format date  
    if date_joined is None or len(date_joined) == 0:
      get_datetime_consumption = db.execute("SELECT datetime FROM consumption_footprint WHERE user_id=?", session.get("user_id"))
      for item in get_datetime_consumption:
        date_joined = item['datetime']
      if date_joined is None or len(get_datetime_consumption) == 0:
        formatted_date_joined = "2022-10-19"
      else:
        formatted_date_joined = date_joined[:10]
    else:
      formatted_date_joined = date_joined[:10]
    
    date_year = (formatted_date_joined[:5])
    date_month = int(formatted_date_joined[5:8].replace("-", ""))
    date_day = formatted_date_joined[8:]
    display_date = date_day + " " + months_in_year[date_month] + " " + date_year.replace("-", "") 
    
    # Check for challenges they wanted to update: 
    challenge_updated = request.form.get("challengecompleted")
    if challenge_updated is None: 
      print("Nothing to update here")
    else: 
      print("They wanted the following to be updated: ", challenge_updated)

    # Extract values from footprint
    for input in footprint_db: 
      electricity_db = input['electricity']
      waste_frequency_db = input['waste_frequency']
      recycling_db = input['recycling']
      landfill_impact = input['landfill_impact']
      recycling_impact = input['recycling_impact']
      total_footprint_general_db = input['total_footprint_general']

    # Format recycling and waste
    if waste_frequency_db is None:
      total_waste_display = "No info yet, please use the calculator to find out more"
    else:
      total_waste_display = waste_frequency_db

    if recycling_db is None:
      recycling_display = "No info yet, please use the calculator to find out more"
    else: 
      recycling_display = str(recycling_db) + "%"

    if landfill_impact is None:
      landfill_impact_display = "No info yet, please use the calculator to find out more"
    else: 
      landfill_impact_display = co2(float(landfill_impact))

    if recycling_impact is None:
      recycling_impact_display = "No info yet, please use the calculator to find out more"
    else:
      recycling_impact_display = co2(float(recycling_impact))

    # Format electricity
    if electricity_db is None:
      electricity_display = "No info yet, please use the calculator to find out more"
    else:
      electricity_display = electricity_db

    # Extract values from transport footprint
    for input in transport_footprint_db:
      transport_cost_db = input['transport_cost']
      short_haul_db = input['short_haul']
      medium_haul_db = input['medium_haul']
      long_haul_db = input['long_haul']
      transport_footprint_total_db = input['transport_footprint_total']

    # Get total values of flights from transport and cost of transport
    total_flights = int(short_haul_db) + int(medium_haul_db) + int(long_haul_db)


    # Extract values from consumption footprint
    for input in consumption_footprint_db:
      beef_consumption_db = input['beef_consumption']
      pork_consumption_db = input['chicken_consumption']
      chicken_consumption_db = input['pork_consumption']
      hotels_db = input['hotels']
      consumption_footprint_total_db = input['consumption_footprint_total']
    
    # Format beef for display: 
    if beef_consumption_db == "I don't eat beef" :
      beef_display = "You were not eating beef"
    elif int(beef_consumption_db) == 1:
      beef_display = "You were eating beef once a week"
    else:
      beef_consumption_db = str(beef_consumption_db)
      beef_display = "You were eating beef " + beef_consumption_db + " times a week"

    # Format chicken for display: 
    if chicken_consumption_db == "I don't eat chicken":
      chicken_display = "You were not eating chicken"
    elif int(chicken_consumption_db) == 1:
      chicken_display = "You were eating chicken once a week"
    else:
      chicken_consumption_db = str(chicken_consumption_db)
      chicken_display = "You were eating chicken " + chicken_consumption_db + " times a week"
    
    # Format pork for display: 
    if pork_consumption_db == "I don't eat pork" :
      pork_display = "You were not eating pork"
    elif int(pork_consumption_db) == 1:
      pork_display = "You were eating pork once a week"
    else:
      pork_consumption_db = str(pork_consumption_db)
      pork_display = "You were eating pork " + pork_consumption_db + " times a week"

    if hotels_db == "No info given":
      hotels_display = "Please complete the calculator to start tracking this"
    else:
      hotels_display = str(int(hotels_db)) + " nights a year"

    # Calculate total footprint and times 1000:
    if "tons" in total_footprint_general_db:
      db_general_total_footprint = total_footprint_general_db.replace(" tons of cO2 per year", "")
    else:
      db_general_total_footprint = total_footprint_general_db.replace(" ton of cO2 per year", "")
    
    if "tons" in transport_footprint_total_db:
      db_transport_total_footprint = transport_footprint_total_db.replace(" tons of cO2 per year", "")
    else:
      db_transport_total_footprint = transport_footprint_total_db.replace(" ton of cO2 per year", "")

    if "tons" in consumption_footprint_total_db:
      db_consumption_total_footprint = consumption_footprint_total_db.replace(" tons of cO2 per year", "")
    else:
      db_consumption_total_footprint = consumption_footprint_total_db.replace(" ton of cO2 per year", "")

    number_in_general_total_footprint = float(db_general_total_footprint) * 1000
    number_in_transport_footprint_total_db = float(db_transport_total_footprint) * 1000
    number_in_consumption_footprint_total_db = float(db_consumption_total_footprint) * 1000
    grand_total = co2(number_in_general_total_footprint + number_in_transport_footprint_total_db +  number_in_consumption_footprint_total_db)

    # Extract values from trackers 
    for input in trackers_db:
      added_friends_db = input['added_friends']
      planted_trees_db = input['planted_trees']
      helped_community_db = input['helped_community']
      vintage_clothing_db = input['vintage_clothing']
      sustainable_clothing_db = input['sustainable_clothing']
      saved_plastic_db = input['saved_plastic']
      saved_money_db = input['saved_money']
      saved_energy_db = input['saved_energy']
      bought_local_db = input['bought_local']
      vacationed_local_db = input['vacationed_local']
      less_beef_db = input['less_beef']
      less_chicken_db = input['less_chicken']
      less_pork_db = input['less_pork']
      more_compost_db = input['more_compost']
      green_tariff_db = input['green_tariff']
      solar_panels_db = input['solar_panels']
      saved_water_db = input['saved_water']
      less_waste_db = input['less_waste']
      more_recycling_db = input['more_recycling']
      fewer_flights_db = input['fewer_flights']
      fewer_hotels_db = input['fewer_hotels']
      more_direct_flights_db = input['more_direct_flights']
      miles_walk_bike_db = input['miles_walk_bike']
      carbon_offset_db = input['carbon_offset']
      carbon_savings_db = input['carbon_savings']
      total_score_db = input['total_score']

      # Format clothes and plastic 
      if saved_plastic_db == 0:
        display_plastic = "You haven't logged anything yet, but you can in the tracker."
      elif saved_plastic_db == 1:
        display_plastic = "You've saved at least one piece of plastic. This is the start of beautiful things."
      else: 
        saved_plastic_db = str(saved_plastic_db)
        # Lifecylce of plastic https://www.wwf.org.au/news/blogs/the-lifecycle-of-plastics
        display_plastic = "You've saved " + saved_plastic_db + " pieces of plastic that otherwise might have landed up in the oceans, or in our drinking water. Plastic bags take 20 years to break down. Plastic cups can take as long as 450 years."
      
      if vintage_clothing_db == 0:
        vintage_clothing = 0
      else:
        vintage_clothing = int(vintage_clothing_db)
      
      if sustainable_clothing_db == 0:
        sustainable_clothing = 0
      else:
        sustainable_clothing = int(sustainable_clothing_db)
      sustainable_clothing_decisions = vintage_clothing + sustainable_clothing
      if sustainable_clothing_decisions == 0:
        clothing_display = "We don't have anything yet, but you can change that in the tracker."
      elif sustainable_clothing_decisions == 1: 
        clothing_display = "once and we think it looks great on you! Keep going."
      else: 
        clothing_display = str(sustainable_clothing_decisions) + " times. This look suits you!"

      if bought_local_db == 0:
        local_shopping = "If you've shopped locally lately tell us in tracker so we can give you kudos."
      elif bought_local_db == 1: 
        local_shopping = "You've increased how much you've shopped locally, we thank you and so do your local farmers and businesses."
      else: 
        local_shopping = "You last reported getting at least " + str(bought_local_db) + " percent of your groceries locally."

      # Format community
      if int(added_friends_db) == 0:
        display_friends = "If you've brought any friends onboard please add it to the tracker so we can thank you."
      elif int(added_friends_db) == 1: 
        display_friends = "Thank you for a new friend."
      else: 
        added_friends = str(added_friends_db)
        display_friends = "Thank you for " + added_friends + " new friends"
      
      if int(helped_community_db) == 0:
        helped_out = "If you've helped your community become more sustainable recently, please add it to the tracker"
      elif int(helped_community_db) == 1:
        helped_out = "You've helped your community once already. This is the start of something beautiful."
      else:
        helped_community_db = str(helped_community_db)
        helped_out = "You've shown up for your community " + helped_community_db + " times! We all appreciate you!"
      
      if int(planted_trees_db) == 0:
        display_planted_trees = "If you've planted any trees lately log it in your tracker"
      elif int(planted_trees_db) == 1:
        display_planted_trees = "You've planted your first tree since starting. Your community is looking greener already!"
      else: 
        planted_trees_db = str(planted_trees_db)
        display_planted_trees = "You've planted " + planted_trees_db + " and we think you're amazing!"

      # Format saved energy for display
      if saved_energy_db == 0:
        saved_energy_display = "Please log an energy saving activity to start tracking your progress here."
      else:
        saved_energy_display = saved_energy_db
      
      if green_tariff_db == "No":
        green_tariff_display = "If you've selected a green tariff from your energy provider let us know in the tracker."
      else:
        green_tariff_display = "Nice work on asking your energy provider to keep you green."
      
      if solar_panels_db == "No":
        solar_panel_display = "If you've gone solar let us know in the db"
      else:
        solar_panel_display = "Nice work going solar and getting your energy from renewable sources!"
      
      if saved_water_db == 0: 
        saved_water_display = "If you've saved water lately let us know in the tracker so we can give you kudos."
      elif saved_water_db == 1: 
        saved_water_display = "You've logged your first time saving water. Keep it going!"
      else: 
        saved_water_db = str(saved_water_db)
        saved_water_display = "You've saved water " + saved_water_db + " times. Thank you!" 

      # Format flexitarian options 
      if less_beef_db == 0:
        beef_less_display = "If you were planning on eating beef recently and substituted for a vegetarian option, please log it in the tracker so we can give you kudos."
      elif less_beef_db == 1: 
        beef_less_display = "Substituted beef once"
      else: 
        beef_less_display = "Substituted beef " + str(less_beef_db) + " times."

      if less_chicken_db == 0: 
        chicken_less_display = "If you were planning on eating chicken recently and substituted it for a vegetarian option, please log it in the tracker so we can give you kudos."
      elif less_chicken_db == 1: 
        chicken_less_display = "Substituted chicken once"
      else:
        chicken_less_display = "Substituted chicken " + str(less_chicken_db) + " times."

      if less_pork_db == 0:
        pork_less_display = "If you were planning on eating pork recently and substituted it for a vegetarian option, please log it in the tracker so we can give you kudos."
      elif less_pork_db == 1:
        pork_less_display = "Substituted pork once"
      else:
        pork_less_display = "Substituted pork " + str(less_pork_db) + " times."

      # Format composing and recycling
      if more_recycling_db == 0:
        more_recycling_display = "If you've recycled more lately log it in the tracker to start seeing progress."
      else: 
        more_recycling_display = str(more_recycling_db * 10) + "%"
      
      if more_compost_db == 0:
        more_compost_display = "If you've composted more lately log it in the tracker so we can give you kudos."
      else:
        more_compost_display = str(more_compost_db) + "% more."

      if less_waste_db == 0:
        less_waste_display = "If you've been throwing out less garbage than usual log it in the tracker so we can give you kudos."
      elif less_waste_db == 1:
        less_waste_display = "once"
      else:
        less_waste_db = str(less_waste_db)
        less_waste_display = less_waste_db + " times."

      # Format carbon offsets for display 
      if carbon_offset_db == 0:
        carbon_offsets = "If you have purchased any carbon offsets since starting, please log them to start tracking your progress here."
      else:
        carbon_offsets = float(carbon_offset_db)
        if carbon_offsets < 1000:
          carbon_offsets = str(carbon_offsets) + " kg of cO2"
        else:
          carbon_offsets = co2(carbon_offsets).replace("per year", "")
      
      # Format carbon savings for display  
      if float(carbon_savings_db) == 0:
        carbon_savings_display = "Please log a carbon saving activity to start tracking your progress here."
      else: 
        carbon_savings_display = float(carbon_savings_db)
        if carbon_savings_display > 1000:
          carbon_savings_display = co2(carbon_savings_display)
        else:
          carbon_savings_display = str(formatfloat(carbon_savings_display)) + " kg of c02"
      
      # Format fewer flights, direct flights and hotels
      if fewer_flights_db == 0:
        flights_display = "Please log an event in which you chose to take fewer flights to start tracking your progress here."
      else:
        flights_display = int(fewer_flights_db)

      if fewer_hotels_db == 0:
        hotels_saved_display = "If you spent fewer nights in hotels than you usually do please log that in the tracker so we can give you kudos."
      else: 
        hotels_saved_display = str(int(fewer_hotels_db)) + " fewer nights"
      
      if more_direct_flights_db == 0:
        direct_flights_display = "Please log an event in which you chose a direct flight so we can give you kudos."
      else:
        direct_flights_display = "A total of " + str(int(more_direct_flights_db)) + " direct flights" 

      if vacationed_local_db == 0: 
        local_vacations_display = "If you've taken local vacation days please let us know in tracker so we can give you kudos."
      elif vacationed_local_db == 0:
        local_vacations_display = "You've taken your first local vacation day. Here's to the start of getting to know your surroundings even better. We're sure you're going to discover some new hidden gems."
      else:
        vacationed_local_db = str(vacationed_local_db)
        local_vacations_display = "You've accumulated " + vacationed_local_db + " days so far. We'd love to know what treasures you've discovered."

      # Format bike walk miles
      if miles_walk_bike_db == 0:
        miles_display = "Please log a walk or cycle to start tracking your progress here."
      else: 
        miles_display = str(miles_walk_bike_db) + " miles"

      # Format total score: 
      if total_score_db == 0:
        display_score = "N/A"
      else:
        if "," in total_score_db:
          total_score_db = total_score_db.replace(",", "")
        display_score = formatfloat(float(total_score_db))

    return render_template("homeuser.html", challenges=challenge_completed, challengesdb=challenges_db, localvacations=local_vacations_display, savedwater=saved_water_display, solardisplay=solar_panel_display, greentariff=green_tariff_display,  locallegend=local_shopping, sustainableshopping=clothing_display, plastic=display_plastic, lesswaste=less_waste_display, addedfriends=display_friends, helpedout=helped_out, plantedtrees=display_planted_trees, totalscore=display_score, morerecycling=more_recycling_display, morecompost=more_compost_display, recyclingimpact=recycling_impact_display, landfillimpact=landfill_impact_display, recycling=recycling_display, totalwaste=waste_frequency_db, chickensub=chicken_less_display, porksub=pork_less_display, beefsub=beef_less_display, chicken=chicken_display, pork=pork_display, beef=beef_display, hotelsaved=hotels_saved_display, hotelnights=hotels_display, flightsdirect=direct_flights_display, flightsaved=flights_display, totalflights=total_flights, bikewalkmiles=miles_display, transportcost=transport_cost_db, energysaved=saved_energy_display, electricitydb=electricity_display, savings=saved_money_db, carbonsavings=carbon_savings_display, carbonoffsets=carbon_offsets, leaderboardname=leaderboardname, datetime=display_date, consumption=grand_total, formatted=number_in_consumption_footprint_total_db)

# Leaderboard page
@app.route("/leaderboard", methods=["GET", "POST"])
@login_required
def leaderboard():
  """Shows user how their consumption and actions rank compared to other users"""
  if request.method == "POST":
    # Need to redirect
    return redirect("/leaderboard")
  
  else: 
    # Check to see if user has answered the questions in the calculater, if not redirect them to the calculator
    check_footprint = db.execute("SELECT user_id FROM footprint WHERE user_id=?", session.get("user_id"))
    if len(check_footprint) == 0: 
      flash("Please calculate your carbon footprint to get started.")
      return redirect("/calculator")
    
    # Get Leaderboardname
    check_name = db.execute("SELECT leaderboardname FROM users WHERE id=?", session.get("user_id"))
    for item in check_name:
      leaderboardname = item['leaderboardname']

    # Get total carbon savings:
    carbon_savings_db = db.execute("SELECT carbon_savings FROM trackers")
    carbon_savings_total = 0
    for savings in carbon_savings_db:
      if savings['carbon_savings'] is not None:
        # carbon_savings_total = carbon_savings_list.append(savings['carbon_savings'])
        carbon_savings_total = carbon_savings_total + float(savings['carbon_savings'])
      else:
        carbon_savings_total = carbon_savings_total + 0
    
    # Format total carbon saved for display
    total_carbon_saved = (co2(float(carbon_savings_total))).replace("per year", "")

    # Get total comulative community money savings
    money_savings_total = db.execute("SELECT SUM(saved_money) FROM trackers")
    for item in money_savings_total:
      total_money_saved = item['sum']
    total_money_saved = total_money_saved

    # Get total comulative community plastic saved:
    plastic_saved = db.execute("SELECT sum(saved_plastic) FROM trackers")
    for item in plastic_saved: 
      total_plastic_saved = item['sum']

    # Get total cumulative water savings: 
    water_saved = db.execute("SELECT SUM(saved_water) FROM trackers")
    for item in water_saved:
      total_water_saved = item['sum']

    # Get total cumulative community green miles 
    miles_walked_biked = db.execute("SELECT SUM(miles_walk_bike) FROM trackers")
    for item in miles_walked_biked: 
      total_miles = item['sum']
    total_miles = str(total_miles)
    total_miles = total_miles + " miles"

    # Get total cumulative community flexitarian days
    less_beef_db = db.execute("SELECT sum(less_beef) FROM trackers")
    for item in less_beef_db:
      beef_flex = item["sum"]
    less_chicken_db = db.execute("SELECT sum(less_chicken) FROM trackers")
    for item in less_chicken_db:
      chicken_flex = item['sum']
    less_pork_db = db.execute("SELECT sum(less_pork) FROM trackers")
    for item in less_pork_db:  
      pork_flex = item['sum']
    total_flex = int(beef_flex) + int(chicken_flex) + int(pork_flex)
    total_flex = str(total_flex)
    total_flex = total_flex + " days"

    # Pull leaders from leaderboard in db
    leaders = db.execute("SELECT leaderboardname, challenges, total_points FROM leaderboard ORDER BY challenges DESC LIMIT 10")
    for leader in leaders: 
      leadingname = leader['leaderboardname']
      challenges = leader['challenges']
      totalpoints = formatfloat(float((str(leader['total_points'])).replace(",", "")))

    # Calculate user's current position (distance from the lead) and handle formatting
    find_leader = db.execute("SELECT leaderboardname, total_points FROM leaderboard ORDER BY total_points DESC LIMIT 1")
    max_points = 0
    for points in find_leader:
      max_points = points['total_points']
    you = db.execute("SELECT leaderboardname, total_points FROM leaderboard WHERE user_id=?", session.get("user_id"))
    temp_test = db.execute("SELECT leaderboardname, total_points FROM leaderboard WHERE user_id=?", session.get("user_id"))
    your_points = 0
    for points in temp_test: 
      your_points = float((str(points['total_points'])).replace(",", ""))
    if "," in max_points:
      max_points = max_points.replace(",", "")
    points_to_top = formatfloat(float(max_points) - your_points)
    your_points = formatfloat(your_points)
    return render_template("/leaderboard.html", yourpoints=your_points, pointstotop= points_to_top, leaders=leaders, leadingname=leadingname, challenges=challenges, totalpoints=totalpoints, flexitarian=total_flex, greenmiles=total_miles, dollarsavings=total_money_saved, carbonsavings=total_carbon_saved, leaderboardname=leaderboardname)

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

    # Check for email render apology
    if not request.form.get("email"):
      flash("Please enter your email")
      return render_template("/login.html")

    # Check for password if no password render apology
    elif not request.form.get("password"):
      flash("Please enter your password")
      return render_template("/login.html")
    
    email_in_db = db.execute("SELECT * FROM users WHERE email=?", request.form.get("email"))
    
    # Check to see if there is an account associated with that email 
    if len(email_in_db) == 0:
      flash("No account is associated with that email")
      return render_template("/login.html")
    
    for detail in email_in_db:
      emailadd = detail['email']
    len_email = len(email_in_db)
    password_hash = db.execute("SELECT * FROM users WHERE email=?", request.form.get("email"))
    password_check = check_password_hash(password_hash[0]["hash"], password)
    
    # Check email exists and password is correct
    if useremail != emailadd:
      flash("No account was found for that email")
      return render_template("/login.html")
    
    elif len(email_in_db) != 1 or not check_password_hash(email_in_db[0]["hash"], password):
      flash("Oops either your email or password are incorrect")
      return render_template("/login.html")

    # Remember which user has logged in
    session["user_id"] = email_in_db[0]["id"]
    return redirect("/homeuser")
  
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

    # Handle random username generator
    if goback is not None:
      return render_template("/register.html", randomname=random_leaderboard) 
    
    # Check name isn't blank
    if len(name) == 0:
      flash("Please enter your name")
      return render_template("/register.html", randomname=random_leaderboard) 
      # return apology("Please enter your name", 403)
    
    # Check email isn't blank
    if len(email) == 0:
      flash('Please enter your email addresss')
      return render_template("/register.html", randomname=random_leaderboard) 
      # return apology("Please enter your email")

    # Check if email is already in database
    email_check = email
    count = db.execute("SELECT count(email) FROM users WHERE email=?", email_check)
    for usermail in count:
      email_count = int(usermail['count'])
    if (email_count == 1):
      flash("I'm sorry an account is already registered for that email. Please go ahead and log in.")
      return render_template("/register.html", randomname=random_leaderboard) 
      # return apology("I'm sorry an account already exists for that email")

    # Check password isn't blank
    if password is None:
      flash("Oops! Password was blank. Please enter a password")
      return render_template("/register.html", randomname=random_leaderboard) 
      # return apology("Oops! Password cannot be blank", 403)
    
    if confirmation is None:
      flash("Confirmation is blank, please enter a confirmation of your chosen password")
      return render_template("/register.html", randomname=random_leaderboard) 
      # return apology("Confirmation is blank")
    
    # Check password and confirmation match
    if password != confirmation:
      flash("Oops! Your passwords don't match. Please try again.")
      return render_template("/register.html", randomname=random_leaderboard) 
      # return apology("Oops! Your passwords don't match", 403)
    
    elif len(password) < 8:
      flash("Passwords should be at least characters long to help keep your account secure. Please try again.")
      return render_template("/register.html", randomname=random_leaderboard) 
      # return apology("Password should be at least 8 char long for your security")

    # Check leaderboard name isn't blank
    if len(leaderboardname) == 0:
      flash("Please choose a leaderboard name. Our random leaderboardname is there to give you inspiration.")
      return render_template("/register.html", randomname=random_leaderboard) 
      # return apology("Please choose a leaderboard name", 403)
    
    # Check leaderboard name is unique
    leaderboard_check = db.execute("SELECT * FROM users WHERE leaderboardname=?", request.form.get("leaderboardname"))
    leaderboard_name_check = ""
    for name in leaderboard_check:
      leaderboard_name_check = name['leaderboardname'] 
    
    if len(leaderboard_name_check) != 0:
      flash("Oops, that leaderboard name has already been claimed. Try our random leaderboard name generator for more ideas.")
      random_name = random_leaderboardname()
      leaderboard_check = db.execute("SELECT * FROM users WHERE leaderboardname=?", random_name)
      leaderboard_suggestion = ""
      
      while len(leaderboard_check) !=0: 
        leaderboard_suggestion = random_leaderboardname
        if leaderboard_suggestion:
          flash("Oops, that leaderboard name has already been claimed. Try our random leaderboard name generator for more ideas.")
          return render_template("/register.html", randomname=leaderboard_suggestion)
        else:
          return render_template("/register.html", randomname=random_name)
    
    else:
      # Generate a hash to store in db and insert user info into db
      hash = generate_password_hash(request.form.get("password"), method="pbkdf2:sha256", salt_length=8)
      new_user = db.execute("INSERT INTO users (name, email, leaderboardname, hash) VALUES(?, ?, ?, ?)", name, email, leaderboardname, hash)
      check_db_new_user = db.execute("SELECT * FROM users WHERE id=?", session.get("user_id"))
      
      # Update Trackers with user info
      find_id = db.execute("SELECT id FROM users WHERE leaderboardname=?", leaderboardname)
      for id in find_id:
        get_id = id['id']
      green_tariffs = "No"
      solar_panels = "No"
      set_tracker_scores_db = db.execute("INSERT INTO trackers (user_id, added_friends, planted_trees, helped_community, vintage_clothing, sustainable_clothing, saved_plastic, saved_money, saved_energy, bought_local, vacationed_local, less_beef, less_chicken, less_pork, more_compost, green_tariff, solar_panels, saved_water, less_waste, more_recycling, fewer_flights, fewer_hotels, more_direct_flights, miles_walk_bike, carbon_offset, carbon_savings, total_score) VALUES(?, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, ?, ?, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)", get_id, green_tariffs, solar_panels)
      check_tracker_scores = db.execute("SELECT * FROM trackers WHERE user_id=?", session.get("user_id"))

      # Add user to the leaderboard 
      join_leaderboard = db.execute("INSERT INTO leaderboard (user_id, leaderboardname, challenges, green_miles, carbon_saved, plastic_saved, total_points) VALUES(?, ?, 0, 0, 0, 0, 0)", get_id, leaderboardname)

      # Add user to challenges table
      join_challenges = db.execute("INSERT into challenges (user_id, leaderboardname, challenge, pledge) VALUES(?, ?, 'None Accepted', 0)", get_id, leaderboardname)
      return render_template("/login.html")

  # Handle GET request 
  else:
    return render_template("/register.html", randomname=random_leaderboard)

# Reset password page
@app.route("/reset", methods=["GET", "POST"])
def reset():
  """Allows user to reset password"""
  # Using SendGrid to reset users' passwords and send them a random temporary password
  # https://docs.sendgrid.com/for-developers/sending-email/quickstart-python
  
  if request.method == "POST":
    flash("Please Check Your Email, if you don't see one from us please check your spam folder and then add us to your address book.")
    email = request.form.get("email")
    
    # Check that person is in fact in db
    account_check = db.execute("SELECT * FROM users WHERE email=?", email)
    if len(account_check) == 0:
      return apology("We don't have an account associated with this email.")
    
    # Handle reset password
    else:
      flash("Please check your email for a temporary password.")
      # Generate random password from helpers
      temp_password = generate_temp_password()

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
      return redirect("/login")
  else: 
    flash("Oopsie, it happens, we can help you with that.")
  return render_template("/reset.html")

# Results page user sees after quiz
@app.route("/results", methods=["GET", "POST"])
@login_required
def results():
  """Shows user the results from their carbon footprint quiz"""
  if request.method == "POST":
    # Reroute to get
    return render_template("/results.html")
  else:
    # Get user from sessions
    user = session.get("user_id")
    
    # Get footprint scores from db
    total_footprint_general_formatted = 0
    total_footprint_general = ""
    db_footprint = db.execute("SELECT * FROM footprint WHERE user_id=?", session.get("user_id"))
    
    # Pull data from returned list of dictionaries from db
    for score in db_footprint: 
      building = score['building']
      if building == "construction-type_multifamily_residential_structures":
        building_type = "Multi-family building / apartment"
      else:
        building_type = "Single-family home"
      
      impact_of_construction = float(score['building_impact'])
      state = score['state']
      electricity = score['electricity']

      # Format scores into a 2 decimal float and remove additional wording displayed in db
      electricity_impact = formatfloat(float(score['electricity_impact']))
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
      individual_score_formatted = co2(individual_score * 1000) 
    elif "ton of cO2 per year" in total_footprint_general:
      individual_score = ((float(total_footprint_general.replace("ton of cO2 per year", ""))) / (int(household_occupants)))
      individual_score_formatted = co2(individual_score * 1000)
    
    if "tons of cO2 per year" in total_footprint_general:
      total_footprint_general_formatted = co2(float(total_footprint_general.replace("tons of cO2 per year", "")) * 1000)
      impact_of_construction_formatted = co2lifetime(impact_of_construction)
      drycleaning_formatted = "{:.2f}".format(drycleaning_spend)
    elif "ton of cO2 per year" in total_footprint_general:
      total_footprint_general_formatted = co2(float(total_footprint_general.replace("ton of cO2 per year", "")) * 1000)
      impact_of_construction_formatted = co2lifetime(impact_of_construction)
      drycleaning_formatted = "{:.2f}".format(drycleaning_spend)

    # Get transport footprint scores from db and format 
    db_transport = db.execute("SELECT * FROM transport_footprint WHERE user_id=?", user)
    for score in db_transport:
      work_situation = score['work_situation']
      commuter_days = score['commuter_days']
      commuter_distance = score['commuter_distance']
      
    transport_mode = score['transport_mode']
    if transport_mode == "passenger_vehicle-vehicle_type_pickup_trucks_vans_suvs-fuel_source_na-engine_size_na-vehicle_age_na-vehicle_weight_na":
      mode_of_transport = "SUV / Pickup Truck / Van"
    elif transport_mode == "passenger_vehicle-vehicle_type_car-fuel_source_na-engine_size_na-vehicle_age_na-vehicle_weight_na": 
      mode_of_transport = "Gas Vehicle"
    elif transport_mode == "passenger_train-route_type_urban-fuel_source_na":
      mode_of_transport = "Subway / Tram"
    elif transport_mode == "passenger_train-route_type_intercity-fuel_source_na":
      mode_of_transport = "Intercity Amtrak"
    elif transport_mode == "passenger_vehicle-vehicle_type_bus-fuel_source_na-distance_na-engine_size_na":
      mode_of_transport = "Bus"
    elif transport_mode == "passenger_vehicle-vehicle_type_motorcycle_bicycle_parts-fuel_source_na-engine_size_na-vehicle_age_na-vehicle_weight_na":
      mode_of_transport = "Bicycle"
    elif transport_mode == "passenger_vehicle-vehicle_type_boat-fuel_source_na-engine_size_na-vehicle_age_na-vehicle_weight_na":
      mode_of_transport = "Ferry"
    else: 
      mode_of_transport = "Motorcycle"
        
    transport_cost = float(score['transport_cost']) * 1.00
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
      commuter_days = str(commuter_days) + " days of the week"
    else:
      commuter_days = str(commuter_days) + " day of the week"

    # Get consumption footprint scores from db
    hotels_add = 0
    appliances_add = 0
    accessories_add = 0

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
        pork_consumption = str(pork_consumption) + " time"
      pork_impact = co2(float(score['pork_impact']))
      pork_add = float(score['pork_impact'])

      chicken_consumption = int(score['chicken_consumption'])
      if chicken_consumption > 1:
        chicken_consumption = str(chicken_consumption) + " times"
      else:
        chicken_consumption= str(chicken_consumption) + "time"
      chicken_impact = co2(float(score['chicken_impact']))
      chicken_add = float(score['chicken_impact'])

      willingness_to_adjust_diet = (score['dietary_attitude']).replace("_", " ")
      new_clothing_spend = score['new_clothes']

      # Manage empty fields in clothing
      if new_clothing_spend == "No info given":
        new_clothing_spend = score['new_clothes']
        new_clothing_impact = "Unknown, we need more information from you to calculate this."
        new_clothing_add = 0
      else:
        new_clothing_spend = "$" + formatfloat(float(score['new_clothes'])) 
        new_clothing_impact = co2(float(score['new_clothes_impact']))
        if "tons of cO2 per year" in new_clothing_impact:
          new_clothing_add = float(new_clothing_impact.replace("tons of cO2 per year", ""))
        else:
          new_clothing_add = float(new_clothing_impact.replace("ton of cO2 per year", ""))

      # Manage empty fields in restaurants:
      restaurants_spend = score['restaurants']
      restaurants_impact = ""
      restaurants_add = 0
      if restaurants_spend == "No info given":
        restaurants_spend = "No info given"
        restaurants_impact = "Unknown, we need more information from you to calculate this."
        restaurants_add = 0
      else:
        restaurants_spend = "$" + formatfloat(float(restaurants_spend))
        restaurants_impact = co2(float(score['restaurants_impact']))
        if "tons of cO2 per year" in restaurants_impact:
          restaurants_add = restaurants_impact.replace("tons of cO2 per year", "")
          restaurants_add = float(restaurants_add)
        else:
          restaurants_add = restaurants_impact.replace("ton of cO2 per year", "")
          restaurants_add = float(restaurants_add)
        
      # Manage empty fields in accessories and format 
      accessories_spend = score['accessories']
      if accessories_spend == "No info given":
        accessories_spend = "No info given"
        accessories_impact = "Unknown, we need more information to calculate this."
        accessories_add = 0
      else:
        accessories_spend = "$" + format(float(accessories_spend))
        accessories_impact = co2(float(score['accessories_impact']))
        accessories_add = accessories_impact
        
        if "tons of cO2 per year" in accessories_impact:
          accessories_add = float(accessories_impact.replace("tons of cO2 per year", ""))
        else:
          accessories_add = float(accessories_impact.replace("ton of cO2 per year", ""))

      # Manage empty fields in appliances and format
      appliances_spend = score['appliances']
      appliances_add = 0
      if appliances_spend == "No info given":
        appliances_spend = "No info given"
        appliances_impact = "Unknown, we need more information to calculate this."
        appliances_add = 0
      else:
        appliances_spend = "$" + format(float(appliances_spend))
        appliances_impact = co2(float(score['appliances_impact']))
        if "tons of cO2 per year" in appliances_impact:
          appliances_add = float(appliances_impact.replace("tons of cO2 per year", ""))
        else:
          appliances_add = float(appliances_impact.replace("ton of cO2 per year", ""))

      # Manage empty fields in hotels and format
      hotels = score['hotels']
        
      if hotels == "No info given":
        hotels = "No info given"
        hotels_impact = "Unknown, we need more information to calculate this."
        hotels_add = 0
      else:
        hotels = int(hotels)
        hotels_add = hotels
        hotels_impact = co2(float(score['hotels_impact']))
        
        if "tons of cO2 per year" in hotels_impact:
          hotels_add = float(hotels_impact.replace("tons of cO2 per year", ""))
        else:
          hotels_add = float(hotels_impact.replace("ton of cO2 per year", ""))

    total_footprint_consumption = hotels_add + appliances_add + accessories_add + restaurants_add + new_clothing_add + beef_add + chicken_add + pork_add
    date_completed = score['datetime']
    date_completed = date_completed[:11]

    # Format General Footprint for sum of scores, handle formatting
    sum_total_footprint_general = total_footprint_general
    if "tons of cO2 per year" in total_footprint_general:
      sum_total_footprint_general = float(total_footprint_general.replace("tons of cO2 per year", "")) * 1000
    elif "ton of cO2 per year" in total_footprint_general:
      sum_total_footprint_general = float(total_footprint_general.replace("ton of cO2 per year", "")) * 1000
    else:
      print("This is an error in results you need to look at")

    # Format Transport Footprint for sum and handle formatting from db
    sum_total_footprint_transport = total_footprint_transport
    if "tons of cO2 per year" in total_footprint_transport:
      sum_total_footprint_transport = float(total_footprint_transport.replace("tons of cO2 per year", "")) * 1000
    elif "ton of cO2 per year" in total_footprint_transport:
      sum_total_footprint_transport = float(total_footprint_transport.replace("ton of cO2 per year", "")) * 1000
    else:
      print("This is an error in results you need to look at")

    # Format Consumption Footprint for sum
    sum_total_footprint_consumption = float(total_footprint_consumption)
    total = sum_total_footprint_general + sum_total_footprint_transport + sum_total_footprint_consumption
    grand_total = co2(total)
    total_footprint_consumption = co2(float(total_footprint_consumption))

    # Return template with elements to display in jinja template
    return render_template("/results.html", total=grand_total, datetime=date_completed, household=total_footprint_general, transport=total_footprint_transport, consumption=total_footprint_consumption, building=building_type, buildingimpact=impact_of_construction_formatted, state=state, electricity=electricity, electrictyimpact=electricity_impact, wastefrequency=waste_frequency, landfill=landfill_impact, recycling=recycling, recyclingimpact=recycling_impact, drycleaning=drycleaning_formatted, drycleaningimpact=drycleaning_impact, totalfootprint=total_footprint_general_formatted, individualfootprint=individual_score_formatted, worksituation=work_situation, commuterdays=commuter_days, commuterdistance=commuter_distance, transportmode=mode_of_transport, transportcost=transport_cost, commuterimpact=impact_of_commute, shorthaul=short_haul_flights, shorthaulimpact=short_haul_flights_impact, mediumhaul=medium_haul_flights, mediumhaulimpact=medium_haul_flights_impact, longhaul=long_haul_flights, longhaulimpact=long_haul_flights_impact, totaltransportfootprint=total_footprint_transport_formatted, beef=beef_consumption, beefimpact=beef_impact, pork=pork_consumption, porkimpact=pork_impact, chicken=chicken_consumption, chickenimpact=chicken_impact, willingness=willingness_to_adjust_diet, newclothing=new_clothing_spend, newclothingimpact=new_clothing_impact, restaurants=restaurants_spend, restaurantsimpact=restaurants_impact, accessories=accessories_spend, accessoriesimpact=accessories_impact, appliances=appliances_spend, appliancesimpact=appliances_impact, hotels=hotels, hotelsimpact=hotels_impact, totalconsumptionfootprint=total_footprint_consumption)

# Tracker page to track carbon footprint
@app.route("/trackercommunity", methods=["GET", "POST"])
@login_required
def trackercommunity():
  """Allows user to track their progress"""
  if request.method == "POST":

    # Get relevant info from DB
    get_db = db.execute("SELECT added_friends, planted_trees, helped_community, total_score FROM trackers WHERE user_id=?", session.get("user_id"))

    # Extract fields from list of dictionaries returned by db
    for info in get_db:
      added_friends = info['added_friends']
      planted_trees = info['planted_trees']
      helped_community = info['helped_community']
      total_score = info['total_score']

    # Get values from forms in template:
    friends = request.form.get("added_friend")
    trees = request.form.get("planted_trees")
    community_garden = request.form.get("community_garden")
    mentor = request.form.get("mentor")
    
    # Manage empty fields and tally score 
    if friends is None:
      friends_add = 0
    else:
      friends_add = int(friends)
    if trees is None:
      trees_add = 0
    else:
      trees_add = int(trees)
    if community_garden is None:
      community_garden_add = 0
    else: 
      community_garden_add = int(community_garden)
    if mentor is None: 
      mentor_add = 0
    else: 
      mentor_add = int(mentor)
    
    # Set new totals:
    friends_total = int(added_friends) + friends_add
    trees_total = int(planted_trees) + trees_add
    community_total = int(helped_community) + community_garden_add + mentor_add
    if "," in total_score:
      total_score = total_score.replace(",", "")
    new_total_score = float(total_score) + friends_total + trees_total + community_total

    # Update Tracker DB: 
    update_db = db.execute("UPDATE trackers SET added_friends=?, planted_trees=?, helped_community=?, total_score=? WHERE user_id=?", friends_total, trees_total, community_total, new_total_score, session.get("user_id"))
    updated_db = db.execute("SELECT * FROM trackers WHERE user_id=?", session.get("user_id"))

    # Update leaderboard DB:
    lookup_total_points = db.execute("SELECT total_points FROM leaderboard WHERE user_id=?", session.get("user_id"))
    old_points = 0
    for point in lookup_total_points: 
      old_points = point['total_points']
    if "," in old_points:
      old_points = old_points.replace(",", "")
    new_score = new_total_score
    update_leaderboard = db.execute("UPDATE leaderboard SET total_points=? WHERE user_id=?", new_score, session.get("user_id"))
    
    return render_template("/trackercommunity.html")
  else:
    print("This is an error in the tracker community route you should look at")
  return render_template("/trackercommunity.html")

@app.route("/trackerelectricity", methods=["GET", "POST"])
@login_required
def trackerelectricity():
  """Allows user to track their progress"""
  if request.method == "POST":
    # Notify user a change has been made
    flash("😀 Would you like to track something else? To see updates to your score please visit your home page.")

    # Get benchmark values from db: 
    get_db_electricity = db.execute("SELECT state, electricity, electricity_impact, waste_frequency, recycling FROM footprint WHERE user_id=?", session.get("user_id"))
    for info in get_db_electricity:
      energy_usage_db = float(info['electricity'])
      waste_frequency = int(info['waste_frequency'])
      recycling_amount = float(info['recycling'])
      state = info['state']

      # Adjust from yearly electricity estimations to monthly (stored as yearly in db)
      previous_emissions = float(formatfloat(float(info['electricity_impact']) / 12))

    # Get tracker info from db and extract elements:
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

    # Get values from form on template
    reduced_utility_bill = request.form.get("reduced_utility_bill")
    composting = request.form.get("composting")
    green_tariff = request.form.get("green_tariff")
    solar_panels = request.form.get("solar_panels")
    short_shower = request.form.get("short_shower")
    saved_electricity = request.form.get("saved_electricity")
    print("Saved Electricity From Form: ", saved_electricity)
    less_plastic = request.form.get("less_plastic")
    less_waste = request.form.get("less_waste")
    more_recycling = request.form.get("more_recycling")
    
    # Handle empty fields and calculate adds for utility bill and carbon savings
    if reduced_utility_bill is None:
      energy_savings_add = 0
      carbon_savings_utilities = 0
      electricity_emissions = 0
    else:
      reduced_utility_bill = float(reduced_utility_bill)

      # Handle cases where users either used more electricity than normal or the same amount
      if reduced_utility_bill > energy_usage_db:
        flash("You used more electricity than usual this month.")
        energy_savings_add = 0
        carbon_savings_utilities = 0
        electricity_emissions = 0
      elif reduced_utility_bill == energy_usage_db:
        flash("You used the same amount of electricity as usual.")
        energy_savings_add = 0
        carbon_savings_utilities = 0
        electricity_emissions = 0
      else:
        # Calculate points for energy savings 
        energy_savings_add = (energy_usage_db - reduced_utility_bill)
        electricity_lookup = impact_by_energy(electricity_activity_id, region, reduced_utility_bill)
        electricity_emissions = float(formatfloat(float(electricity_lookup['Carbon_emissions'])))
        carbon_savings_utilities = float(formatfloat(previous_emissions - electricity_emissions))

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
      if green_tariff_status == "Yes":
        points_for_going_green = 0
      else:
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
      if solar_panels_status == "Yes":
        points_for_solar_panels = 0
      else:
        solar_panels_status = "Yes"
        points_for_solar_panels = 20
    
    # Short shower
    if short_shower is None:
      water_savings_add = 0
    else: 
      # HACK:
      # Average shower uses 2.5 Gallons of water per minute https://green.harvard.edu/tools-resources/green-tip/4-ways-measure-5-minute-shower#:~:text=Did%20you%20know%20the%20average,water%20for%20the%20average%20shower!
      water_savings_add = float(short_shower) * 2.5
    
    # Electricity savings from bulbs
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
      # Offered the user double points for this - add to score
      added_points_bulbs = 2
      money_savings_add_bulbs = (float((3.05 - 1.34) * (saved_electricity))) 
      
      
      # Estimating savings of 50 watts per hour from switching to LED the equivalent in kWh
      # kWh=(watts * hrs) / 1,000 https://justenergy.com/blog/kilowatts-and-calculations/#:~:text=Here's%20the%20Formula%20for%20Calculating,watts%20%C3%97%20hrs)%20%C3%B7%201%2C000
      energy_savings_add_bulbs = (50 * saved_electricity) / 1000
      carbon_savings_lookup = impact_by_energy(electricity_activity_id, region, energy_savings_add)
      carbon_savings_bulbs = (float(carbon_savings_lookup['Carbon_emissions'])) + 2
    
    # Calculate scores for using less Less plastic and handle empty values
    if less_plastic is None:
      less_plastic_add = 0
    else:
      less_plastic_add = float(less_plastic)
    
    # Calculate scores for generating less waste and handle empty values
    # Handle cases where users used more than usual or the same amount
    if less_waste is None: 
      less_waste_add = 0
    else: 
      if float(less_waste) > float(waste_frequency) or float(less_waste) == float(waste_frequency):
        flash("That's the same amount or more than you usually throw out")
        less_waste_add = 0
      else:
        less_waste_add = float(less_waste)
    
    # Calculate scores for recycling more of their waste and handle empty values
    # Handle cases where users did not recycle more than usual or the same amount
    if more_recycling is None:
      more_recycling_add = 0
    else: 
      if float(more_recycling) < float(recycling_amount) or float(more_recycling) == float(recycling_amount):
        flash("That's less or the same amount than you usually recycle.")
        more_recycling_add = 0
      else:
        more_recycling_add = float(more_recycling) / 100
    
    # Tally up totals and manage formatting
    energy_savings_total = float(energy_savings) + energy_savings_add + energy_savings_add_bulbs
    carbon_savings_total = formatfloat(float(carbon_savings) + carbon_savings_utilities + carbon_savings_bulbs)
    if "$" in monetary_savings:
      monetary_savings = (monetary_savings.replace("$", "")).replace(",", "")
    money_savings_total = formatfloat(float(monetary_savings) + money_savings_add_bulbs)
    compost_new_total = int(float(compost_total) + composting_add)
    green_tariff_status_end = green_tariff_status
    solar_panels_status_end = solar_panels_status
    water_savings_total = float(water_savings) + water_savings_add
    plastic_savings = int(float(saved_plastic) + less_plastic_add)
    total_waste_savings = float(less_waste_total) + float(less_waste_add)
    total_recycling_score = float(more_recycling_total) + more_recycling_add
    if "," in db_total_score:
      db_total_score = db_total_score.replace(",", "")
    starting_score = float(db_total_score)
    stuff_to_add = energy_savings_add + energy_savings_add_bulbs + carbon_savings_bulbs + carbon_savings_utilities + composting_add + money_savings_add_bulbs + points_for_going_green + points_for_solar_panels + water_savings_add + less_plastic_add + less_waste_add + more_recycling_add + added_points_bulbs
    new_added_score =  energy_savings_add + energy_savings_add_bulbs + carbon_savings_utilities + carbon_savings_bulbs + money_savings_add_bulbs + composting_add + points_for_going_green + points_for_solar_panels + water_savings_add + less_plastic_add + less_waste_add + more_recycling_add
    new_total_score = formatfloat(float(db_total_score) + new_added_score)
   
    # Update db with scores
    updatedb = db.execute("UPDATE trackers SET saved_plastic=?, saved_money=?, saved_energy=?, more_compost=?, green_tariff=?, solar_panels=?, saved_water=?, less_waste=?, more_recycling=?, carbon_savings=?, total_score=? WHERE user_id=?", plastic_savings, money_savings_total, energy_savings_total, compost_new_total, green_tariff_status_end, solar_panels_status_end, water_savings_total, total_waste_savings, total_recycling_score, carbon_savings_total, new_total_score, session.get("user_id"))
    
    # Look up leaderboard scores 
    lookup_total_points = db.execute("SELECT carbon_saved, plastic_saved, total_points FROM leaderboard WHERE user_id=?", session.get("user_id"))
    
    # Extract values from leaderboard 
    lb_old_points = 0
    lb_carbon_savings = 0
    lb_plastic_saved = 0
    for point in lookup_total_points: 
      lb_carbon_savings = point['carbon_saved']
      lb_plastic_saved = point['plastic_saved']
      lb_old_points = point['total_points']
    lb_new_carbon_savings = carbon_savings_total
    lb_new_plastic_savings = plastic_savings
    lb_new_score = new_total_score

    # Update LB with new scores
    lb_update = db.execute("UPDATE leaderboard SET carbon_saved=?, plastic_saved=?, total_points=? WHERE user_id=?", lb_new_carbon_savings, lb_plastic_saved, lb_new_score, session.get("user_id"))
    
    return render_template("/trackerelectricity.html", garbage=waste_frequency, recycling=recycling_amount, kwh=energy_usage_db)
  else:

    # Get electricity metrics from db
    get_db_electricity = db.execute("SELECT electricity, waste_frequency, recycling FROM footprint WHERE user_id=?", session.get("user_id"))

    # Extract values from db
    for info in get_db_electricity:
      energy_usage_db = info['electricity']
      waste_frequency = info['waste_frequency']
      recycling_amount = info['recycling']
    energy_usage = int(float(energy_usage_db))

  return render_template("/trackerelectricity.html", garbage=waste_frequency, recycling=recycling_amount, kwh=energy_usage)

@app.route("/trackershopping", methods=["GET", "POST"])
@login_required
def trackershopping():
  """Allows user to track their progress"""
  if request.method == "POST":
    
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
      restaurants_spend = "When you got started you said you were spending $" + restaurants + " each month. How much did you spend this month?"
      
    if accessories == "No info given":
      accessories_spend = "You didn't mention when you started how much you were spending on accessories. You can update that at any point. How much did you spend this month?"
    else:
      accessories_spend = "When you got started you said you were spending $" + accessories + " each month. How much did you spend this month?"
      
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

    # Set region for calculations:
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
      # Points awarded for the percentage of groceries bough locally (10%) so as not to inflate scores too quickly
      local_points = float(local_groceries) / 10

    # Calculate how many fewer times each meat was consumed, and carbon savings
    carbon_savings_chicken = 0
    carbon_savings_beef = 0
    carbon_savings_pork = 0
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
      
      # Get Price estimates from calculator 
      beef_price = 5.12 / 2
      chicken_prices = (1.87 / 2) 
      pork_prices = [1.21, 11.21, 9.64, 11.26, 8.89, 9.04, 16.22, 9.56, 8.20, 7.92, 8.83, 9.04, 8.79, 8.76, 11.25]
      sum_pork_prices = sum(pork_prices)
      average_pork_prices = sum(pork_prices) / len(pork_prices)

      # Handle cases where users ate more of any type than usual
      # If users consumed less calculate how much less and what their carbon savings are
      if beef > beef_consumption_weekly or beef == beef_consumption_weekly:
        less_beef_add = 0
        carbon_savings_beef = 0
        flash("This was the same amount or more beef than you normally eat.")
        if chicken > chicken_consumption_weekly or chicken == chicken_consumption_weekly:
          less_chicken_add = 0 
          carbon_savings_chicken = 0
          flash("This was the same amount or more chicken than you normally eat.")
          if pork > pork_consumption_weekly or pork == pork_consumption_weekly:
            less_pork_add = 0
            carbon_savings_pork = 0
            flash("This was the same amount or more pork than you normally eat.")  
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

    # Handle empty fields and work out scores and carbon savings if users spent less money on dry cleaning this month
    # Handle cases where users spent more money on dry cleaning this month 
    if drycleaning_form is None: 
      drycleaning_savings = 0
      carbon_savings_drycleaning = 0
    else: 
      drycleaning_form = float(drycleaning_form)
      if drycleaning_form > float(drycleaning_spend_db) or drycleaning_form == float(drycleaning_spend_db):
        flash("Oops you it looks like you didn't save on drycleaning this month.")
        drycleaning_savings = 0
        carbon_savings_drycleaning = 0
      else:
        drycleaning_savings = float(drycleaning_spend_db) - drycleaning_form
        # Get dry cleaning values from calculator to work out impact
        drycleaning_activity_id = "consumer_goods-type_dry_cleaning_laundry"
        drycleaning_lookup = impact_by_money(drycleaning_activity_id, region, drycleaning_savings)
        carbon_savings_drycleaning = drycleaning_lookup['Carbon_emissions']
    
    # Handle empty fields and calculate savings from users spending less on restaurants this month
    # Handle cases where users spent more than usual on restaurants
    if restaurants_form is None: 
      restaurants_savings = 0
      carbon_savings_restaurants = 0
    else:
      # Information from calculator needed to calculate impact
      restaurants_activity_id = "consumer_services-type_full_service_restaurants"
      if restaurants == "No info given":
        restaurants = 0
        restaurants_savings = 0
        carbon_savings_restaurants = 0
      else: 
        restaurants_form = float(restaurants_form)
        restaurants = float(restaurants)
        if restaurants_form > restaurants or restaurants_form == restaurants:
          flash("Oops looks like you didn't save on restaurants this month.")
          restaurants_savings = 0
          carbon_savings_restaurants = 0
        else: 
          restaurants_savings = restaurants - restaurants_form
          restaurants_lookup = impact_by_money(restaurants_activity_id, region, restaurants_savings)
          carbon_savings_restaurants = restaurants_lookup['Carbon_emissions']
    
    # Handle empty fields and calculate savings from users spending less accessories this year
    # Handle cases where users spent more than usual on accessories this year
    if accessories_form is None: 
      accessories_savings = 0
      carbon_savings_accessories = 0
    else: 
      if accessories == "No info given":
        accessories = 0
        accessories_savings = 0
        carbon_savings_accessories = 0
      else:
        accessories_activity_id = "consumer_goods-type_clothing_clothing_accessories_stores"
        accessories = float(accessories) 
        accessories_form = float(accessories_form)
        if accessories_form > accessories or accessories_form == accessories:
          flash("Looks like you actually spent the same amount or more than usual on accessories.")
          accessories_savings = 0
          carbon_savings_accessories = 0
        else: 
          accessories_savings = accessories - accessories_form
          accessories_lookup = impact_by_money(accessories_activity_id, region, accessories_savings)
          carbon_savings_accessories = accessories_lookup['Carbon_emissions']

    # Tally totals based on previous values in trackers form
    get_db_tracker = db.execute("SELECT vintage_clothing, sustainable_clothing, saved_plastic, saved_money, bought_local, less_beef, less_chicken, less_pork, carbon_savings, total_score FROM trackers WHERE user_id=?", session.get("user_id"))
    # Extract elements from list of dictionaries returned by db and handle formatting
    for info in get_db_tracker: 
      vintage_clothes = info['vintage_clothing']
      sustainable_clothes = info['sustainable_clothing']
      saved_plastic = info['saved_plastic']
      saved_money = (info['saved_money']).replace("$", "")
      bought_local = info['bought_local']
      less_beef = info['less_beef']
      less_chicken = info['less_chicken']
      less_pork = info['less_pork']
      carbon_savings_db = info['carbon_savings']
      total_score = info['total_score']
    
    # Tally totals and handle formatting issues for values over 1,000
    vintage_clothes_total = int(vintage_clothes) + vintage_clothes_add
    sustainable_clothes_total = int(sustainable_clothes) + sustainable_clothes_add
    saved_plastic_total = int(saved_plastic) + plastic_saved_by_paper + plastic_saved_by_reusable
    if "," in saved_money:
      saved_money = saved_money.replace(",", "")
    saved_money_total = formatfloat(float(saved_money) + float(money_savings_plastic) + float(drycleaning_savings) + float(accessories_savings) + float(restaurants_savings))
    bought_local_total = int(bought_local) + local_points
    new_beef_total = int(less_beef) + less_beef_add
    new_chicken_total = int(less_chicken) + less_chicken_add
    new_pork_total = int(less_pork) + less_pork_add
    if "," in carbon_savings_db:
      carbon_savings_db = carbon_savings_db.replace(",", "")
    carbon_savings_total = float(carbon_savings_db) + carbon_savings_beef + carbon_savings_chicken + carbon_savings_pork + carbon_savings_drycleaning + carbon_savings_restaurants + carbon_savings_accessories
    if "," in total_score:
      total_score = total_score.replace(",", "")
    new_total_score = formatfloat(float(total_score) + vintage_clothes_add + sustainable_clothes_add + plastic_saved_by_paper + plastic_saved_by_reusable + local_points + less_beef_add + less_chicken_add + less_pork_add + carbon_savings_beef + carbon_savings_chicken + carbon_savings_pork + money_savings_plastic + drycleaning_savings + accessories_savings)
    
    # Update DB with new scores
    update_db = db.execute("UPDATE trackers SET vintage_clothing=?, sustainable_clothing=?, saved_plastic=?, saved_money=?, bought_local=?, less_beef=?, less_chicken=?, less_pork=?, carbon_savings=?, total_score=? WHERE user_id=?", vintage_clothes_total, sustainable_clothes_total, saved_plastic_total, saved_money_total, bought_local_total, new_beef_total, new_chicken_total, new_pork_total, carbon_savings_total, new_total_score, session.get("user_id"))
    check_db = db.execute("SELECT vintage_clothing, sustainable_clothing, saved_plastic, saved_money, bought_local, less_beef, less_chicken, less_pork, carbon_savings, total_score FROM trackers WHERE user_id=?", session.get("user_id")) 
    print("Check DB after totals: ", check_db)
    
    # Update LB with new scores
    get_lb_score = db.execute("SELECT carbon_saved, plastic_saved, total_points FROM leaderboard WHERE user_id=?", session.get("user_id"))
    
    # Extract elements from list of dictionaries returned by db and handle formatting
    lb_old_score = 0
    lb_carbon_savings = 0
    lb_plastic_savings = 0
    for score in get_lb_score:
      lb_carbon_savings = score['carbon_saved']
      if "," in lb_carbon_savings:
        lb_carbon_savings = lb_carbon_savings.replace(",", "")
      lb_plastic_savings = score['plastic_saved']
      lb_old_score = str(score['total_points'])
      if "," in lb_old_score:
        lb_old_score = lb_old_score.replace(",", "")
      if "," in new_total_score:
        new_total_score = new_total_score.replace(",", "")
      if "," in total_score:
        total_score = total_score.replace(",", "")
    
    # Tally new LB totals and add to db
    new_lb_score = formatfloat(float(lb_old_score) + float(new_total_score) - float(total_score))
    new_lb_carbon_savings = carbon_savings_total
    new_lb_plastic = formatfloat(float(lb_plastic_savings) + plastic_saved_by_paper + plastic_saved_by_reusable)
    update_lb_total_points = db.execute("UPDATE leaderboard SET carbon_saved=?, plastic_saved=?, total_points=? WHERE user_id=?", new_lb_carbon_savings, new_lb_plastic, new_lb_score, session.get("user_id"))
    flash("😀 Would you like to track something else? To see updates to your score please visit your home page.")
    return render_template("/trackershopping.html", dietaryattitude=dietary_attitude, beefconsumption = beef_consumption, chickenconsumption=chicken_consumption, porkconsumption=pork_consumption, drycleaningspend=drycleaning_spend_db, restaurantsspend=restaurants_spend, accessories=accessories_spend)
  
  # Handle GET request
  else:
    check_footprint = db.execute("SELECT * FROM footprint WHERE user_id=?", session.get("user_id"))
    # Check to see if user has calculated their footprint yet, if not redirect to the calculator to start
    if len(check_footprint) == 0:
      flash("Please calculate your carbon footprint to start")
      return redirect("/calculator")
    
    # Get and display information from db
    else:
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
      
      # Handle cases where no information was given initially for spending on restaurants, accessories
      if restaurants == "No info given":
        restaurants_spend = "You didn't mention when you started how much you were spending on restaurants. You can update that at any point. How much did you spend this month?"
      else:
        restaurants_spend = "When you got started you said you were spending $" + restaurants + " each month. How much did you spend this month?"
      
      if accessories == "No info given":
        accessories_spend = "You didn't mention when you started how much you were spending on accessories. You can update that at any point. How much did you spend this month?"
      else:
        accessories_spend = "When you got started you said you were spending $" + accessories + " each month. How much did you spend this month?"
      return render_template("/trackershopping.html", dietaryattitude=dietary_attitude, beefconsumption = beef_consumption, chickenconsumption=chicken_consumption, porkconsumption=pork_consumption, drycleaningspend=drycleaning_spend_db, restaurantsspend=restaurants_spend, accessories=accessories_spend)

@app.route("/trackertransport", methods=["GET", "POST"])
@login_required
def trackertransport():
  """Allows user to track their progress"""
  if request.method == "POST":
    
    # Set region for calculations using API calls
    region = "US"
    
    # Get db values to repopulate fields on load 
    get_db_transport = db.execute("SELECT short_haul, medium_haul, long_haul FROM transport_footprint WHERE user_id=?", session.get("user_id"))
    get_db_spending = db.execute("SELECT hotels FROM consumption_footprint WHERE user_id=?", session.get("user_id"))
    
    # Extract flight info from transport table
    for info in get_db_transport:
      short_haul = info['short_haul']
      medium_haul = info['medium_haul']
      long_haul = info['long_haul']
    total_flights = int(short_haul) + int(medium_haul) + int(long_haul)
    
    # Extract flight info from spending table
    for info in get_db_spending: 
      hotel_nights = info['hotels']
    
    # Handle cases where user did not provide information about hotels
    if hotel_nights == "No info given":
      hotel_nights = "You didn't mention how many nights you spend, on average, in hotels. You can change this at anytime to track your changes here."
      fewer_hotels_db = 0
      hotel_counter = hotel_nights
    else:
      fewer_hotels_db = hotel_nights
      hotel_counter = "When you started, you reported spending an average of " + fewer_hotels_db + " nights in hotels per year."
    
    # Get current values from form 
    get_db = db.execute("SELECT saved_money, saved_energy, vacationed_local, green_tariff, solar_panels, fewer_flights, fewer_hotels, more_direct_flights, miles_walk_bike, carbon_savings, total_score FROM trackers WHERE user_id=?", session.get("user_id"))

    # Get information from form in template
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
    
    # Extract information from list of dictionaries returned by db and handle formatting 
    for info in tracker_db:
      saved_money_db = info['saved_money']
      vacationed_local_db = info['vacationed_local']
      fewer_flights_db = info['fewer_flights']
      fewer_hotels_tracker = info['fewer_hotels']
      more_direct_flights_db = info['more_direct_flights']
      miles_walked_biked_db = info['miles_walk_bike']
      carbon_offset_db = info['carbon_offset']
      carbon_savings_db = info['carbon_savings']
      total_score_db = info['total_score']
    
    # Manage empty fields for flights and calculate scores
    if fewer_flights is None:
      flights_saved = 0
    else: 
      if int(fewer_flights) > total_flights or int(fewer_flights) == total_flights:
        flights_saved = 0
      else:
        flights_saved = total_flights - int(fewer_flights)

    # Manage empty fields for hotels and calculate scores
    carbon_savings_hotels = 0
    if fewer_hotels is None:
      hotel_nights_saved = 0
      
    elif fewer_hotels_db == 0:
      hotel_nights_saved = 0
      carbon_savings_hotels = 0
    elif int(fewer_hotels) > int(fewer_hotels_db) or int(fewer_hotels) == int(fewer_hotels_db):
      hotel_nights_saved = 0
      carbon_savings_hotels = 0
    else:
      hotel_nights_saved = int(fewer_hotels_db) - int(fewer_hotels)
      hotel_activity_id = "accommodation_type_hotel_stay"
      original_carbon_impact = impact_by_number(hotel_activity_id, int(fewer_hotels_db), region)
      initial_carbon_impact_hotels = float(original_carbon_impact['Carbon_emissions'])  
      current_carbon_impact = impact_by_number(hotel_activity_id, int(fewer_hotels), region)
      current_carbon_impact_hotels = float(current_carbon_impact['Carbon_emissions'])
      carbon_savings_hotels = initial_carbon_impact_hotels - current_carbon_impact_hotels
    
     # Manage empty fields for direct flights and calculate scores
    if direct_flights is None:
      direct_flights_add = 0
    else: 
      direct_flights_add = int(direct_flights)
    
    # Manage empty fields for choosing trains instead of planes and calculate scores
    if train_over_plane is None:
      more_trains_add = 0 
    else: 
      more_trains_add = int(train_over_plane)
    
    # Manage empty fields for local vacation days and calculate scores 
    if local_vacation is None:
      local_vacation_add = 0
    else: 
      local_vacation_add = int(local_vacation)
    
    # Manage empty fields for green miles and calculate scores 
    if bike_walk is None: 
      biked_miles_add = 0 
    else: 
      biked_miles_add = float(bike_walk)
    
    # Manage empty fields for saving money on transport this month, calculate scores
    if transport_savings is None:
      money_savings_transport = 0.00
    else: 
      money_savings_transport = float(transport_savings) * 1.00
    
    # Manage empty fields for purchasing carbon offsets from an airline and calculate scores 
    if carbon_offset is None:
      carbon_offset_status = 0
    else:
      carbon_offset_status = float(carbon_offset)
    
    # Calculate ew scores totals and manage formatting
    total_flights_saved = int(fewer_flights_db) + flights_saved + more_trains_add
    carbon_savings_total = formatfloat(carbon_savings_hotels + float(carbon_savings_db))
    direct_flights_total = direct_flights_add + int(more_direct_flights_db)
    local_vacation_total = int(vacationed_local_db) + local_vacation_add
    total_hotel_nights_saved = int(fewer_hotels_db) + hotel_nights_saved
    total_bike_walk = formatfloat(float(miles_walked_biked_db) + biked_miles_add)
    if "$" in saved_money_db:
      saved_money_db = saved_money_db.replace("$", "")
      if "," in saved_money_db:
        saved_money_db = saved_money_db.replace(",", "")
    if "," in total_score_db:
      total_score_db = total_score_db.replace(",", "")
    money_savings_total = formatfloat((float(money_savings_transport) + float(saved_money_db)) * 1.00)
    carbon_offset_total = formatfloat(float(carbon_offset_db) + carbon_offset_status)
    new_total_score = float(total_score_db) + flights_saved + hotel_nights_saved + more_trains_add  + carbon_savings_hotels + direct_flights_add + local_vacation_add + biked_miles_add + money_savings_transport + carbon_offset_status

    # Add new scores to db
    update_db = db.execute("UPDATE trackers SET saved_money=?, vacationed_local=?, fewer_flights=?, fewer_hotels=?, more_direct_flights=?, miles_walk_bike=?, carbon_offset=?, carbon_savings=?, total_score=? WHERE user_id=?", money_savings_total, local_vacation_total, total_flights_saved, total_hotel_nights_saved, direct_flights_total, total_bike_walk, carbon_offset_total, carbon_savings_total, new_total_score, session.get("user_id"))
    update_lb = db.execute("UPDATE leaderboard SET green_miles=?, carbon_saved=?, total_points=? WHERE user_id=?", total_bike_walk, carbon_savings_total, new_total_score, session.get("user_id"))
    flash("Processed 😀 Would you like to track something else? To see updates to your score please see your home page.")
    return render_template("/trackertransport.html", hotelcounter=hotel_counter, totalflights=total_flights, hotelnights=hotel_nights)
  else:
    
    # Handle get request
    # Get values from transport and spending db tables to populate fields on load
    get_db_transport = db.execute("SELECT short_haul, medium_haul, long_haul FROM transport_footprint WHERE user_id=?", session.get("user_id"))
    get_db_spending = db.execute("SELECT hotels FROM consumption_footprint WHERE user_id=?", session.get("user_id"))

    # Extract elements from list of dictionaries returned by db and manage formatting
    for info in get_db_transport:
      short_haul = info['short_haul']
      medium_haul = info['medium_haul']
      long_haul = info['long_haul']
    total_flights = int(short_haul) + int(medium_haul) + int(long_haul)
    
    for info in get_db_spending: 
      hotel_nights = info['hotels']
      hotel_counter = 0
    if hotel_nights == "No info given":
      hotel_nights = "You didn't mention how many nights you spend on average in hotels. You can change this at anytime to track your changes here."
      hotel_counter = "You haven't tracked the amount of average nights you spend in hotels in the calculator. Update that to start tracking your progress."
    else:
      hotel_nights = hotel_nights
      hotel_counter = "When you started, you reported spending an average of " + hotel_nights + " nights in hotels per year. How many less did you spend?"
  
  return render_template("/trackertransport.html", hotelcounter=hotel_counter, totalflights=total_flights, hotelnights=hotel_nights)


# References sourced to build random username generator:
# https://grammar.yourdictionary.com/parts-of-speech/adjectives/list-of-adjective-words.html
# https://www.grammarly.com/blog/adjective/
# https://a-z-animals.com/animals/
# https://stackoverflow.com/questions/4319236/remove-the-newline-character-in-a-list-read-from-a-file 


  