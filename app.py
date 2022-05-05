#Import Flask Library
from email import charset
from flask import Flask, render_template, request, session, url_for, redirect
from flask_restx import reqparse
from dotenv import load_dotenv
from utils.objectParsers import customer_parser, airline_staff_parser, airport_parser, flight_parser, airplane_parser, purchase_parser, rate_comment_parser, create_tickets_parser, preview_purchase_parser
import dbmanager
import dbmanager_customer

#Initialize the app from Flask
app = Flask(__name__)

#Define a route to hello function
@app.route('/')
def hello():
	return render_template('home.html')

@app.route('/index')
def index():
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
    # if it's round trip, just use this endpoint again with departure_date = arrival_date of the first trip
    query_type = request.form["query_type"]
    departure = request.form["departure_date"]
    if query_type == "airport":
        source = request.form["source"] # airport code
        destination = request.form["destination"]
        flights = dbmanager.searchFlightsAirport(source, destination, departure)
    else:
        source_city = request.form["source_city"]
        source_country = request.form["source_country"]
        destination_city = request.form["destination_city"]
        destination_country = request.form["destination_country"]
        flights = dbmanager.searchFlightsCityCountry(source_city, source_country, destination_city, destination_country, departure)
            
    if flights:
        session.pop("error", None)
        session["flights"] = flights
    else:
        session.pop("flights", None)
        if query_type == "airport":
            session["error"] = f"No Flights Available F from {source} to {destination} at {departure}"
        else: 
            session["error"] = f"No Flights Available F from {source_city}, {source_country} to {destination_city}, {destination_country} at {departure}"
            

    username = session.get("username")
    airline = session.get("airline")

    if username and airline:
        # it's a staff
        return redirect(url_for("staffHome"))
    elif username:
        # it's a customer 
        return redirect(url_for("customerHome"))
    else:
        # it's public 
        return redirect(url_for("home"))

@app.route('/flight/search/return', methods=['POST'])
def searchReturnFlights(): 
    print(request)
    source = request.form["source"] # airport code
    destination = request.form["destination"]
    departure = request.form["departure_date"]
    returnFlights = dbmanager.searchFlightsAirport(source, destination, departure)
    username = session.get("username")
    airline = session.get("airline")

    if returnFlights:
        session.pop("error", None)
        session["returnFlights"] = returnFlights
    else:
        session.pop("returnFlights", None)
        session["error"] = f"No Flights Available F from {source} to {destination} at {departure}"

    if username and airline:
        # it's a staff
        return redirect(url_for("staffHome"))
    elif username:
        # it's a customer 
        return redirect(url_for("customerHome"))
    else:
        # it's public 
        return redirect(url_for("home"))

@app.route('/flight_status/view/', methods=['POST'])
def viewFlightStatus(): 
    airline = request.form["airline"]
    flight_number = request.form["flight_number"]
    arrival_date = request.form.get("arrival_date")
    departure_date = request.form["departure_date"]
    status = dbmanager.viewFlightStatus(airline, flight_number, departure_date, arrival_date)
    
    username = session.get("username")
    airline = session.get("airline")
    session["status"] = status
    if username and airline:
        # it's a staff
        return redirect(url_for("staffHome"))
    elif username:
        # it's a customer 
        return redirect(url_for("customerHome"))
    else:
        # it's public 
        return redirect(url_for("home"))

# 2. REGISTER
@app.route('/registerAuth/<type_user>', methods=['GET', 'POST'])
def registerAuth(type_user):
    session.clear()
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
        if type_user == "airline_staff":
            session['username'] = inDB[0]
            session['airline'] = inDB[1]
            path = 'staffHome'
        else:
            session['username'] = inDB
            path = 'customerHome'
        return redirect(url_for(path))

# 3. LOGIN
@app.route('/loginAuth', methods=['GET', 'POST'])
def loginAuth():
    session.clear()
	#grabs information from the forms
    username = request.form['username']
    password = request.form['password']
    type_user = request.form['type']

    exists = dbmanager.checkUserLogin(type_user, username, password)
    print(f"{exists=}")
    error = None
    if(exists):
		#creates a session for the the user
		#session is a built in
        session['username'] = username
        if type_user == 'customer':
            session['name'] = exists.get("name", None)
            return redirect(url_for('customerHome'))
        else:
            session['name'] = exists.get("first_name", None)
            session["airline"] = exists["airline_name"]
            return redirect(url_for('staffHome'))
        
    else:
		#returns an error message to the html page 
        error = 'Invalid login or username'
        return render_template('login.html', error=error)

# CUSTOMER USE CASES
# 1. VIEW MY FLIGHTS
@app.route('/view_my_flights', methods=['GET'])
def viewMyFlights():
    if not session.get("username"):
        return None # todo render page with error 
    if request.method == 'GET':
        myFlights = dbmanager_customer.viewMyFlights(session["username"])
        return myFlights
    
@app.route('/view_my_upcoming_flights', methods=['GET'])
def viewMyUpcomingFlights():
    if not session.get("username"):
        return None # todo render page with error 
    if request.method == 'GET':
        myFlights = dbmanager_customer.viewMyUpcomingFlights(session["username"])
        return myFlights

# # 2. SEARCH FOR FLIGHTS
# # I don't think we really need to do two searchFlights functions?
# @app.route('/flight/search/', methods=['POST'])
# def searchFlights(): 
#     # if it's round trip, just use this endpoint again
#     source = request.form["source"] # airport code
#     destination = request.form["destination"]
#     departure = request.form["departure_date"]
#     return_date = request.form.get("return_date")
    
#     return dbmanager_customer.searchFlights_customer(source, destination, departure, return_date)

# 3. PURCHASE TICKETS
@app.route('/purchase_tickets_preview', methods=['POST'])
def purchaseTicketsPreview():
    session.pop("error", None)
    session.pop("purchaseStatus", None)
    purchase_preview = preview_purchase_parser.parse_args()
    source_airline = purchase_preview["airline_name"]
    source_flight = purchase_preview["flight_number"]
    source_departure = purchase_preview["departure_date_time"]
    source_travel = purchase_preview["travel_class"]
    to_ticket = dbmanager_customer.getTicketPrice(source_airline, source_flight,
                                                  source_departure, source_travel)
    print(f"\n{to_ticket=}")
    error = to_ticket.get("error", None)
    if error:
        return render_template("purchasePreview.html", error=error)
    
    session["sold_price"] = to_ticket["price"]

    return_airline = purchase_preview.get("airline_name_return")
    return_flight = purchase_preview.get("flight_number_return")
    return_departure = purchase_preview.get("departure_date_time_return")
    return_travel = purchase_preview.get("travel_class_return")
    if return_airline and return_flight and return_departure and return_travel:
        from_ticket = dbmanager_customer.getTicketPrice(return_airline, return_flight,
                                                        return_departure, return_travel)
        print(f"\n{from_ticket=}")
        error = from_ticket.get("error", None)
        if error:
            return render_template("purchasePreview.html", error=error)
        session["sold_price_return"] = from_ticket["price"]
        
    else:
        from_ticket = None
    
    name = session.get("name")
    username = session["username"]
    
    return render_template("purchasePreview.html", to_ticket=to_ticket, from_ticket=from_ticket, name=name, username=username)

@app.route('/purchase_tickets', methods=['POST'])
def purchaseTickets():
    session.pop("error", None)
    session.pop("purchaseStatus", None)
    purchase = purchase_parser.parse_args()
    purchase["customer_email"] = session.get("username")
    sold_price = session["sold_price"]
    sold_price_return = session.get("sold_price_return")
    success = dbmanager_customer.purchaseTicketsDict(purchase, sold_price, sold_price_return)
    purchased = []
    for tickets in success:
        status = tickets.get("success")
        if status:
            purchased.append(status)
        else: 
            error = tickets.get("error", "Error handling ticket purchase. Please try again later")
            session.pop("purchaseStatus", None)
            session["error"] = error

    if purchased:
        session.pop("error", None)
        purchaseStatus = f"Purchasing successful! Ticket ID is {purchased}"
        session["purchaseStatus"] = purchaseStatus
        return render_template("purchaseSuccess.html", purchaseStatus=purchaseStatus)
        
    return redirect(url_for("purchaseTicketsPreview"))

@app.route('/manageFlights')
def manageFlights():
    myFlights = viewMyFlights() # all flights, not just upcoming
    cancelTrip = session.get("cancelTrip")
    rateTrip = session.get("rateTrip")
    error = session.get("error")
    return render_template('manageFlights.html', myFlights=myFlights, cancelTrip=cancelTrip, rateTrip=rateTrip, error=error)

# 4. CANCEL TRIP 
@app.route('/cancel_trip', methods=['POST'])
def cancelTrip():
    if not session.get("username"):
        return None # todo render page with error 
    if request.method == 'POST':
        ticketID = request.form["ticketID"]
        cancelTrip = dbmanager_customer.cancelTrip(session["username"], ticketID)
        session["cancelTrip"] = cancelTrip.get("success", None)
        session["error"] = cancelTrip.get("error", None)
        return redirect(url_for("manageFlights"))

# 5. GIVE RATINGS AND COMMENTS
@app.route('/rate_and_comment', methods=['POST'])
def rateAndComment():
    if not session.get("username"):
            return None # todo render page with error 
    if request.method == 'POST':
        ratings_comments = rate_comment_parser.parse_args()
        response = dbmanager_customer.giveRatingsAndComments(session["username"], ratings_comments)
        print(f"{response=}")
        if response.get("success"):
            session["rateTrip"] = response["success"]
        else: 
            session["error"] = response.get("error", "Trouble rating flight, try again later.")
            print(session["error"])
        return redirect(url_for("manageFlights"))

# 6. TRACK MY SPENDING
@app.route('/track_my_spending/default', methods=['GET'])
def trackMySpendingDefault():
    if not session.get("username"):
            return None # todo render page with error 
    if request.method == 'GET':
        mySpending = dbmanager_customer.trackSpending(session["username"])
        session["error"] = mySpending.get("error", None)
        session["mySpending"] = mySpending
        return redirect(url_for("customerHome"))

@app.route('/track_my_spending', methods=['POST'])
def trackMySpending():
    if not session.get("username"):
        return None # todo render page with error 
    if request.method == 'POST':
        start = request.form["start"]
        end = request.form["end"]
        mySpending = dbmanager_customer.trackSpending(session["username"], start, end)
        session["error"] = mySpending.get("error", None)
        session["mySpending"] = mySpending
        return redirect(url_for("customerHome"))

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
    createdFlight = session.get("createdFlight")
    createdTickets = session.get("createdTickets")
    return render_template('createFlight.html', message=message, error=error, createdFlight=createdFlight, createdTickets=createdTickets)

@app.route('/flights', methods=['POST'])
def flights():
    if not session.get("username"):
        return createFlight("Login first")
    if request.method == 'POST':
        flight = flight_parser.parse_args()
        success = dbmanager.createFlight(flight, session["username"])
        session["createdFlight"] = success
        return redirect(url_for("createFlight"))

@app.route('/create_tickets', methods=['POST'])
def createTickets():
    if not session.get("username"):
        return createFlight(error="Login first")
    if request.method == 'POST':
        print(request.form)
        ticketsToCreate = create_tickets_parser.parse_args()
        success = dbmanager.createTickets(ticketsToCreate, session["username"])
        if success:
            createdTickets = "Success creating tickets for purchase"
            session["createdTickets"] = createdTickets
            error = None
        else:
            error = "Failed to create tickets, please try again later"
            return createFlight(error=error)
        return redirect(url_for("createFlight"))
        

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
        airline = request.form['airline_name']
        
        message = dbmanager.changeFlightStatus(status, flight_number, departure_date_time, airline, session["username"])
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
    flightRevenue = session.get("flightRevenue")
    purchaseRevenue = session.get("purchaseRevenue")
    travel_class_revenue = session.get("travel_class_revenue")
    monthDestinations = session.get("monthDestinations")
    yearDestinations = session.get("yearDestinations")
    return render_template("viewReports.html", airline=session["airline"], revenueTravelClass=revenueTravelClass, report=report, flightRevenue=flightRevenue, purchaseRevenue=purchaseRevenue, travel_class_revenue=travel_class_revenue, monthDestinations=monthDestinations, yearDestinations=yearDestinations)

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
@app.route('/viewRevenue/flight/date', methods=['POST'])
def viewRevenueFlight(): 
    if not session.get("username"):
        return None # todo render page with error
    if request.method == 'POST':
        start = request.form["start"]
        end = request.form["end"]
        revenue = dbmanager.viewRevenue(start, end, session["username"])
        session["flightRevenue"] = revenue
        print(revenue)
        return redirect(url_for("viewReports"))
    
@app.route('/viewRevenue/purchase/date', methods=['POST'])
def viewRevenuePurchase(): 
    if not session.get("username"):
        return None # todo render page with error
    if request.method == 'POST':
        start = request.form["start"]
        end = request.form["end"]
        revenue = dbmanager.viewRevenue2(start, end, session["username"])
        session["purchaseRevenue"] = revenue
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
    flight_status = session.get("status")
    return render_template('home.html', username=username, flights=flights, returnFlights=returnFlights, flight_status=flight_status)

@app.route('/staffHome')
def staffHome():
    username = session['username']
    name = session.get('name')
    airline = session["airline"]
    flights = session.get("flights")
    status = session.get("status")
    ratings = session.get("ratings")
    mostFrequentFlyer = session.get("mostFrequentFlyer")
    customer_flights = session.get("customer_flights")
    returnFlights = session.get("returnFlights")
    return render_template('staffHome.html', username=username, name=name, flights=flights, airline=airline, flight_status=status, ratings=ratings, mostFrequentFlyer=mostFrequentFlyer, customer_flights=customer_flights, returnFlights=returnFlights)

@app.route('/customerHome')
def customerHome():
    username = session.get('username')
    name = session.get('name')
    flights = session.get("flights")
    returnFlights = session.get("returnFlights")
    flight_status = session.get("status")
    purchaseStatus = session.get("purchaseStatus")
    error = session.get("error")
    myFlights = viewMyUpcomingFlights()
    mySpending = session.get("mySpending")
    print(f"{mySpending=}")
    return render_template('customerHome.html', username=username, name=name, flights=flights, returnFlights=returnFlights, flight_status=flight_status, purchaseStatus=purchaseStatus, error=error, myFlights=myFlights, mySpending=mySpending)

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
