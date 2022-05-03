import pymysql.cursors
import os
from dotenv import load_dotenv
import hashlib
from datetime import date, datetime, timedelta # modified here
from dbmanager import executeQuery, executeCommitQuery

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
        query = "SELECT * FROM %s WHERE email = '%s' AND password = '%s'" % (typeUser, username, password)
    elif typeUser == "airline_staff":
        query = "SELECT * FROM %s WHERE username = '%s' AND password = '%s'" % (typeUser, username, password)
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
        print("insertCustomer:", insertCustomer)
        cursor.execute(insertCustomer)
        conn.commit()
        cursor.close()
        return customer["email"]

def searchFlights(source, destination, departure_date):
    conn = createConnection()
    cursor = conn.cursor()
    # this query is wrong
    # query = f"SELECT * FROM flight WHERE departure_airport_code = '%s' AND arrival_airport_code = '%s' AND departure_date_time > '%s'" % (source, destination, departure_date)
    # import pdb; pdb.set_trace()
    cursor.execute("""SELECT * FROM flight
    WHERE departure_airport_code = %s AND arrival_airport_code = %s AND departure_date_time > %s""", (source, destination, departure_date)) # protect malicious injection
    matchingFlights = cursor.fetchall()
    cursor.close()
    return convertToDict("flight_number", matchingFlights)

def convertToDict(field, lists):
    print(lists)
    dict = {}
    for elem in lists:
        dict[elem[field]] = elem
    print(dict)
    return dict


# print("Flights:", findFutureAirlineFlights("allison2@allison.com"))

# Customer Use case

# 1. View My flights
def viewMyFlights(email):
    conn = createConnection()
    cursor = conn.cursor()
    exists = checkUserExistsInDb("customer", "email", email, cursor)
    if (exists):
        today = date.today()
        today = today.strftime("%Y-%m-%d")
        cursor.execute("SELECT flight_number, departure_date_time, airline_name FROM ticket INNER JOIN purchases ON ticket.ID = purchases.ticket_id AND customer_email = %s;", email)
        conn.commit()
        flights = cursor.fetchall()
        cursor.close()
        return flights
    else:
        cursor.close()
        return False

# 2. Search for flights
def searchFlights_customer(source, destination, departure_date, return_date=None):
    conn = createConnection()
    cursor = conn.cursor()

    # convert code/city to code
    cursor.execute("SELECT code FROM airport WHERE code = %s OR city = %s", (source, source))
    departure_airport_code = cursor.fetchall()[0]["code"]
    cursor.execute("SELECT code FROM airport WHERE code = %s OR city = %s", (destination, destination))
    arrival_airport_code = cursor.fetchall()[0]["code"]

    if return_date == None:
        start = (datetime.strptime(departure_date,"%m/%d/%Y")).strftime("%Y-%m-%d")
        end = (datetime.strptime(departure_date,"%m/%d/%Y") + timedelta(days=1)).strftime("%Y-%m-%d")
        cursor.execute("""SELECT * FROM flight
        WHERE departure_airport_code = %s AND arrival_airport_code = %s AND (departure_date_time > %s AND departure_date_time < %s)""", (departure_airport_code, arrival_airport_code, start, end))
    else:
        start1 = (datetime.strptime(departure_date,"%m/%d/%Y")).strftime("%Y-%m-%d")
        end1 = (datetime.strptime(departure_date,"%m/%d/%Y") + timedelta(days=1)).strftime("%Y-%m-%d")
        start2 = (datetime.strptime(return_date,"%m/%d/%Y")).strftime("%Y-%m-%d")
        end2 = (datetime.strptime(return_date,"%m/%d/%Y") + timedelta(days=1)).strftime("%Y-%m-%d")
        cursor.execute("""SELECT * FROM flight
        WHERE (departure_airport_code = %s AND arrival_airport_code = %s AND (departure_date_time > %s AND departure_date_time < %s))
        OR (departure_airport_code = %s AND arrival_airport_code = %s AND (departure_date_time > %s AND departure_date_time < %s))""",
        (departure_airport_code, arrival_airport_code, start1, end1, arrival_airport_code, departure_airport_code, start2, end2))
    matchingFlights = cursor.fetchall()
    cursor.close()
    return convertToDict("flight_number", matchingFlights)

# 3. Purchase tickets (for the front end, may implement together with the "searchFlights")
def purchaseTicketsDict(purchase):
    print(purchase)
    email = purchase["customer_email"]
    airline_name = purchase["airline_name"]
    flight_number = purchase["flight_number"]
    departure_date_time = purchase["departure_date_time"]
    travel_class = purchase["travel_class"]
    card_type = purchase["card_type"]
    card_number = purchase["card_number"]
    name_on_card = purchase["name_on_card"]
    card_exp = purchase["card_expiration"]
    
    return_flight_number = purchase.get("flight_number_return")
    return_airline_name = purchase.get("airline_name_return")
    return_departure_date_time = purchase.get("departure_date_time_return") 

    to_trip = purchaseTickets(email, airline_name, flight_number, departure_date_time, travel_class, card_type, card_number, name_on_card, card_exp)
    print("Purchasing Ticket for: ", flight_number, airline_name, departure_date_time) 

    error = to_trip.get("error")
    if error: 
        return [to_trip]
    
    if return_flight_number and return_airline_name and return_departure_date_time: 
        print("Purchasing Ticket for: ", return_flight_number, return_airline_name, return_departure_date_time) 
        return_trip = purchaseTickets(email, return_airline_name, return_flight_number, return_departure_date_time, travel_class, card_type, card_number, name_on_card, card_exp)
        return [to_trip, return_trip]
    else: 
        return[to_trip]

def purchaseTickets(email, airline_name, flight_number, departure_date_time, travel_calss, card_type, card_number, name_on_card, card_exp): # various inputs through a form
    # I suppose here to be sure that two tickets are for the same flights, they must have the same airline_name, flight_number and departure_date_time (including hour-mintue-second), because one possible case is that the same flight go round trip for multiple times within a single day
    conn = createConnection()
    cursor = conn.cursor()
    exists = checkUserExistsInDb("customer", "email", email, cursor)
    if (exists):
        # decide whether the flight is on high-demand
        query = ("SELECT * FROM flight WHERE airline_name = %s AND flight_number = %s AND departure_date_time = %s")
        params = (airline_name, flight_number, departure_date_time)
        flight = executeQuery(query, params, True)
        airplane_id = flight["airplane_id"]
        cursor.execute("SELECT number_of_seats FROM airplane WHERE ID = %s", (airplane_id))
        capacity = cursor.fetchall()[0]["number_of_seats"] # flight airplane capacity

        cursor.execute("SELECT COUNT(*) from purchases WHERE ticket_id in (SELECT ID FROM ticket WHERE airline_name = %s AND flight_number = %s AND departure_date_time = %s)", (airline_name, flight_number, departure_date_time))
        count = cursor.fetchall()[0]["COUNT(*)"] # the number of tickets already sold out of this flight

        if count == capacity:
            print("No available tickets.")
            cursor.close()
            return False
        elif count >= 0.75*capacity:
            high_demand = True
        else:
            high_demand = False

        # select a ticket
        cursor.execute("""SELECT * FROM ticket WHERE airline_name = %s AND flight_number = %s AND departure_date_time = %s AND travel_class = %s AND ID not in
        (SELECT ticket_id FROM purchases)""", (airline_name, flight_number, departure_date_time, travel_calss)) # find available tickets

        tickets = cursor.fetchall()
        if len(tickets) == 0:
            error = f"No available tickets for {flight_number}"
            cursor.close()
            return {"error": error}
        ticket = tickets[0]
        ticket_id = ticket["ID"]

        # find the base price and sold price
        cursor.execute("SELECT base_price FROM flight WHERE airline_name = %s AND flight_number = %s AND departure_date_time = %s", (airline_name, flight_number, departure_date_time))
        base_price = float(cursor.fetchall()[0]["base_price"])
        if high_demand:
            sold_price = round(base_price*1.25, 2)
        else:
            sold_price = round(base_price, 2) # here I find that we did not distinguish the price between the economy class and the business class, i am not sure whether we need to modify the schema of the database to implement this function. But for simplicity, we can set the price of the business class to be like sold_price(business) = sold_price(economy)*1.3, etc.

        # get purchase time
        purchase_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # import pdb; pdb.set_trace()
        cursor.execute("INSERT INTO purchases VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", (ticket_id, sold_price, purchase_time, email, card_type, card_number, name_on_card, card_exp))
        conn.commit()
        cursor.close()
        return {"success": ticket_id}
    else:
        cursor.close()
        return {"error": "Trouble purchasing, plesae try again later"}

# 4. Cancel Trip
def cancelTrip(email, ticket_id):
    conn = createConnection()
    cursor = conn.cursor()

    exists = checkUserExistsInDb("customer", "email", email, cursor)

    if (exists):
        #import pdb; pdb.set_trace()
        cursor.execute("SELECT * FROM purchases WHERE customer_email = %s AND ticket_id = %s", (email, ticket_id))
        tickets = cursor.fetchall()
        if len(tickets) == 0:
            print("No such ticket to be cancelled.")
            cursor.close()
            return False
        else:
            cursor.execute("SELECT departure_date_time FROM ticket WHERE ID = %s", (ticket_id))
            departure_date_time = cursor.fetchall()[0]["departure_date_time"]
            now = datetime.now()
            if (departure_date_time - now) > timedelta(hours=24):
                cursor.execute("DELETE FROM purchases WHERE customer_email = %s AND ticket_id = %s", (email, ticket_id))
                conn.commit()
                cursor.close()
            else:
                print("Cancellation of a flight ticket taking place within 24 hours is not allowed.")
                cursor.close()
                return False
    else:
        cursor.close()
        return False

# 5. Give Ratings and Comment on previous flights
def giveRatingsAndComments(email, rating_comment):
    rating = rating_comment["rating"]
    comment = rating_comment["comment"]
    ticket_id = rating_comment["ticket_id"]
    
    giveRatings(email, ticket_id, rating)
    giveComments(email, ticket_id, comment)

def giveRatings(email, ticket_id, rating):
    conn = createConnection()
    cursor = conn.cursor()

    exists = checkUserExistsInDb("customer", "email", email, cursor)

    if (exists):
        #import pdb; pdb.set_trace()
        cursor.execute("SELECT * FROM purchases WHERE customer_email = %s AND ticket_id = %s", (email, ticket_id))
        purchases = cursor.fetchall()
        if len(purchases) == 0:
            print("You haven't bought such a ticket.")
            cursor.close()
            return False
        else:
            cursor.execute("SELECT * FROM ticket WHERE ID = %s", (ticket_id))
            tickets = cursor.fetchall()
            departure_date_time = tickets[0]["departure_date_time"]
            now = datetime.now()
            if departure_date_time > now:
                print("You haven't taken the flight.")
                cursor.close()
                return False
            else:
                cursor.execute("SELECT * FROM ratings WHERE customer_email = %s AND ticket_id = %s", (email, ticket_id))
                ratings = cursor.fetchall()
                if len(ratings) != 0:
                    print("You already rated the flight.")
                    cursor.close()
                    return False
                else:
                    cursor.execute("INSERT INTO ratings VALUES (%s, %s, %s)", (email, ticket_id, rating))
                    conn.commit()
                    cursor.close()
    else:
        cursor.close()
        return False

def giveComments(email, ticket_id, comment):
    conn = createConnection()
    cursor = conn.cursor()

    exists = checkUserExistsInDb("customer", "email", email, cursor)

    if (exists):
        #import pdb; pdb.set_trace()
        cursor.execute("SELECT * FROM purchases WHERE customer_email = %s AND ticket_id = %s", (email, ticket_id))
        purchases = cursor.fetchall()
        if len(purchases) == 0:
            print("You haven't bought such a ticket.")
            cursor.close()
            return False
        else:
            cursor.execute("SELECT * FROM ticket WHERE ID = %s", (ticket_id))
            tickets = cursor.fetchall()
            departure_date_time = tickets[0]["departure_date_time"]
            now = datetime.now()
            if departure_date_time > now:
                print("You haven't taken the flight.")
                cursor.close()
                return False
            else:
                cursor.execute("SELECT * FROM comments WHERE customer_email = %s AND ticket_id = %s", (email, ticket_id))
                comments = cursor.fetchall()
                if len(comments) != 0:
                    print("You already commented the flight.")
                    cursor.close()
                    return False
                else:
                    cursor.execute("INSERT INTO comments VALUES (%s, %s, %s)", (email, ticket_id, comment))
                    conn.commit()
                    cursor.close()
    else:
        cursor.close()
        return False

# 6. Track My Spending
def trackSpending(email, start_date=None, end_date=None):
    conn = createConnection()
    cursor = conn.cursor()

    exists = checkUserExistsInDb("customer", "email", email, cursor)

    if (exists):
        if start_date == None and end_date == None: # the default case
            now = datetime.now()
            one_year_ago = now - timedelta(days=365)
            six_month_ago = now - timedelta(days=183)
            if six_month_ago.month == 12:
                first_day_of_next_month = datetime(six_month_ago.year+1, 1, 1)
            else:
                first_day_of_next_month = datetime(six_month_ago.year, six_month_ago.month+1, 1)
            cursor.execute("SELECT sum(sold_price) FROM purchases WHERE customer_email = %s AND date_time >= %s", (email, one_year_ago))
            tot_spend = float(cursor.fetchall()[0]["sum(sold_price)"]) # total spend within the past year # not sure whether I should convert it to float

            cursor.execute("""SELECT YEAR(date_time), MONTH(date_time), sum(sold_price) FROM purchases
            WHERE customer_email = %s AND date_time >= %s
            GROUP BY YEAR(date_time), MONTH(date_time)""", (email, first_day_of_next_month))
            month_wise_spending = cursor.fetchall() # I left the raw dictionary here, not sure whether further processing is needed

            cursor.close()
            return tot_spend, month_wise_spending
        else:
            # if the input format of the date is like "04/30/2022", we need these two lines
            start_date = (datetime.strptime(start_date,"%m/%d/%Y")).strftime("%Y-%m-%d")
            end_date = (datetime.strptime(end_date,"%m/%d/%Y")).strftime("%Y-%m-%d")

            cursor.execute("SELECT sum(sold_price) FROM purchases WHERE customer_email = %s AND date_time >= %s AND date_time <= %s", (email, start_date, end_date))
            tot_spend = float(cursor.fetchall()[0]["sum(sold_price)"]) # total spend within the past year # not sure whether I should convert it to float

            cursor.execute("""SELECT YEAR(date_time), MONTH(date_time), sum(sold_price) FROM purchases
            WHERE customer_email = %s AND date_time >= %s AND date_time <= %s
            GROUP BY YEAR(date_time), MONTH(date_time)""", (email, start_date, end_date))
            month_wise_spending = cursor.fetchall()

            cursor.close()
            return tot_spend, month_wise_spending
    else:
        cursor.close()
        return False

# 7. Logout

#viewMyFlights("allison@allison.com")
#searchFlights_customer("NYC", "Shanghai", "04/06/2022")
#searchFlights("JFK", "PVG", "04/07/2022")
#purchaseTickets("allison@allison.com", "China Eastern", "CH200", "2022-04-06 14:00:09", "Economy", "Debit", "12345678", "allison", "12/28")
#cancelTrip("allison@allison.com", "ABC7654321")
#giveRatings("test3@yahoo.com", "XYZ7778880", 4)
#giveComments("test3@yahoo.com", "XYZ7778880", "Fair. Quite good.")
#trackSpending("test3@yahoo.com", "05/06/2020", "03/19/2023")
