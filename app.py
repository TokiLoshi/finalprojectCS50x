
from audioop import avg
from crypt import methods
from curses import use_default_colors
import email
from hashlib import new
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
from helpers import apology, login_required, lookup, usd, random_leaderboardname, generate_temp_password
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
app.jinja_env.filters["usd"] = usd

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
  for info in get_user_info:
    name = info['name']
    leaderboardname = info['leaderboardname']
    emailaddy = info['email']
    datejoined = info['datejoined']
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

    # Print Statements to test
    print("Building is a: ", building)
    print("State is: ", state)
    print("There are household occupants: ", household_occupants)
    print("Recycling: ", recycling)
    print("Utility Bill: ", utility_bill)
    print("Dry cleaning: ", drycleaning)

    # HACK: 
    # Buildings multifamily is 0.113kg/USD median cost per unit is $64,500 0 $86,000 https://www.multifamily.loans/apartment-finance-blog/multifamily-construction-costs-an-investor-guide#:~:text=According%20to%20the%20most%20recent,%2464%2C500%20to%20%2486%2C000%20per%20unit. 
    multifamily_median = (64500 + 86000)/2
    singlefamily_median = 428700
    # Single family home is 0.226kgs/USD according to a service by the Motley Fool https://www.fool.com/the-ascent/research/average-house-price-state/#:~:text=Average%20home%20price%20in%20the%20United%20States%3A%20%24428%2C700&text=That's%20a%2030%25%20increase%20from,when%20the%20median%20was%20%24329%2C000.&text=Median%20sales%20price%20of%20homes,of%20homes%20in%20the%20U.S.&text=Data%20source%3A%20Federal%20Reserve%20Bank%20of%20St
    
    if building is None: 
      building = "Info not provided"
      building_impact = "Need more info to calculate"
    elif building == "construction-type_multifamily_residential_structures":
      print("We've got a multi")
      building_impact = impact_by_money(building, region, multifamily_median)
      print("Impact of multi family home: ", building_impact)
    elif building == "construction-type_single_family_residential_structures":
      print("We've got a single family home")
      building_impact = impact_by_money(building, region, singlefamily_median)
      print("Impact of Single family home: ", building_impact)
    else:
      print("Dunno what happend but they got something through")

    # Work out impact by electricity
    electricity_activity_id = "electricity-energy_source_grid_mix"
    if state is None:
      state = "Info not provided"
      impact_electricity = "Need more info to calculate"
    else:  
      region = state
      energy = utility_bill
      impact_electricity = impact_by_energy(electricity_activity_id, region, energy)
      print("Impact by electricity: ", impact_electricity)

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
      print("Weight in pounds", total_weight_pounds)
      weight_kg = total_weight_pounds / 2.2046
      print("Weight in KG", weight_kg)
      # Convert to percentage
      percentage_recycled = recycling / 100
      percentage_landfil = (100 - recycling)
      print("Percentage recycled", percentage_recycled)
      weight_recycled = weight_kg * percentage_recycled
      weight_landfill = float((weight_kg - weight_recycled) * percentage_landfil)
      print("Weight recycled: ", weight_recycled)
      print("Weight landfill", weight_landfill)
      impact_landfill = impact_by_weight(landfill_id, weight_landfill)
      impact_recycling = impact_by_weight(recycling_id, weight_recycled)
      print("Impact of landfill: ", impact_landfill)
      print("Impact of recycling: ", impact_recycling)

    # Impact of drycleaning per person in house:
    if household_occupants is None: 
      household_occupants = "Info not provided"
      drycleaning_impact = "Need number of houshold occupants to " 
    drycleaning_cost_per_person = int(drycleaning / int(household_occupants))
    drycleaning_region = "US"
    print("drycleaning cost per person: ", drycleaning_cost_per_person)
    drycleaning_activity_id = "consumer_goods-type_dry_cleaning_laundry"
    drycleaning_impact = impact_by_money(drycleaning_activity_id, drycleaning_region, drycleaning_cost_per_person)
    print("Drycleaning impact: ", drycleaning_impact)

    return render_template("/calculatortransport.html")
  else:
    return render_template("/calculator.html")

# Calculator page for transport
@app.route("/calculatortransport", methods=["GET", "POST"])
@login_required
def calculatortransport():
  """Quiz user takes to tally up their carbon score"""
  if request.method == "POST":
    print("Yay post")
    work_situation = request.form.get("work_situation")
    commuter_days = request.form.get("commuter_days")
    commuter_distance = request.form.get("commuter_distance")
    transport_mode = request.form.get("transport_mode")
    short_haul = request.form.get("short_haul")
    medium_haul = request.form.get("medium_haul")
    long_haul = request.form.get("long_haul")
    transport_cost = int(request.form.get("transport_cost"))
    
    # Print statements to test
    print("Work situation: ", work_situation)
    print("commuter days: ", commuter_days)
    print("commuter distance: ", commuter_distance)
    print("transport_mode: ", transport_mode)
    print("short haul: ", short_haul)
    print("medium haul: ", medium_haul)
    print("long haul: ", long_haul)
    print("Transport Cost: ", transport_cost)

    region = "US"

    # HACK:
    # Impact of total number of short_haul_flights 0.22701067kg/passengermile
    short_haul_id = "passenger_flight-route_type_na-aircraft_type_na-distance_lt_300mi-class_na-rf_na"
    short_distance = 300
    short_haul_impact = impact_by_flights(short_haul_id, short_distance)
    print("short haul impact: ", short_haul_impact)
    # Impact of total_number of long haul flights
    medium_haul_id = "passenger_flight-route_type_na-aircraft_type_na-distance_gt_300mi_lt_2300mi-class_na-rf_na" 
    medium_distance = 2300
    medium_haul_impact = impact_by_flights(medium_haul_id, medium_distance)
    print("Medium Haul Flight Impact: ", medium_haul_impact)
    # Impact of total number of long haul flights
    long_haul_id = "passenger_flight-route_type_na-aircraft_type_na-distance_gt_2300mi-class_na-rf_na"
    long_distance = 3500
    long_distance_impact = impact_by_flights(long_haul_id, long_distance)
    print("Long Haul impact: ", long_distance_impact)
    
    # Work out total commuter distance per week
    distance_commute = (float(commuter_distance) * 2) * int(commuter_days)
    impact_driving = impact_by_road("passenger_vehicle-vehicle_type_passenger_ground_transport-fuel_source_na-distance_na-engine_size_na", transport_cost)
    print("Commuter total distance: ", distance_commute)
    print("Impact of road transport: ", impact_driving)
    if transport_mode == "passenger_vehicle-vehicle_type_pickup_trucks_vans_suvs-fuel_source_na-engine_size_na-vehicle_age_na-vehicle_weight_na":
      print("We've got ourselves an SUV")
    return render_template("/calculatorconsumption.html")
  else: 
    print("Nope")
    return render_template("/calculatortransport.html")

# Calculator page for consumption
@app.route("/calculatorconsumption", methods=["GET", "POST"])
@login_required
def calculatorconsumption():
  """Quiz user takes to tally up their carbon score"""
  print("hi we're here")
  if request.method == "POST":
    print("Wahoo post")
    beef = request.form.get("beef")
    pork = request.form.get("pork")
    chicken = request.form.get("chicken")
    flexitarian = request.form.get("flexitarian")
    new_clothes = request.form.get("new_clothes")
    restaurants = request.form.get("restaurants")
    accessories = request.form.get("accessories")
    appliances = request.form.get("appliances")
    electronics = request.form.get("electronics")
    hotels = request.form.get("hotels")
    # print("Beef: ", beef)
    # print("Pork", pork)
    # print("Chicken", chicken)
    # print("flexitarian: ", flexitarian)
    # print("new clothes: ", new_clothes)
    # print("restaurants: ", restaurants)
    # print("accessories: ", accessories)
    # print("appliances: ", appliances)
    # print("electronics: ", electronics)
    # print("hotels: ", hotels)
    region = "US"
    
    # Hotel impact at 16.1kg (default 2022) per night 
    hotel_activity_id = "accommodation_type_hotel_stay"
    if hotels is None: 
      hotels = "No info given"
      hotel_impact = "Need more information to calculate"
    else:
      hotel_number = int(hotels)
      hotel_impact = impact_by_number(hotel_activity_id, hotel_number, region)
      print("Hotel impact: ", hotel_impact)
      print(type(hotel_impact))
      for impact in hotel_impact:
        hotel_carbon = hotel_impact['Carbon_emissions']
        hotel_unit = hotel_impact['Carbon_unit']
      print("Hotel carbon: ", hotel_carbon)
      print("Hotel unit: ", hotel_unit)

    # Impact by clothes 2020 - 1.947kg/usd 
    clothing_activity_id = "consumer_goods-type_clothing"
    if clothing_spend is None:
      clothing_spend = "No info given"
      clothing_impact = "Need more information to calculate"
    else:
      clothing_spend = int(new_clothes)
      clothing_impact = impact_by_money(clothing_activity_id, region, clothing_spend)
      print("Clothing Impact: ", clothing_impact)
      for impact in clothing_impact:
        clothing_carbon = clothing_impact['Carbon_emissions']
        clothing_unit = clothing_impact['Carbon_unit']
        print("Clothing carbon: ", clothing_carbon)
      print("Clothing unit: ", clothing_unit)
    
    # Impact by accessories 2020 - 0.215kg/USD
    accessories_activity_id = "consumer_goods-type_clothing_clothing_accessories_stores"
    if accessories_spend is None:
      accessories_spend = "No info given"
      accessories_impact = "Need more information to calculate"
    else:
      accessories_spend = int(accessories)
      accessories_impact = impact_by_money(accessories_activity_id, region, accessories_spend)
      print("Accessories impact: ", accessories_impact)
      for impact in accessories_impact:
        accessories_carbon = accessories_impact['Carbon_emissions']
        accessories_unit = accessories_impact['Carbon_unit']
        print("Accessories Carbon: ", accessories_carbon)
        print("Accessories unit: ", accessories_unit)

    # Impact by electronics 2020 - 1.083kg/USD
    electronics_activity_id = "electrical_equipment-type_small_electrical_appliances"
    if electronics_impact is None:
      electronics_spend = "No info given"
      electronics_impact = "Need more information to calculate"
    else:
      electronics_spend = int(electronics)
      electronics_impact = impact_by_money(electronics_activity_id, region, electronics_spend)
      for impact in electronics_impact:
        electronics_carbon = electronics_impact['Carbon_emissions']
        electronics_unit = electronics_impact['Carbon_unit']
        print("Electronics carbon: ", electronics_carbon)
        print("Electronics unit: ", electronics_unit)

    # Impact by appliances (cooking) 2020 - 0.524kg/USD
    appliances_activity_id = "electrical_equipment-type_home_cooking_appliances"
    if appliances_spend is None: 
      appliances_spend = "No info given"
      appliances_impact = "Need more information to calculate"
    else:
      appliances_spend = int(appliances)
      appliances_impact = impact_by_money(appliances_activity_id, region, appliances_spend)
      for impact in appliances_impact:
        appliances_carbon = appliances_impact['Carbon_emissions']
        appliances_unit = appliances_impact['Carbon_unit']
        print("Appliances Carbon: ", appliances_carbon)
        print("Appliances unit: ", appliances_unit)

    # Impact by restaurants 2020 - 0.261kg/USD
    restaurants_activity_id = "consumer_services-type_full_service_restaurants"
    if restaurants_spend is None:
      restaurants_spend = "No info given"
      restaurants_impact = "Need more information to calculate"
    else:
      restaurants_spend = int(restaurants)
      restaurants_impact = impact_by_money(restaurants_activity_id, region, restaurants_spend)
      for impact in restaurants_impact:
        restaruant_carbon = restaurants_impact['Carbon_emissions']
        restaurants_unit = restaurants_impact['Carbon_unit']
        print("Restaurants carbon: ", restaruant_carbon)
        print("Restaurants unit: ", restaurants_unit)

    # Impact by beef consumption 2021 3.7609kg/EUR 
    # We might need to look further into this guessing each person eats half a pound per adult
    beef_activity_id = "consumer_goods-type_meat_products_beef"
    beef_frequency = int(beef)
    beef_price = (5.12 / 2)
    beef_spend = beef_price * beef_frequency
    # To get the spend we need to figure out how many times a week the person is eating it multiplied by the average cost per serving
    beef_impact = impact_by_money(beef_activity_id, region, beef_spend)
    print("Beef impact: ", beef_impact)
    
    # We might want to look at port as well which is 2021 and higher 0.4543 kg/USD
    pork_activity_id = "consumer_goods-type_meat_products_pork"
    pork_frequency = int(pork)
    # Average price obtained from USDA https://www.ams.usda.gov/mnreports/lsmnprpork.pdf
    pork_prices = [1.21, 11.21, 9.64, 11.26, 8.89, 9.04, 16.22, 9.56, 8.20, 7.92, 8.83, 9.04, 8.79, 8.76, 11.25]
    sum_pork_prices = sum(pork_prices)
    print("Pork_prices sum", sum_pork_prices)
    print(type(sum_pork_prices))

    average_pork_prices = sum(pork_prices) / len(pork_prices)
    print("Pork Price", average_pork_prices)
    print(type(average_pork_prices))
    # We might want to weight this by popularity 
    # To get the spend we need to figure out how many times a week the person is eating it multiplied by the average cost per serving
    pork_spend = int(pork_frequency) * average_pork_prices
    print("Pork spend", pork_spend)
    print(type(pork_spend))
    pork_impact = impact_by_money(pork_activity_id, region, pork_spend)
    print("Pork impact: ", pork_impact)
    
    # Chicken is 2021 at 0.6325 USD/kg
    chicken_activity_id = "consumer_goods-type_meat_products_poultry"
    # To get the spend we need to figure out how many times a week the person is eating it multiplied by the average cost per serving
    chicken_frequency = int(chicken)
    # Stats for chicken spend https://www.bls.gov/regions/mid-atlantic/data/averageretailfoodandenergyprices_usandmidwest_table.htm
    chicken_spend = (1.87 / 2)
    chicken_impact = impact_by_money(chicken_activity_id, region, chicken_spend)
    print("Chicken impact: ", chicken_impact)

    return render_template("/results.html")
  else: 
    print("Reliable old get")
    return render_template("/calculatorconsumption.html")


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

    elif (len(count) > 1):
      return apology("An account already exists")
    
    else:
      # INSERT new user and store a hash of the password:
      # **** Should look at ways to make this password more secure
      hash = generate_password_hash(request.form.get("password"), method="pbkdf2:sha256", salt_length=8)
      new_user = db.execute("INSERT INTO users (name, email, leaderboardname, hash) VALUES(?, ?, ?, ?)", name, email, leaderboardname, hash)
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
  return render_template("/results.html")

# Tracker page to track carbon footprint
@app.route("/tracker", methods=["GET", "POST"])
@login_required
def tracker():
  """Allows user to track their progress"""
  if request.method == "POST":
    flash("You're amazing. Great work!")
  return render_template("/tracker.html")



# References sourced to build random username generator:
# https://grammar.yourdictionary.com/parts-of-speech/adjectives/list-of-adjective-words.html
# https://www.grammarly.com/blog/adjective/
# https://a-z-animals.com/animals/
# https://stackoverflow.com/questions/4319236/remove-the-newline-character-in-a-list-read-from-a-file 
