#Import Flask Library
from email import charset
from flask import Flask, render_template, request, session, url_for, redirect
from flask_restx import reqparse
import pymysql.cursors
import os 
from dotenv import load_dotenv
import dbmanager


customer_parser = reqparse.RequestParser() 
customer_parser.add_argument("email", type=str, location='form')
customer_parser.add_argument("name", type=str, location='form')
customer_parser.add_argument("password", type=str, location='form')
customer_parser.add_argument("building_number", type=str, location='form')
customer_parser.add_argument("street", type=str, location='form')
customer_parser.add_argument("city", type=str, location='form')
customer_parser.add_argument("state", type=str, location='form')
customer_parser.add_argument("phone_number", type=str, location='form')
customer_parser.add_argument("passport_number", type=str, location='form')
customer_parser.add_argument("passport_expiration", type=str, location='form')
customer_parser.add_argument("passport_country", type=str, location='form')
customer_parser.add_argument("date_of_birth", type=str, location='form')

airline_staff_parse = reqparse.RequestParser() 
airline_staff_parse.add_argument("username", type=str, location='form')
airline_staff_parse.add_argument("password", type=str, location='form')
airline_staff_parse.add_argument("first_name", type=str, location='form')
airline_staff_parse.add_argument("last_name", type=str, location='form')
airline_staff_parse.add_argument("date_of_birth", type=str, location='form')
airline_staff_parse.add_argument("airline", type=str, location='form')
airline_staff_parse.add_argument("phone_number", type=str, location='form')

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

#Authenticates the login
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
		return redirect(url_for('home'))
	else:
		#returns an error message to the html page
		error = 'Invalid login or username'
		return render_template('login.html', error=error)

#Authenticates the register
@app.route('/registerAuth/<type_user>', methods=['GET', 'POST'])
def registerAuth(type_user):
    if type_user == "customer":
        customer = customer_parser.parse_args()
        inDB = dbmanager.registerCustomer(customer)
    elif type_user == "airline_staff":
        staff = airline_staff_parse.parse_args()
        inDB = dbmanager.registerStaff(staff)
        
    if not inDB: 
        if type_user == "customer":
            template = "customerRegister.html"
        elif type_user == "airline_staff":
            template = "staffRegister.html"
        return render_template(template, error="email or username exists already")
    else:
        session['username'] = inDB
        return redirect(url_for('home'))
    
     
@app.route('/home')
def home():
    username = session['username']
    return render_template('home.html', username=username)

		
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
	session.pop('username')
	return redirect('/')
		
app.secret_key = 'some key that you will never guess'
#Run the app on localhost port 5000
#debug = True -> you don't have to restart flask
#for changes to go through, TURN OFF FOR PRODUCTION
if __name__ == "__main__":
	app.run('127.0.0.1', 5000, debug = True)
