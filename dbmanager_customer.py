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
        cursor.execute("SELECT purchases.ticket_id as ticket_id, flight_number, departure_date_time, airline_name, rating, comment FROM ticket INNER JOIN purchases ON ticket.ID = purchases.ticket_id AND purchases.customer_email = %s LEFT JOIN ratings ON purchases.ticket_id = ratings.ticket_id;", (email))
        conn.commit()
        flights = cursor.fetchall()
        cursor.close()
        return flights
    else:
        cursor.close()
        return False

def viewMyUpcomingFlights(email):
    conn = createConnection()
    cursor = conn.cursor()
    exists = checkUserExistsInDb("customer", "email", email, cursor)
    cursor.close()
    if not exists:
        return False
    today = datetime.today().strftime("%Y-%m-%d")
    query = "SELECT purchases.ticket_id as ticket_id, flight_number, departure_date_time, airline_name FROM ticket INNER JOIN purchases ON ticket.ID = purchases.ticket_id AND customer_email = %s AND departure_date_time > %s;"
    params = (email, today)
    flights = executeQuery(query, params)
    print(f"{flights=}")
    return flights

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

def getTicketPrice(airline_name, flight_number, departure_date_time, travel_class):
    print("getTicketPrice", airline_name, flight_number, departure_date_time, travel_class)
    # I suppose here to be sure that two tickets are for the same flights, they must have the same airline_name, flight_number and departure_date_time (including hour-mintue-second), because one possible case is that the same flight go round trip for multiple times within a single day
    # decide whether the flight is on high-demand
    flightQuery = "SELECT * FROM flight WHERE airline_name = %s AND flight_number = %s AND departure_date_time = %s"
    params = (airline_name, flight_number, departure_date_time)
    flight = executeQuery(flightQuery, params, True)

    airplane_id = flight["airplane_id"]
    airplaneSeatQuery = "SELECT number_of_seats FROM airplane WHERE ID = %s"
    params = (airplane_id)
    capacity = executeQuery(airplaneSeatQuery, params, True)["number_of_seats"]

    countQuery = "SELECT COUNT(*) from purchases WHERE ticket_id in (SELECT ID FROM ticket WHERE airline_name = %s AND flight_number = %s AND departure_date_time = %s AND travel_class = %s)"
    params = (airline_name, flight_number, departure_date_time, travel_class)
    count = executeQuery(countQuery, params, True)["COUNT(*)"] # the number of tickets already sold out of this flight
    if count == capacity:
        error = f"No available tickets for {flight_number}"
        return {"error": error}
    elif count >= 0.75*capacity:
        high_demand = True
    else:
        high_demand = False
        
    ticketQuery = "SELECT * FROM ticket WHERE airline_name = %s AND flight_number = %s AND departure_date_time = %s AND travel_class = %s AND ID not in (SELECT ticket_id FROM purchases)"
    params = (airline_name, flight_number, departure_date_time, travel_class) # find available tickets
    tickets = executeQuery(ticketQuery, params)
    
    if len(tickets) == 0:
        error = f"No available tickets for {flight_number}"
        return {"error": error}
    ticket = tickets[0]
    ticket_id = ticket["ID"]
    
    basePriceQuery = "SELECT base_price, departure_airport_code, arrival_airport_code, arrival_date_time FROM flight WHERE airline_name = %s AND flight_number = %s AND departure_date_time = %s"
    params = (airline_name, flight_number, departure_date_time)
    result = executeQuery(basePriceQuery, params, True)
    base_price = float(result["base_price"])
    departure_airport_code = result["departure_airport_code"]
    arrival_airport_code = result["arrival_airport_code"]
    arrival_date_time = result["arrival_date_time"]
    if high_demand:
        sold_price = round(base_price*1.25, 2)
    else:
        sold_price = round(base_price, 2)
    
    ticket_preview = {
        "ticket_id" : ticket_id, 
        "airline": airline_name, 
        "flight_number": flight_number, 
        "departure_date_time": departure_date_time, 
        "departure_airport_code": departure_airport_code,
        "arrival_airport_code": arrival_airport_code, 
        "arrival_date_time":arrival_date_time,
        "airplane_id": airplane_id,
        "travel_class": travel_class,
        "price": sold_price
    }
    return ticket_preview

# 3. Purchase tickets (for the front end, may implement together with the "searchFlights")
def purchaseTicketsDict(purchase, ticket1price, ticket2price=None):
    print(purchase)
    email = purchase["customer_email"]
    card_type = purchase["card_type"]
    card_number = purchase["card_number"]
    name_on_card = purchase["name_on_card"]
    card_exp = purchase["card_expiration"]
    
    ticket_id = purchase["ticket_id"]
    airline_name = purchase["airline_name"]
    flight_number = purchase["flight_number"]
    departure_date_time = purchase["departure_date_time"]
    
    return_ticket_id = purchase["ticket_id_return"]
    return_flight_number = purchase.get("flight_number_return")
    return_airline_name = purchase.get("airline_name_return")
    return_departure_date_time = purchase.get("departure_date_time_return") 

    to_trip = purchaseTickets(ticket_id, ticket1price, email, card_type, card_number, name_on_card, card_exp)
    print("Purchasing Ticket for: ", flight_number, airline_name, departure_date_time)
    print(to_trip) 

    error = to_trip.get("error",None)
    if error: 
        return [to_trip]
    
    if return_ticket_id: 
        print("Purchasing Ticket for: ", return_flight_number, return_airline_name, return_departure_date_time) 
        return_trip = purchaseTickets(return_ticket_id, ticket2price, email, card_type, card_number, name_on_card, card_exp)
        print(return_trip)
        error = return_trip.get("error", None)
        if error:
            return return_trip
        return [to_trip, return_trip]
    else: 
        return[to_trip]    

def purchaseTickets(ticket_id, sold_price, email, card_type, card_number, name_on_card, card_exp
): # various inputs through a form
    # get purchase time
    purchase_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    purchaseInsert = "INSERT INTO purchases VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
    params = (ticket_id, sold_price, purchase_time, email, card_type, card_number, name_on_card, card_exp)
    success = executeCommitQuery(purchaseInsert, params)
    if success == 0:
        return {"error": "Trouble purchasing at the moment, try again later"}
    return {"success": ticket_id}

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
            error ="No such ticket to be cancelled."
            cursor.close()
            return {"error":error}
        else:
            cursor.execute("SELECT departure_date_time FROM ticket WHERE ID = %s", (ticket_id))
            departure_date_time = cursor.fetchall()[0]["departure_date_time"]
            now = datetime.now()
            print((departure_date_time - now))
            if (departure_date_time - now) > timedelta(hours=24):
                cursor.execute("DELETE FROM purchases WHERE customer_email = %s AND ticket_id = %s", (email, ticket_id))
                conn.commit()
                cursor.close()
                return {"success": f"Success cancelling flight for ticket {ticket_id}"}
            elif (departure_date_time - now) < timedelta(hours=-24):
                error = "Cannot cancel completed flights"
                return {"error": error}
            else:
                error = "Cancellation of a flight ticket taking place within 24 hours is not allowed."
                cursor.close()
                return {"error": error}
    else:
        cursor.close()
        return {"error": "Error handling flight cancellation. Please try again later."}

# 5. Give Ratings and Comment on previous flights
def giveRatingsAndComments(email, rating_comment):
    rating = rating_comment["rating"]
    comment = rating_comment["comment"]
    ticket_id = rating_comment["ticket_id"]
    
    return giveRatings(email, ticket_id, rating, comment)
    # giveComments(email, ticket_id, comment)

def giveRatings(email, ticket_id, rating, comment):
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
                error = "You haven't taken the flight."
                cursor.close()
                return {"error": error}
            else:
                cursor.execute("SELECT * FROM ratings WHERE customer_email = %s AND ticket_id = %s", (email, ticket_id))
                ratings = cursor.fetchall()
                if len(ratings) != 0:
                    error = "You already rated the flight."
                    cursor.close()
                    return {"error": error}
                else:
                    cursor.execute("INSERT INTO ratings VALUES (%s, %s, %s, %s)", (email, ticket_id, rating, comment))
                    conn.commit()
                    cursor.close()
                    return {"success": f"Success rating flight with ticket {ticket_id}"}
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

            cursor.execute("""SELECT YEAR(date_time) as year, MONTH(date_time) as month, sum(sold_price) as total FROM purchases
            WHERE customer_email = %s AND date_time >= %s
            GROUP BY YEAR(date_time), MONTH(date_time)""", (email, first_day_of_next_month))
            month_wise_spending = cursor.fetchall() # I left the raw dictionary here, not sure whether further processing is needed

            cursor.close()
            start_date = one_year_ago.strftime("%Y-%m-%d")
            end_date = now.strftime("%Y-%m-%d")
            # return tot_spend, month_wise_spending
        else:
            # if the input format of the date is like "04/30/2022", we need these two lines
            # start_date = (datetime.strptime(start_date,"%m/%d/%Y")).strftime("%Y-%m-%d")
            # end_date = (datetime.strptime(end_date,"%m/%d/%Y")).strftime("%Y-%m-%d")

            cursor.execute("SELECT sum(sold_price) FROM purchases WHERE customer_email = %s AND date_time >= %s AND date_time <= %s", (email, start_date, end_date))
            spent = cursor.fetchone().get("sum(sold_price)", None)
            if not spent:
                return {"error": "You didn't spend anything"}
            print(f"{spent=}")
            tot_spend = float(spent) # total spend within the past year # not sure whether I should convert it to float

            cursor.execute("""SELECT YEAR(date_time) as year, MONTH(date_time) as month, sum(sold_price) as total FROM purchases
            WHERE customer_email = %s AND date_time >= %s AND date_time <= %s
            GROUP BY YEAR(date_time), MONTH(date_time)""", (email, start_date, end_date))
            month_wise_spending = cursor.fetchall()

            cursor.close()            
            # return tot_spend, month_wise_spending
        return {
            "total_spent": tot_spend, 
            "start": start_date, 
            "end": end_date,
            "monthly": month_wise_spending
        }
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
