import pymysql.cursors
import os 
from dotenv import load_dotenv
import hashlib
from datetime import datetime
from dateutil.relativedelta import *
from flask import abort

load_dotenv()
host = os.environ.get("HOST")
user = os.environ.get("USER")
password = os.environ.get("PASSWORD")
db = os.environ.get("DB")
port = int(os.environ.get("PORT"))
print(host, user, password, db)


def createConnection():
    return pymysql.connect(host=host,
                       port=port,
                       user=user,
                       password=password,
                       db=db,
                       charset='utf8mb4',
                       cursorclass=pymysql.cursors.DictCursor, 
                       max_allowed_packet=16777216, 
                       connect_timeout=100)

def executeQuery(query, params=None, fetchOne=False): 
    print(query)
    print(params)
    try:
        conn = createConnection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        if fetchOne:
            data = cursor.fetchone() 
        else: 
            data = cursor.fetchall()
        cursor.close() 
        return data
    except Exception as e: 
        print(e)
        print(query)
        print(params)
    
def executeCommitQuery(query, params): 
    print(query)
    print(params)
    try: 
        conn = createConnection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        cursor.close()
    except Exception as e:
        print(e)
        print(query)
        print(params)
    

def checkUserExistsInDb(typeUser, username):
	#executes query
    if typeUser == "customer":
        query = "SELECT * FROM customer WHERE email = %s"
    else: 
        query = "SELECT * FROM airline_staff WHERE username = %s"
    params = (username)
    data = executeQuery(query, params, True)
    return data
        
def checkUserLogin(typeUser, username, password):
    # incoming pass must be hashed to check
    # stored pass can't be decrypted (md5 is one way hash)
    password = hashlib.md5(password.encode()).hexdigest() 
    if typeUser == "customer":
        # customers don't use username
        query = "SELECT * FROM customer WHERE email = %s AND customer_password = %s"
    elif typeUser == "airline_staff":
        query = "SELECT * FROM airline_staff WHERE username = %s AND user_password = %s"
    params = (username, password)
    data = executeQuery(query, params, True)
    return data

def registerCustomer(customer): 
    """
    dict[email, name, ...]
    """
    exists = checkUserExistsInDb("customer", customer["email"])
    if (exists): 
        return False 
    else:
        password = customer["password"]
        customer["password"] = hashlib.md5(password.encode()).hexdigest()
        
        # todo - I'm pretty sure there's a better way of writing this
        # Tried it another way with string concatenation but it felt dumb
        insertCustomer = "INSERT INTO customer VALUES (%(email)s, %(name)s, %(password)s, %(building_number)s, %(street)s, %(city)s, %(state)s, %(phone_number)s, %(passport_number)s, %(passport_expiration)s, %(passport_country)s, %(date_of_birth)s)"
        params = customer
        executeCommitQuery(insertCustomer, params)
        return customer["email"]

def registerStaff(staff): 
    """
    dict[email, name, ...]
    """
    exists = checkUserExistsInDb("airline_staff", staff["username"])
    if (exists): 
        return False 
    else: 
        password = staff["password"]
        staff["password"] = hashlib.md5(password.encode()).hexdigest()
        insertStaff = "INSERT INTO airline_staff VALUES (%(username)s, %(password)s, %(first_name)s, %(last_name)s, %(date_of_birth)s, %(airline)s)"
        params = staff
        executeCommitQuery(insertStaff, params)
        # now insert phone
        insertStaffPhone = "INSERT INTO airline_staff_phones VALUES (%(username)s, %(phone_number)s)"
        executeCommitQuery(insertStaffPhone, staff)
        return staff["username"]

# 1. VIEW PUBLIC INFO A 
# for round trips, just use this endpoint again and make departure = arrival of the first result
def searchFlights(source, destination, departure_date):
    query = "SELECT * FROM flight WHERE departure_airport_code = %s AND arrival_airport_code = %s AND departure_date_time > %s"
    params = (source, destination, departure_date)
    matchingFlights = executeQuery(query, params)
    return {"data": matchingFlights}

# 1. VIEW PUBLIC INFO B
def viewFlightStatus(airline, flight_number, departure, arrival=None):
    if arrival: 
        query = "SELECT status FROM flight WHERE airline_name = %s AND flight_number = %s AND departure_date_time >= %s AND arrival_date_time >= %s"
        params = (airline, flight_number, departure, arrival)
    else:
        query = "SELECT status FROM flight WHERE airline_name =%s AND flight_number = %s AND departure_date_time >= %s"
        params = (airline, flight_number, departure)
    status = executeQuery(query, params, True)
    return {"status": status}

# AIRLINE STAFF USE CASE
# 1. VIEW FUTURE FLIGHTS WITHIN 30 DAYS
def findFutureAirlineFlightsTime(start, end, username): 
    staff = checkUserExistsInDb("airline_staff", username)
    airline = staff["airline_name"]
    today = datetime.today()
    if start is None and end is None: 
        start = today.strftime("%Y-%m-%d")
        end = (today + relativedelta(months=3)).strftime("%Y-%m-%d")
    elif start is None: 
        start = today.strftime("%Y-%m-%d")
    elif end is None:
        end = today.strftime("%Y-%m-%d")
    query = "SELECT * FROM flight WHERE (departure_date_time BETWEEN %s AND %s) AND airline_name = %s"
    params = (start, end, airline)
    flights = executeQuery(query, params)
    return {"data": flights}

# 1. VIEW FUTURE FLIGHTS BY AIRPORTS
def findFutureAirlineFlightsAirport(way_type, airport, username): 
    staff = checkUserExistsInDb("airline_staff", username)
    airline = staff["airline_name"]
    if way_type == "source":
        query = "SELECT * FROM flight WHERE departure_airport_code = %s AND airline_name = %s"
    elif way_type == "destination": 
        query = "SELECT * FROM flight WHERE arrival_airport_code = %s AND airline_name = %s"
    params = (airport, airline)
    flights = executeQuery(query, params)
    return {"data" : flights}

# 2. CREATE NEW FLIGHTS 
def createFlight(flight): 
    query = "INSERT INTO flight VALUES (%(flight_number)s, %(airplane_id)s, %(departure_date_time)s, %(departure_airport_code)s, %(arrival_date_time)s, %(arrival_airport_code)s, %(base_price)s, %(status)s, %(airline_name)s)"
    params = flight
    executeCommitQuery(query, params)
    number = flight["flight_number"]
    return f"Creating flight {number} successful"

# 3. CHANGE FLIGHT STATUS
def changeFlightStatus(status, flight_number, departure_date_time, username): 
    staff = checkUserExistsInDb("airline_staff", username)
    airline = staff["airline_name"]
    updateFlightStatus = "UPDATE flight SET status = %s WHERE flight_number = %s AND departure_date_time = %s AND airline_name = %s"
    params = (status, flight_number, departure_date_time, airline)
    executeCommitQuery(updateFlightStatus, params)
    return f"Changing flight #{flight_number} successful"

# 4. ADD AIRPLANE 
def addAirplane(airplane, username): 
    staff = assertStaffPermission(username, airplane["airline_name"])
    insertAirplane = "INSERT INTO airplane VALUES (%(ID)s, %(airline_name)s, %(number_of_seats)s, %(manufacturer)s, %(age)s)"
    params = airplane
    executeCommitQuery(insertAirplane, params)
    id = airplane["ID"]
    return f"Adding airplane {id} successful"

# 5. ADD AIRPORT
def addAirport(airport):
    insertAirport = "INSERT INTO airport VALUES (%(airport_code)s, %(name)s, %(city)s, %(country)s, %(type)s)"
    params = airport
    executeCommitQuery(insertAirport, params)
    code = airport["airport_code"]
    return f"Adding airport {code} successful"

# 6. VIEW FLIGHT RATINGS 
def viewFlightRatings(flight_number, username):
    findFlight = "SELECT * FROM flight WHERE flight_number = %s"
    params = flight_number
    flights = executeQuery(findFlight, params)
    airline = flights[0]["airline_name"]
    
    assertStaffPermission(username, airline)
    query = "SELECT * FROM ratings LEFT JOIN ticket ON ratings.ticket_id = ticket.ID WHERE flight_number = %s"
    params = flight_number
    ratings = executeQuery(query, params)
    return {"data": ratings}

# 7. VIEW MOST FREQUENT CUSTOMER
def viewMostFrequentCustomer(username):
    staff = checkUserExistsInDb("airline_staff", username)
    airline = staff["airline_name"]
    query = "SELECT customer_email, COUNT(ticket_id) as trips FROM ticket JOIN purchases ON ticket.ID = purchases.ticket_id WHERE airline_name = %s GROUP BY customer_email ORDER BY trips DESC LIMIT 1"
    mostFrequentFlyer = executeQuery(query, airline)
    return {"mostFrequentFlyer": mostFrequentFlyer}

def viewCustomerFlights(customer_email, username):
    staff = checkUserExistsInDb("airline_staff", username)
    airline = staff["airline_name"]
    query = "SELECT flight_number FROM purchases INNER JOIN ticket ON purchases.ticket_id = ticket.ID AND customer_email = %s AND airline_name = %s"
    params = (customer_email, airline)
    flights = executeQuery(query, params)
    return {"data": flights}
    
# 8. VIEW REPORTS 
def viewReportDate(start, end, username):
    staff = checkUserExistsInDb("airline_staff", username)
    airline = staff["airline_name"]
    query = "SELECT flight_number, COUNT(ticket_id) AS tickets_sold FROM purchases JOIN ticket ON purchases.ticket_id = ticket.ID WHERE airline_name = %s AND date_time BETWEEN %s AND %s GROUP BY flight_number;" 
    params = (airline, start, end)
    numTicket = executeQuery(query, params)
    return {"data": numTicket}

# 9. VIEW REVENUE
def viewRevenue(start, end, username):
    # create connection and grab airline
    staff = checkUserExistsInDb("airline_staff", username)
    airline = staff["airline_name"]
    
    totalBasePriceQuery = "SELECT SUM(base_price) as totalbaseprice FROM (flight NATURAL JOIN ticket) WHERE airline_name = %s AND (departure_date_time BETWEEN %s AND %s)"
    params = (airline, start, end)
    totalBasePrice = executeQuery(totalBasePriceQuery, params, True)["totalbaseprice"]
    
    totalSoldPriceQuery = "SELECT SUM(sold_price) as totalsoldprice FROM ticket RIGHT JOIN purchases ON ticket.ID = purchases.ticket_id WHERE airline_name = %s AND (date_time BETWEEN %s AND %s)"
    totalSoldPrice = executeQuery(totalSoldPriceQuery, params, True)["totalsoldprice"]
    
    revenue = totalSoldPrice - totalBasePrice
    data = {"totalbaseprice": totalBasePrice,
            "totalsoldprice": totalSoldPrice, 
            "revenue": revenue, 
            "airline": airline, 
            "period_start": start,
            "period_end": end}
    return {"data": data}

# 10. VIEW REVENUE TRAVEL CLASS  
def viewRevenueTravelClass(username):
    staff = checkUserExistsInDb("airline_staff", username)
    airline = staff["airline_name"]

    createBaseView = "CREATE VIEW base_travel AS SELECT travel_class, SUM(base_price) as base_cost FROM ticket INNER JOIN flight ON ticket.flight_number = flight.flight_number AND ticket.departure_date_time = flight.departure_date_time AND ticket.airline_name = %s GROUP BY travel_class;"
    params = airline    
    executeQuery(createBaseView, params)
    
    createSoldView = "CREATE VIEW sold_travel AS SELECT travel_class, SUM(sold_price) as sold_price FROM ticket JOIN purchases ON ticket.ID = purchases.ticket_id WHERE airline_name = %s GROUP BY travel_class;"
    executeQuery(createSoldView, params)
    
    revenueQuery = "SELECT sold_travel.travel_class, base_cost, sold_price, (sold_price - base_cost) AS revenue FROM base_travel INNER JOIN sold_travel ON base_travel.travel_class = sold_travel.travel_class;"
    revenue = executeQuery(revenueQuery)
    
    dropBaseViews = "DROP VIEW base_travel;"
    executeQuery(dropBaseViews)
    dropSoldView = "DROP VIEW sold_travel;"
    executeQuery(dropSoldView)

    return {"data":revenue}
    
# 11. VIEW TOP DESTINATIONS
def viewTopDestinations(period, username):
    staff = checkUserExistsInDb("airline_staff", username)
    airline = staff["airline_name"]
    if period == "month":
        start = datetime.today() + relativedelta(months=-3)
    else:
        start = datetime.today() + relativedelta(years=-1)
    end = datetime.today()
    
    viewCountAirportQuery = "CREATE VIEW airport_count AS SELECT arrival_airport_code AS airport_code, COUNT(DISTINCT id) AS tickets_sold FROM ticket NATURAL JOIN flight WHERE airline_name = %s AND departure_date_time BETWEEN %s AND %s GROUP BY arrival_airport_code ORDER BY tickets_sold DESC;"
    params = (airline, start, end)
    executeQuery(viewCountAirportQuery, params)
    
    orderDestinationsQuery = "SELECT city, country, tickets_sold FROM airport_count NATURAL JOIN airport GROUP BY city, country ORDER BY tickets_sold DESC LIMIT 3"
    cityCountryTicketsSold = executeQuery(orderDestinationsQuery)
    
    deleteViewQuery = "DROP view airport_count;"
    executeQuery(deleteViewQuery)
    return {"data": cityCountryTicketsSold}

def assertStaffPermission(username, airline): 
    staff = checkUserExistsInDb("airline_staff", username)
    if staff["airline_name"] == airline:
        return staff 
    else:
        otherAirline = staff["airline_name"]
        print(f"{otherAirline} employee {username} does not have access to {airline}")
        return abort(403, f"{otherAirline} employee {username} does not have access to {airline}")
