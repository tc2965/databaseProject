import pymysql.cursors
import os 
from dotenv import load_dotenv
from utils import CUSTOMER, STAFF
import hashlib
from datetime import datetime
from dateutil.relativedelta import *

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


def checkUserExistsInDb(typeUser, field, username, cursor):
	#executes query
    query = "SELECT * FROM %s WHERE %s = '%s'" % (typeUser, field, username)
    cursor.execute(query)
	#stores the results in a variable
    data = cursor.fetchone()
	#use fetchall() if you are expecting more than 1 data row
    return data
        
def checkUserLogin(typeUser, username, password):
    conn = createConnection()
    cursor = conn.cursor()
    # incoming pass must be hashed to check
    # stored pass can't be decrypted (md5 is one way hash)
    password = hashlib.md5(password.encode()).hexdigest() 
    if typeUser == "customer":
        # customers don't use username
        query = "SELECT * FROM %s WHERE email = '%s' AND customer_password = '%s'" % (typeUser, username, password)
    elif typeUser == "airline_staff":
        query = "SELECT * FROM %s WHERE username = '%s' AND user_password = '%s'" % (typeUser, username, password)
    cursor.execute(query)
    data = cursor.fetchone()
    cursor.close()
    return data

def registerCustomer(customer): 
    """
    dict[email, name, ...]
    """
    conn = createConnection()
    cursor = conn.cursor()
    exists = checkUserExistsInDb("customer", "email", customer["email"], cursor)
    if (exists): 
        cursor.close()
        return False 
    else:
        password = customer["password"]
        customer["password"] = hashlib.md5(password.encode()).hexdigest()
        
        # todo - I'm pretty sure there's a better way of writing this
        # Tried it another way with string concatenation but it felt dumb
        insertCustomer = f"INSERT INTO customer VALUES ('%(email)s', '%(name)s', '%(password)s', '%(building_number)s', '%(street)s', '%(city)s', '%(state)s', '%(phone_number)s', '%(passport_number)s', '%(passport_expiration)s', '%(passport_country)s', '%(date_of_birth)s' )" % customer
        cursor.execute(insertCustomer)
        conn.commit() 
        cursor.close()
        return customer["email"]

def registerStaff(staff): 
    """
    dict[email, name, ...]
    """
    conn = createConnection()
    cursor = conn.cursor()
    exists = checkUserExistsInDb("airline_staff", "username", staff["username"], cursor)
    if (exists): 
        cursor.close()
        return False 
    else: 
        password = staff["password"]
        staff["password"] = hashlib.md5(password.encode()).hexdigest()
        insertStaff = f"INSERT INTO airline_staff VALUES ('%(username)s', '%(password)s', '%(first_name)s', '%(last_name)s', '%(date_of_birth)s', '%(airline)s')" % staff
        cursor.execute(insertStaff)
        conn.commit()
        # now insert phone
        insertStaffPhone = f"INSERT INTO airline_staff_phones VALUES ('%(username)s', '%(phone_number)s')" % staff
        cursor.execute(insertStaffPhone)
        conn.commit() 
        cursor.close()
        return staff["username"]

def searchFlights(source, destination, departure_date):
    conn = createConnection()
    cursor = conn.cursor()
    # this query is wrong 
    query = f"SELECT * FROM flight WHERE departure_airport_code = '%s' AND arrival_airport_code = '%s' AND departure_date_time > '%s'" % (source, destination, departure_date)
    cursor = conn.cursor() 
    cursor.execute(query)
    matchingFlights = cursor.fetchall()
    cursor.close()
    return {"data": matchingFlights}

# AIRLINE STAFF USE CASE
# 1. VIEW FUTURE FLIGHTS WITHIN 30 DAYS
def findFutureAirlineFlightsTime(start, end, username): 
    conn = createConnection() 
    cursor = conn.cursor()
    staff = checkUserExistsInDb("airline_staff", "username", username, cursor)
    airline = staff["airline_name"]
    today = datetime.today()
    if start is None and end is None: 
        start = today.strftime("%Y-%m-%d")
        end = (today + relativedelta(months=3)).strftime("%Y-%m-%d")
    elif start is None: 
        start = today.strftime("%Y-%m-%d")
    elif end is None:
        end = today.strftime("%Y-%m-%d")
    query = f"SELECT * FROM flight WHERE (departure_date_time BETWEEN '%s' AND '%s') AND airline_name = '%s'" % (start, end, airline)
    cursor.execute(query)
    flights = cursor.fetchall() 
    cursor.close() 
    return {"data": flights}

# 1. VIEW FUTURE FLIGHTS BY AIRPORTS
def findFutureAirlineFlightsAirport(way_type, airport, username): 
    conn = createConnection() 
    cursor = conn.cursor()
    staff = checkUserExistsInDb("airline_staff", "username", username, cursor)
    airline = staff["airline_name"]
    if way_type == "source":
        query = f"SELECT * FROM flight WHERE departure_airport_code = '%s' AND airline_name = '%s'" % (airport, airline)
    elif way_type == "destination": 
        query = f"SELECT * FROM flight WHERE arrival_airport_code = '%s' AND airline_name = '%s'" % (airport, airline)
    cursor.execute(query)
    flights = cursor.fetchall() 
    cursor.close() 
    return {"data" : flights}

# 2. CREATE NEW FLIGHTS 
def createFlight(flight): 
    conn = createConnection() 
    cursor = conn.cursor()
    query = f"INSERT INTO flight VALUES ('%(flight_number)s', '%(airplane_id)s', '%(departure_date_time)s', '%(departure_airport_code)s', '%(arrival_date_time)s', '%(arrival_airport_code)s', '%(base_price)s', '%(status)s', '%(airline_name)s')" % flight
    cursor.execute(query)
    conn.commit() 
    cursor.close() 
    return flight["flight_number"]

# 3. CHANGE FLIGHT STATUS
def changeFlightStatus(status, flight_number, departure_date_time, username): 
    conn = createConnection()
    cursor = conn.cursor() 
    staff = checkUserExistsInDb("airline_staff", "username", username, cursor)
    airline = staff["airline_name"]
    updateFlightStatus = f"UPDATE flight SET status = '%s' WHERE flight_number = '%s' AND departure_date_time = '%s' AND airline_name = '%s'" % (status, flight_number, departure_date_time, airline)
    cursor.execute(updateFlightStatus)
    conn.commit() 
    cursor.close()
    return f"Changing flight #{flight_number} successful"

# 4. ADD AIRPLANE 
def addAirplane(airplane, username): 
    conn = createConnection()
    cursor = conn.cursor() 
    staff = assertStaffPermission(username, airplane["airline_name"], cursor)
    if not staff: 
        return None # todo raise 401 forbidden, trying to add an airplane outside of own company
    insertAirplane = f"INSERT INTO airplane VALUES ('%(ID)s', '%(airline_name)s', '%(number_of_seats)s', '%(manufacturer)s', '%(age)s')" % airplane
    cursor.execute(insertAirplane)
    conn.commit() 
    cursor.close()
    id = airplane["ID"]
    return f"Adding airplane {id} successful"

# 5. ADD AIRPORT
def addAirport(airport):
    conn = createConnection()
    cursor = conn.cursor()
    insertAirport = f"INSERT INTO airport VALUES ('%(airport_code)s', '%(name)s', '%(city)s', '%(country)s', '%(type)s')" % airport
    cursor.execute(insertAirport)
    conn.commit()
    cursor.close()
    code = airport["airport_code"]
    return f"Adding airport {code} successful"

# 6. VIEW FLIGHT RATINGS 
def viewFlightRatings(flight_number, username):
    conn = createConnection()
    cursor = conn.cursor() 
    findFlight = f"SELECT * FROM flight WHERE flight_number='%s'" % flight_number
    cursor.execute(findFlight)
    flights = cursor.fetchall() 
    airline = flights[0]["airline_name"]
    
    staff = assertStaffPermission(username, airline, cursor)
    if not staff:
        return None # todo raise 401 forbidden, trying to see ratings outside of own company
    query = f"SELECT * FROM ratings LEFT JOIN ticket ON ratings.ticket_id = ticket.ID WHERE flight_number = '%s'" % flight_number
    cursor.execute(query)
    ratings = cursor.fetchall()
    cursor.close()
    return {"data": ratings}

# 7. VIEW MOST FREQUENT CUSTOMER
def viewMostFrequentCustomer(username):
    conn = createConnection()
    cursor = conn.cursor()
    staff = checkUserExistsInDb("airline_staff", "username", username, cursor)
    airline = staff["airline_name"]
    # todo query
    query = "SELECT customer_email, COUNT(ticket_id) as trips FROM ticket JOIN purchases ON ticket.ID = purchases.ticket_id GROUP BY customer_email ORDER BY trips DESC LIMIT 1"
    cursor.execute(query)
    mostFrequentFlyer = cursor.fetchone() 
    cursor.close() 
    return {"mostFrequentFlyer": mostFrequentFlyer}
    
# 8. VIEW REPORTS 
def viewReportDate(start, end, username):
    conn = createConnection()
    cursor = conn.cursor()
    staff = checkUserExistsInDb("airline_staff", "username", username, cursor)
    airline = staff["airline_name"]
    query = f"SELECT flight_number, COUNT(ticket_id) AS tickets_sold FROM purchases JOIN ticket ON purchases.ticket_id = ticket.ID WHERE airline_name = '%s' AND date_time BETWEEN '%s' AND '%s' GROUP BY flight_number;" % (airline, start, end)
    cursor.execute(query)
    numTicket = cursor.fetchall()
    cursor.close()
    return {"data": numTicket}

# 9. VIEW REVENUE
def viewRevenue(start, end, username):
    # create connection and grab airline
    conn = createConnection()
    cursor = conn.cursor()
    staff = checkUserExistsInDb("airline_staff", "username", username, cursor)
    airline = staff["airline_name"]
    
    totalBasePriceQuery = f"SELECT SUM(base_price) as price FROM (flight NATURAL JOIN ticket) WHERE airline_name = '%s' AND (departure_date_time BETWEEN '%s' AND '%s')" % (airline, start, end)
    cursor.execute(totalBasePriceQuery)
    totalBasePrice = cursor.fetchone()["price"]
    
    totalSoldPriceQuery = f"SELECT SUM(sold_price) as price FROM ticket RIGHT JOIN purchases ON ticket.ID = purchases.ticket_id WHERE airline_name = '%s' AND (date_time BETWEEN '%s' AND '%s')" % (airline, start, end)
    cursor.execute(totalSoldPriceQuery)
    totalSoldPrice = cursor.fetchone()["price"]
    cursor.close()
    return {"revenue" : totalSoldPrice - totalBasePrice}

# 10. VIEW REVENUE TRAVEL CLASS  
def viewRevenueTravelClass(travel_class, username):
    # create connection and grab airline
    conn = createConnection()
    cursor = conn.cursor()
    staff = checkUserExistsInDb("airline_staff", "username", username, cursor)
    airline = staff["airline_name"]

    totalSoldPriceQuery = f"SELECT travel_class, SUM(sold_price) as price FROM ticket JOIN purchases ON ticket.ID = purchases.ticket_id WHERE airline_name = '%s' GROUP BY travel_class" % (airline)
    cursor.execute(totalSoldPriceQuery)
    totalSoldPrice = cursor.fetchall()
    cursor.close()
    return {"data":totalSoldPrice}
    
# 11. VIEW TOP DESTINATIONS
def viewTopDestinations(period, username):
    # create connection and grab airline
    conn = createConnection()
    cursor = conn.cursor()
    staff = checkUserExistsInDb("airline_staff", "username", username, cursor)
    airline = staff["airline_name"]
    if period == "month":
        start = datetime.today() + relativedelta(months=-3)
    else:
        start = datetime.today() + relativedelta(years=-1)
    end = datetime.today()
    
    countAirportQuery = "CREATE VIEW airport_count AS SELECT arrival_airport_code AS airport_code, COUNT(DISTINCT id) AS tickets_sold FROM ticket NATURAL JOIN flight WHERE airline_name = '%s' AND departure_date_time BETWEEN '%s' AND '%s' GROUP BY arrival_airport_code ORDER BY tickets_sold DESC;" % (airline, start, end)
    cursor.execute(countAirportQuery)
    
    orderDestinationsQuery = "SELECT city, country, tickets_sold FROM airport_count NATURAL JOIN airport GROUP BY city, country ORDER BY tickets_sold DESC LIMIT 3"
    cursor.execute(orderDestinationsQuery)
    cityCountryTicketsSold = cursor.fetchall()
    deleteViewQuery = "DROP view airport_count;"
    cursor.execute(deleteViewQuery)
    cursor.close()
    return {"data": cityCountryTicketsSold}

def assertStaffPermission(username, airline, cursor): 
    staff = checkUserExistsInDb("airline_staff", "username", username, cursor)
    if staff["airline_name"] == airline:
        return staff 
    else:
        return None


