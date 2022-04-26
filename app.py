#Import Flask Library
from email import charset
from flask import Flask, render_template, request, session, url_for, redirect
from flask_restx import reqparse
import pymysql.cursors
import os 
from dotenv import load_dotenv
from objectParsers import customer_parser, airline_staff_parser, airport_parser, flight_parser
import dbmanager

#Initialize the app from Flask
app = Flask(__name__)

load_dotenv()
host = os.environ.get("HOST")
user = os.environ.get("USER")
password = os.environ.get("PASSWORD")
db = os.environ.get("DB")
print(host, user, password, db)

#Configure MySQL
conn = pymysql.connect(host=host,
                       user=user,
                       password=password,
                       db=db,
                       charset='utf8mb4',
                       cursorclass=pymysql.cursors.DictCursor)

#Define a route to hello function
@app.route('/')
def hello():
	return render_template('index.html')

#Define route for login
@app.route('/login')
def login():
	return render_template('login.html')

#Define route for register
@app.route('/register')
def register():
	return render_template('register.html')

@app.route('/customerRegister')
def customerRegister(): 
    return render_template('customerRegister.html')

@app.route('/staffRegister')
def staffRegister(): 
    return render_template('staffRegister.html')

# APPLICATION USE CASES
# 1. VIEW PUBLIC INFO
@app.route('/airports', methods=['GET', 'POST'])
def airports(): 
	if request.method == 'GET': 
		# returns dict = {city1: airport_obj1, city2: airport_obj2 }
		return dbmanager.getAllAirports()
	elif request.method == 'POST': 
		airport = airport_parser.parse_args()
		return dbmanager.createAirport(airport)
	else: 
		# todo raise 405 method not allowed
		return None

@app.route('/flight/search/', methods=['POST'])
def searchFlights(): 
    # if it's round trip, just use this endpoint again
    source = request.form["source"] # airport code
    destination = request.form["destination"]
    departure = request.form["departure_date"]
    
    # return render_template('home.html', username=session["username"], flights=dbmanager.searchFlights(source, destination, departure))
    return dbmanager.searchFlights(source, destination, departure)

# 2. REGISTER
@app.route('/registerAuth/<type_user>', methods=['GET', 'POST'])
def registerAuth(type_user):
    if type_user == "customer":
        customer = customer_parser.parse_args()
        inDB = dbmanager.registerCustomer(customer)
    elif type_user == "airline_staff":
        staff = airline_staff_parser.parse_args()
        inDB = dbmanager.registerStaff(staff)
        
    if not inDB: 
        if type_user == "customer":
            template = "customerRegister.html"
        elif type_user == "airline_staff":
            template = "staffRegister.html"
        return render_template(template, error="email or username exists already")
    else:
        session['username'] = inDB
        return redirect(url_for('home'))

# 3. LOGIN
@app.route('/loginAuth', methods=['GET', 'POST'])
def loginAuth():
	#grabs information from the forms
	username = request.form['username']
	password = request.form['password']
	type_user = request.form['type']

	exists = dbmanager.checkUserLogin(type_user, username, password)
	error = None
	if(exists):
		#creates a session for the the user
		#session is a built in
		session['username'] = username
		return redirect(url_for('home'))
	else:
		#returns an error message to the html page
		error = 'Invalid login or username'
		return render_template('login.html', error=error)

# AIRLINE STAFF USE CASES
# 1. VIEW FUTURE FLIGHTS WITHIN 30 DAYS 
# 2. CREATE FLIGHTS
@app.route('/flights', methods=['GET', 'POST'])
def flights():
    if not session["username"]:
        return None # should actually render template with login error 
    if request.method == 'GET': 
        return dbmanager.findFutureAirlineFlights(session["username"])
    elif request.method == 'POST':
        flight = flight_parser.parse_args()
        return dbmanager.createFlight(flight)

# 3. CHANGE FLIGHT STATUS
@app.route('/flight_status', methods=['POST'])
def flightStatus():
    if not session["username"]:
        return None 
    if request.method == 'POST':
        status = request.form['status']
        flight_number = request.form['flight_number']
        departure_date_time = request.form['departure_date_time']
        
        return dbmanager.changeFlightStatus(status, flight_number, departure_date_time, session["username"])
        
     
@app.route('/home')
def home():
    username = session['username']
    return render_template('home.html', username=username)

		
@app.route('/post', methods=['GET', 'POST'])
def post():
	username = session['username']
	cursor = conn.cursor();
	blog = request.form['blog']
	query = 'INSERT INTO blog (blog_post, username) VALUES(%s, %s)'
	cursor.execute(query, (blog, username))
	conn.commit()
	cursor.close()
	return redirect(url_for('home'))

@app.route('/logout')
def logout():
	session.pop('username')
	return redirect('/')
		
app.secret_key = 'some key that you will never guess'
#Run the app on localhost port 5000
#debug = True -> you don't have to restart flask
#for changes to go through, TURN OFF FOR PRODUCTION
if __name__ == "__main__":
	app.run('127.0.0.1', 5000, debug = True)
