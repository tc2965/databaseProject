# You can use this file to make http calls to test

from unittest import TestCase
import os 
import app as ep
from dotenv import load_dotenv

load_dotenv()
host = os.environ.get("HOST")
user = os.environ.get("USER")
password = os.environ.get("PASSWORD")
db = os.environ.get("DB")

class EndpointTestCase(TestCase):
    def setUp(self):
        self.app = ep.app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        pass
    
    def tearDown(self):
        pass 
    
    def test_create_user(self):
        customerRegistration = {
            "email": "testing@gmail.com", 
            "name": "name", 
            "password": "password", 
            "building_number": "6", 
            "street": "Metrotech", 
            "city": "Brooklyn", 
            "state": "NY", 
            "phone_number": "0000000000", 
            "passport_number": "0000000000",
            "passport_expiration": "01-01-2000", 
            "passport_country": "USA", 
            "date_of_birth": "2000-01-01"
        }
        response = self.client.post("/registerAuth/customer", data=customerRegistration)
        print(response)
        self.assertEqual(response.status_code, 200)
        
    def test_create_airport(self):
        # airport = {
        #     "airport_code": "99999", 
        #     "name": "JFK", 
        #     "city": "NYC", 
        #     "country": "USA", 
        #     "type": "Both"
        # }
        # response = self.client.post("/airports", data=airport)
        # print(response.data)
        response = self.client.get("/airports")
        print(response.data)