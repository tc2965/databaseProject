#Import Flask Library
from email import charset
from flask import Flask, render_template, request, session, url_for, redirect
from flask_restx import reqparse
import pymysql.cursors
import os 
from dotenv import load_dotenv
from utils.objectParsers import customer_parser, airline_staff_parser, airport_parser, flight_parser, airplane_parser
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
# 1. VIEW PUBLIC INFO A
@app.route('/flight/search/', methods=['POST'])
def searchFlights(): 
    # if it's round trip, just use this endpoint again
    print(request)
    source = request.form["source"] # airport code
    destination = request.form["destination"]
    departure = request.form["departure_date"]
    flights = dbmanager.searchFlights(source, destination, departure)
    
    username = session.get("username")
    airline = session.get("airline")
    if username and airline:
        # it's a staff
        session["flights"] = flights
        return redirect(url_for("staffHome"))
    elif username:
        # it's a customer 
        return redirect(url_for("customerHome"))
    else:
        # it's public 
        session["flights"] = flights
        return redirect(url_for("home"))

@app.route('/flight/search/return', methods=['POST'])
def searchReturnFlights(): 
    print(request)
    source = request.form["source"] # airport code
    destination = request.form["destination"]
    departure = request.form["departure_date"]
    returnFlights = dbmanager.searchFlights(source, destination, departure)
    username = session.get("username")
    airline = session.get("airline")
    if username and airline:
        # it's a staff
        session["returnFlights"] = returnFlights
        return redirect(url_for("staffHome"))
    elif username:
        # it's a customer 
        return redirect(url_for("customerHome"))
    else:
        # it's public 
        session["returnFlights"] = returnFlights
        return redirect(url_for("home"))

@app.route('/flight_status/view/', methods=['POST'])
def viewFlightStatus(): 
    airline = request.form["airline"]
    flight_number = request.form["flight_number"]
    arrival_date = request.form.get("arrival_date")
    departure_date = request.form["departure_date"]
    
    status = dbmanager.viewFlightStatus(airline, flight_number, departure_date, arrival_date)
    session["status"] = status
    print(status)
    return redirect(url_for('staffHome'))

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
        if type_user == "airline_staff":
            path = 'staffHome'
        return redirect(url_for(path))

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
        if type_user == 'customer':
            return redirect(url_for('home'))
        else:
            session["airline"] = exists["airline_name"]
            return redirect(url_for('staffHome'))
        
    else:
		#returns an error message to the html page 
        error = 'Invalid login or username'
        return render_template('login.html', error=error)

# AIRLINE STAFF USE CASES
# 1. VIEW FUTURE FLIGHTS BY RANGE OF DATES
@app.route('/view_flights/time', methods=['POST'])
def view_flights_time():
    if not session.get("username"):
        return None # todo render page with error
    if request.method == 'POST': 
        start = request.form["start"]
        end = request.form["end"]
        flights = dbmanager.findFutureAirlineFlightsTime(start, end, session["username"])["data"]
        session["flights"] = flights
        return redirect(url_for('staffHome'))

# 1. VIEW FUTURE FLIGHTS WITHIN 30 DAYS
@app.route('/view_flights/time/default', methods=['GET'])
def view_flights_time_default():
    if not session.get("username"):
        return None # todo render page with error
    if request.method == 'GET': 
        return dbmanager.findFutureAirlineFlightsTime(None, None, session["username"])

# 1. VIEW FUTURE FLIGHTS BY AIRPORTS
@app.route('/view_flights/airport', methods=['POST'])
def view_flights_airports():
    if not session.get("username"):
        return None # todo render page with error
    if request.method == 'POST': 
        type = request.form["type"]
        airport = request.form["airport"]
        flights = dbmanager.findFutureAirlineFlightsAirport(type, airport, session["username"])["data"]
        print(flights)
        session["flights"] = flights
        return redirect(url_for('staffHome'))
    
# 1. SEE ALL CUSTOMERS OF PARTICULAR FLIGHT
# 2. CREATE FLIGHTS
@app.route('/createFlight')
def createFlight(message=None, error=None): 
    return render_template('createFlight.html', message=message, error=error)

@app.route('/flights', methods=['GET', 'POST'])
def flights():
    if not session.get("username"):
        return createFlight("Login first")
    if request.method == 'POST':
        flight = flight_parser.parse_args()
        return dbmanager.createFlight(flight)

# 3. CHANGE FLIGHT STATUS
@app.route("/changeFlightStatus")
def changeFlightStatus(message=None, error=None):
    return render_template("changeFlightStatus.html", message=message, error=error)

@app.route('/flight_status', methods=['POST'])
def flightStatus():
    if not session.get("username"):
        return changeFlightStatus(error="Login first")
    if request.method == 'POST':
        status = request.form['status']
        flight_number = request.form['flight_number']
        departure_date_time = request.form['departure_date_time']
        
        message = dbmanager.changeFlightStatus(status, flight_number, departure_date_time, session["username"])
        return changeFlightStatus(message=message)
        
# 4. ADD AIRPLANE 
@app.route('/createAirplane')
def createAirplane(message=None, error=None): 
    return render_template('createAirplane.html', message=message, error=error)

@app.route('/airplane', methods=['POST'])
def airplane(): 
    if not session.get("username"):
        return createAirplane(error="Login first")
    if request.method == 'POST':
        airplane = airplane_parser.parse_args() 
        message = dbmanager.addAirplane(airplane, session["username"])
        return createAirplane(message=message)

# 5. ADD AIRPORT 
@app.route('/createAirport')
def createAirport(message=None, error=None): 
    return render_template('createAirport.html', message=message, error=error)

@app.route('/airport', methods=['POST'])
def airport():
    if not session.get("username"):
        return createAirport(error="Login first") # todo render page with error
    if request.method == 'POST':
        airport = airport_parser.parse_args() 
        message = dbmanager.addAirport(airport)
        return createAirport(message=message)

# 6. VIEW FLIGHT RATINGS 
# /view_flight_ratings/ER400
@app.route('/view_flight_ratings/', methods=['POST'])
def viewFlightRatings():
    if not session.get("username"):
        return None # todo render page with error
    if request.method == 'POST':
        flight_number = request.form["flight_number"]
        ratings = dbmanager.viewFlightRatings(flight_number, session["username"])
        session["ratings"] = ratings 
        print(ratings)
        return redirect(url_for('staffHome'))
     
# 7. VIEW MOST FREQUENT CUSTOMER 
@app.route('/view_most_frequent_customer', methods=['GET'])
def viewMostFrequentCustomer(): 
    if not session.get("username"):
        return None # todo render page with error
    if request.method == 'GET':
        mostFrequentFlyer= dbmanager.viewMostFrequentCustomer(session["username"])
        session["mostFrequentFlyer"] = mostFrequentFlyer
        return redirect(url_for('staffHome'))

@app.route('/view_customer_flights', methods=['POST'])
def viewCustomerFlights():
    if not session.get("username"):
        return None 
    if request.method == 'POST':
        customer_email = request.form["customer_email"]
        customer_flights = dbmanager.viewCustomerFlights(customer_email, session["username"])
        session["customer_flights"] = customer_flights 
        print(customer_flights)
        return redirect(url_for('staffHome'))

# 8. VIEW REPORT
@app.route('/viewReports')
def viewReports():
    revenueTravelClass = session.get("viewRevenueTravelClass")
    report = session.get("viewReportDate")
    revenue = session.get("revenue")
    travel_class_revenue = session.get("travel_class_revenue")
    monthDestinations = session.get("monthDestinations")
    yearDestinations = session.get("yearDestinations")
    return render_template("viewReports.html", airline=session["airline"], revenueTravelClass=revenueTravelClass, report=report, revenue=revenue, travel_class_revenue=travel_class_revenue, monthDestinations=monthDestinations, yearDestinations=yearDestinations)

# /viewReport/2022-01-01/2023-01-01
@app.route('/viewReport/date', methods=['POST'])
def viewReportDate(): 
    if not session.get("username"):
        return None # todo render page with error
    if request.method == 'POST':
        start = request.form["start"]
        end = request.form["end"]
        report = dbmanager.viewReportDate(start, end, session["username"])
        session["viewReportDate"] = report 
        print(report)
        return redirect(url_for('viewReports'))

# 9. VIEW EARNED REVENUE
# /viewRevenue/2022-01-01/2023-01-01
@app.route('/viewRevenue/date', methods=['POST'])
def viewRevenue(): 
    if not session.get("username"):
        return None # todo render page with error
    if request.method == 'POST':
        start = request.form["start"]
        end = request.form["end"]
        revenue = dbmanager.viewRevenue(start, end, session["username"])
        session["revenue"] = revenue
        print(revenue)
        return redirect(url_for("viewReports"))
    
# 10. VIEW EARNED REVENUE BY TRAVEL CLASS 
# /viewRevenueTravelClass/Economy
@app.route('/viewRevenueTravelClass', methods=['GET'])
def viewRevenueTravelClass():
    if not session.get("username"):
        return None # todo render page with error
    if request.method == 'GET':
        travel_class_revenue = dbmanager.viewRevenueTravelClass(session["username"])
        session["travel_class_revenue"] = travel_class_revenue
        print(travel_class_revenue)
        return redirect(url_for("viewReports"))

# 11. VIEW TOP DESTINATIONS
# /viewTopDestinations/month 
# /viewTopDestinations/year
@app.route('/viewTopDestinations/<period>', methods=['GET'])
def viewTopDestinations(period):
    if not session.get("username"):
        return None # todo render page with error
    if request.method == 'GET':
        destinations = dbmanager.viewTopDestinations(period, session["username"])
        session[period+"Destinations"] = destinations
        print(session[period+"Destinations"])
        return redirect(url_for("viewReports"))

@app.route('/home')
def home():
    username = session.get('username')
    flights = session.get("flights")
    returnFlights = session.get("returnFlights")
    return render_template('home.html', username=username, flights=flights, returnFlights=returnFlights)

@app.route('/staffHome')
def staffHome():
    username = session['username']
    airline = session["airline"]
    flights = session.get("flights")
    status = session.get("status")
    ratings = session.get("ratings")
    mostFrequentFlyer = session.get("mostFrequentFlyer")
    customer_flights = session.get("customer_flights")
    returnFlights = session.get("returnFlights")
    return render_template('staffHome.html', username=username, flights=flights, airline=airline, flight_status=status, ratings=ratings, mostFrequentFlyer=mostFrequentFlyer, customer_flights=customer_flights, returnFlights=returnFlights)
		
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
    # session.pop('username')
    session.clear()
    return redirect('/')

		
app.secret_key = 'some key that you will never guess'
#Run the app on localhost port 5000
#debug = True -> you don't have to restart flask
#for changes to go through, TURN OFF FOR PRODUCTION
if __name__ == "__main__":
	app.run('127.0.0.1', 5000, debug = True)
