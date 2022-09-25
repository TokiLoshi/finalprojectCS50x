
from crypt import methods
from curses import use_default_colors
import email
import os
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
from helpers import apology, login_required, lookup, usd, random_leaderboardname

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
  return render_template("/account.html")

# Users activity page
@app.route("/activity", methods=["GET", "POST"])
@login_required
def activity():
  """Allows users to track their activities and see how that affects their carbon score"""

# Calculator page
@app.route("/calculator", methods=["GET", "POST"])
@login_required
def calculator():
  """Quiz user takes to tally up their carbon score"""
  return render_template("/calculator.html")

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
  return render_template("/contact.html")

# Footprint page
@app.route("/footprint", methods=["GET", "POST"])
@login_required
def footprint():
  """Shows user their current footprint and which areas are impacting their score the most"""
  return render_template("/footprint.html")

# Main home page
@app.route("/", methods=["GET"])
def home():
  """Information about the web app and what it does"""
  return render_template("home.html")

# Page user sees the first time after they register and login:
@app.route("/homefirst", methods=["GET"])
@login_required
def homefirst():
  """Welcome message"""
  return render_template("homefirst.html")

# Page user sees after they return
@app.route("/homeuser", methods=["GET", "POST"])
@login_required
def homeuser():
  """Displays information for returning user"""
  return render_template("homeuser.html")

# Leaderboard page
@app.route("/leaderboard", methods=["GET"])
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

    useremail = request.form.get("email")
    print(f"Email: ", useremail)
    password = request.form.get("password")
    print(f"Password: ", password)
    # Check db for email

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
  if request.method == "POST":
    flash("Please Check Your Email, if you don't see it please check your spam folder and then add us to your address book")
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
  return render_template("/tracker.hml")



# References sourced to build random username generator:
# https://grammar.yourdictionary.com/parts-of-speech/adjectives/list-of-adjective-words.html
# https://www.grammarly.com/blog/adjective/
# https://a-z-animals.com/animals/
# https://stackoverflow.com/questions/4319236/remove-the-newline-character-in-a-list-read-from-a-file 
