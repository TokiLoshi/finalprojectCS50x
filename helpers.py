import os
import requests
import urllib.parse
import json
import string
import requests
import random
from dotenv import load_dotenv
from flask import redirect, render_template, request, session
from functools import wraps

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

# Adopted from code from CS50 Pset 9 - Finance
def lookup(footprint):
  """Call API with input variables from user to calculate footprint"""
  api_key = os.getenv('CARBON_API_KEY')
  api_url = '{}'.format(footprint)
  response = requests.get(api_url, header={api_key})
  if response.status_code == requests.codes.ok:
    try:
      query = response.json()
    except (KeyError, TypeError, ValueError):
      return apology("Something went wrong")
  else:
    print("Error", response.status_code, response.text)

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

