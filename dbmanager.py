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
    query = "SELECT * FROM %s WHERE %s = %s"
    cursor.execute(query, (typeUser, field, username))
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
    exists = checkUserExistsInDb("customer", "email", customer["email"])
    if (exists): 
        return False 
    else:
        password = customer["password"]
        customer["password"] = hashlib.md5(password.encode()).hexdigest()
        values = ""
        for field in CUSTOMER: 
            values += customer[field] + ", "
        insertCustomer = f"INSERT INTO customer VALUES ({values})"
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
        values = ""
        for field in STAFF: 
            values += staff[field] + ", "
        insertStaff = f"INSERT INTO airline_staff VALUES ({values})"
        cursor = conn.cursor()
        cursor.execute(insertStaff)
        conn.commit()
        cursor.close()
        return staff["username"]