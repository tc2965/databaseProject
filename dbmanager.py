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
        return False
    
def executeCommitQuery(query, params=None): 
    print(query)
    print(params)
    try: 
        conn = createConnection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        rows = cursor.rowcount
        cursor.close()
        return rows
    except Exception as e:
        print(e)
        print(query)
        print(params)
        return False
    

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
        return (staff["username"], staff["airline"])

# 1. VIEW PUBLIC INFO A 
# for round trips, just use this endpoint again and make departure = arrival of the first result
def searchFlights(source, destination, departure_date):
    query = "SELECT * FROM flight WHERE departure_airport_code = %s AND arrival_airport_code = %s AND departure_date_time > %s"
    params = (source, destination, departure_date)
    matchingFlights = executeQuery(query, params)
    return matchingFlights

# 1. VIEW PUBLIC INFO B
def viewFlightStatus(airline, flight_number, departure, arrival=None):
    if arrival: 
        query = "SELECT status, flight_number, departure_date_time FROM flight WHERE airline_name = %s AND flight_number = %s AND departure_date_time >= %s AND arrival_date_time >= %s"
        params = (airline, flight_number, departure, arrival)
    else:
        query = "SELECT status, flight_number, departure_date_time FROM flight WHERE airline_name =%s AND flight_number = %s AND departure_date_time >= %s"
        params = (airline, flight_number, departure)
    status = executeQuery(query, params, True)
    return status

# AIRLINE STAFF USE CASE
# 1. VIEW FUTURE FLIGHTS WITHIN 30 DAYS
def findFutureAirlineFlightsTime(start, end, username): 
    # This handles the default 30 day view and queries for specific dates
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
def createFlight(flight, username): 
    staff = assertStaffPermission(username, flight["airline_name"])
    query = "INSERT INTO flight VALUES (%(flight_number)s, %(airplane_id)s, %(departure_date_time)s, %(departure_airport_code)s, %(arrival_date_time)s, %(arrival_airport_code)s, %(base_price)s, %(status)s, %(airline_name)s)"
    params = flight
    success = executeCommitQuery(query, params)
    number = flight["flight_number"]
    return f"Creating flight {number} successful" if success else success

def createTickets(ticketsToCreate, username): 
    print(ticketsToCreate)
    staff = assertStaffPermission(username, ticketsToCreate["airline_name"])
    economy_seats = ticketsToCreate["economy_seats"]
    business_seats = ticketsToCreate["business_seats"]
    first_seats = ticketsToCreate["first_seats"]
    flight_number = ticketsToCreate["flight_number"]
    airline_name = ticketsToCreate["airline_name"]
    departure = ticketsToCreate["departure_date_time"]
    depart = departure.replace(" ", "").replace("-", "").replace(":", "")
    airline = airline_name.upper()
    flight = flight_number.upper()
    print("dep ", depart)
    # ticket is len 20
    
    economy_ticket = "E" + flight[:3] + airline[:3] + depart[4:13] + ":"
    business_ticket = "B" + flight[:3] + airline[:3] + depart[4:13] + ":"
    first_ticket = "F" + flight[:3] + airline[:3] + depart[4:13] + ":"
    
    full_query = "INSERT INTO ticket VALUES "
    for i in range(economy_seats):
        curr_ticket = str(i).zfill(3)
        ticket = economy_ticket + curr_ticket
        query = f"('{ticket}', 'Economy', '{airline_name}', '{flight_number}', '{departure}')"
        full_query += query + ", "

    for i in range(business_seats):
        curr_ticket = str(i).zfill(3)
        ticket = business_ticket + curr_ticket
        query = f"('{ticket}', 'Business', '{airline_name}', '{flight_number}', '{departure}')"
        full_query += query + ", "
        
    for i in range(first_seats):
        curr_ticket = str(i).zfill(3)
        ticket = first_ticket + curr_ticket
        query = f"('{ticket}', 'First', '{airline_name}', '{flight_number}', '{departure}')"
        if i == first_seats - 1:
            full_query += query
        else:
            full_query += query + ", "
    success = executeCommitQuery(full_query)
    return success

# 3. CHANGE FLIGHT STATUS
def changeFlightStatus(status, flight_number, departure_date_time, airline, username): 
    staff = assertStaffPermission(username, airline)
    airline = staff["airline_name"]
    updateFlightStatus = "UPDATE flight SET status = %s WHERE flight_number = %s AND departure_date_time = %s AND airline_name = %s"
    params = (status, flight_number, departure_date_time, airline)
    success = executeCommitQuery(updateFlightStatus, params)
    if success == 0:
        return f"Changing flight #{flight_number} unsuccessful"
    return f"Changing flight #{flight_number} successful"

# 4. ADD AIRPLANE 
def addAirplane(airplane, username): 
    staff = assertStaffPermission(username, airplane["airline_name"])
    insertAirplane = "INSERT INTO airplane VALUES (%(ID)s, %(airline_name)s, %(number_of_seats)s, %(manufacturer)s, %(age)s)"
    params = airplane
    success = executeCommitQuery(insertAirplane, params)
    id = airplane["ID"]
    if success == 0:
        return f"Adding airplane #{id} unsuccessful"
    return f"Adding airplane {id} successful"

# 5. ADD AIRPORT
def addAirport(airport):
    insertAirport = "INSERT INTO airport VALUES (%(airport_code)s, %(name)s, %(city)s, %(country)s, %(type)s)"
    params = airport
    success = executeCommitQuery(insertAirport, params)
    code = airport["airport_code"]
    if success == 0:
        return f"Adding airport #{code} unsuccessful"
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
    
    averageQuery = "SELECT flight_number, AVG(rating) as avg FROM ratings LEFT JOIN ticket ON ratings.ticket_id = ticket.ID WHERE flight_number = %s GROUP BY flight_number"
    average = executeQuery(averageQuery, params, True)
    print(f"{average=}")
    ratingReport = {
        "average": average["avg"], 
        "flight_number": average["flight_number"], 
        "ratings": ratings
    }
    return ratingReport

# 7. VIEW MOST FREQUENT CUSTOMER
def viewMostFrequentCustomer(username):
    staff = checkUserExistsInDb("airline_staff", username)
    airline = staff["airline_name"]
    query = "SELECT customer_email, COUNT(DISTINCT ticket_id) as trips FROM ticket JOIN purchases ON ticket.ID = purchases.ticket_id WHERE airline_name = %s GROUP BY customer_email ORDER BY trips DESC LIMIT 1"
    mostFrequentFlyer = executeQuery(query, airline, True)
    print(mostFrequentFlyer)
    return mostFrequentFlyer

def viewCustomerFlights(customer_email, username):
    staff = checkUserExistsInDb("airline_staff", username)
    airline = staff["airline_name"]
    query = "SELECT flight_number, departure_date_time, airline_name FROM purchases INNER JOIN ticket ON purchases.ticket_id = ticket.ID AND customer_email = %s AND airline_name = %s"
    params = (customer_email, airline)
    flights = executeQuery(query, params)
    return flights
    
# 8. VIEW REPORTS 
def viewReportDate(start, end, username):
    staff = checkUserExistsInDb("airline_staff", username)
    airline = staff["airline_name"]
    query = "SELECT flight_number, COUNT(DISTINCT ticket_id) AS tickets_sold FROM purchases JOIN ticket ON purchases.ticket_id = ticket.ID WHERE airline_name = %s AND date_time BETWEEN %s AND %s GROUP BY flight_number;" 
    params = (airline, start, end)
    numTicket = executeQuery(query, params)
    return numTicket

# 9. VIEW REVENUE
def viewRevenue(start, end, username):
    # create connection and grab airline
    staff = checkUserExistsInDb("airline_staff", username)
    airline = staff["airline_name"]

    # PDF doesn't say whether to use the departure date or purchase date for the period
    totalBasePriceQuery = "SELECT SUM(base_price) as totalbaseprice FROM (flight NATURAL JOIN ticket) WHERE airline_name = %s AND (departure_date_time BETWEEN %s AND %s)"
    params = (airline, start, end)
    total_base = executeQuery(totalBasePriceQuery, params, True)["totalbaseprice"]
    
    totalSoldPriceQuery = "SELECT SUM(sold_price) as totalsoldprice FROM ticket RIGHT JOIN purchases ON ticket.ID = purchases.ticket_id WHERE airline_name = %s AND (departure_date_time BETWEEN %s AND %s)"
    total_sold = executeQuery(totalSoldPriceQuery, params, True)["totalsoldprice"]
    
    if total_sold:
        total_sold = total_sold
    else:
        total_sold = 0

    if total_base:
        total_base = total_base
    else:
        total_base = 0
    
    revenue = total_sold - total_base
    data = {"totalbaseprice": total_base,
            "totalsoldprice": total_sold, 
            "revenue": revenue, 
            "airline": airline, 
            "period_start": start,
            "period_end": end}
    return data

def viewRevenue2(start, end, username):
    staff = checkUserExistsInDb("airline_staff", username)
    airline = staff["airline_name"]
    
    # This uses the purchase date for the period
    createRevenueView = "CREATE VIEW revenue AS SELECT sold_price, base_price, date_time, flight.flight_number, flight.airline_name, flight.departure_date_time FROM flight INNER JOIN ticket ON flight.flight_number = ticket.flight_number AND flight.airline_name = %s AND flight.departure_date_time = ticket.departure_date_time INNER JOIN purchases ON ticket.ID = purchases.ticket_id WHERE (date_time BETWEEN %s AND %s)"
    params = (airline, start, end)
    
    executeQuery(createRevenueView, params)

    sold_price = "SELECT SUM(sold_price) as sold_price FROM revenue;"
    base_price = "SELECT SUM(base_price) as base_price FROM revenue;"
    total_sold = executeQuery(sold_price, None, True)["sold_price"]
    total_base = executeQuery(base_price, None, True)["base_price"]
    if total_sold:
        total_sold = total_sold
    else:
        total_sold = 0

    if total_base:
        total_base = total_base
    else:
        total_base = 0

    dropRevenueView = "DROP VIEW revenue;"
    executeQuery(dropRevenueView)
    
    data = {"totalbaseprice": total_base,
            "totalsoldprice": total_sold, 
            "revenue": total_sold - total_base, 
            "airline": airline, 
            "period_start": start,
            "period_end": end}
    
    return data


# 10. VIEW REVENUE TRAVEL CLASS  
def viewRevenueTravelClass(username):
    staff = checkUserExistsInDb("airline_staff", username)
    airline = staff["airline_name"]

    # this is assuming that the base_price of a flight is how much it costs to 
    # fly 1 customer regardless of what travel class they have
    createBaseView = "CREATE VIEW base_travel AS SELECT travel_class, SUM(base_price) as base_cost FROM ticket INNER JOIN flight ON ticket.flight_number = flight.flight_number AND ticket.departure_date_time = flight.departure_date_time AND ticket.airline_name = %s GROUP BY travel_class;"
    params = airline    
    executeQuery(createBaseView, params)
    
    createSoldView = "CREATE VIEW sold_travel AS SELECT travel_class, SUM(sold_price) as sold_price FROM ticket INNER JOIN purchases ON ticket.ID = purchases.ticket_id WHERE airline_name = %s GROUP BY travel_class;"
    executeQuery(createSoldView, params)
    
    revenueQuery = "SELECT sold_travel.travel_class as travel_class, base_cost, sold_price, (sold_price - base_cost) AS revenue FROM base_travel INNER JOIN sold_travel ON base_travel.travel_class = sold_travel.travel_class;"
    revenue = executeQuery(revenueQuery)
    
    dropBaseViews = "DROP VIEW base_travel;"
    executeQuery(dropBaseViews)
    dropSoldView = "DROP VIEW sold_travel;"
    executeQuery(dropSoldView)

    return revenue
    
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
    return cityCountryTicketsSold

def assertStaffPermission(username, airline): 
    staff = checkUserExistsInDb("airline_staff", username)
    if staff["airline_name"] == airline:
        return staff 
    else:
        otherAirline = staff["airline_name"]
        print(f"{otherAirline} employee {username} does not have access to {airline}")
        return abort(403, f"{otherAirline} employee {username} does not have access to {airline}")
