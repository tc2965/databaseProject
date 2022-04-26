import pymysql.cursors
import os 
from dotenv import load_dotenv
from models import CUSTOMER, STAFF
import hashlib

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