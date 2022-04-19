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
print(host, user, password, db)

conn = pymysql.connect(host=host,
                       user=user,
                       password=password,
                       db=db,
                       charset='utf8mb4',
                       cursorclass=pymysql.cursors.DictCursor)


def checkUserExistsInDb(typeUser, field, username):
    cursor = conn.cursor()
	#executes query
    query = "SELECT * FROM %s WHERE %s = '%s'" % (typeUser, field, username)
    print(typeUser, field, username)
    print(query)
    cursor.execute(query)
	#stores the results in a variable
    data = cursor.fetchone()
    cursor.close()
	#use fetchall() if you are expecting more than 1 data row
    return data
        
def checkUserLogin(typeUser, username, password):
    cursor = conn.cursor()
    # incoming pass must be hashed to check
    # stored pass can't be decrypted (md5 is one way hash)
    password = hashlib.md5(password.encode()).hexdigest() 
    query = "SELECT * FROM %s WHERE username = %s AND password = %s"
    cursor.execute(query, (typeUser, username, password))
    data = cursor.fetchone()
    cursor.close()
    return data

def registerCustomer(customer): 
    """
    dict[email, name, ...]
    """
    print("REGISTERCUSTOMER")
    exists = checkUserExistsInDb("customer", "email", customer["email"])
    if (exists): 
        return False 
    else:
        password = customer["password"]
        customer["password"] = hashlib.md5(password.encode()).hexdigest()
        # values = ""
        # print(customer)
        # for field in CUSTOMER: 
        #     values += "'" + str(customer[field]) + "', "
        insertCustomer = f"INSERT INTO customer VALUES ('%(email)s', '%(name)s', '%(password)s', '%(building_number)s', '%(street)s', '%(city)s', '%(state)s', '%(phone_number)s', '%(passport_number)s', '%(passport_expiration)s', '%(passport_country)s', '%(date_of_birth)s' )" % customer
        print(insertCustomer)
        cursor = conn.cursor()
        cursor.execute(insertCustomer)
        conn.commit()
        cursor.close()
        return customer["email"]

def registerStaff(staff): 
    """
    dict[email, name, ...]
    """
    exists = checkUserExistsInDb("airline_staff", "username", staff["username"])
    if (exists): 
        return False 
    else: 
        password = staff["password"]
        staff["password"] = hashlib.md5(password.encode()).hexdigest()
        insertStaff = f"INSERT INTO airline_staff VALUES ('%(username)s', '%(password)s', '%(first_name)s', '%(last_name)s', '%(date_of_birth)s', '%(airline)s')" % staff
        cursor = conn.cursor()
        cursor.execute(insertStaff)
        conn.commit()
        cursor.close()
        return staff["username"]