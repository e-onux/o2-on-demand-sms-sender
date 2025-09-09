from huawei_lte_api.Client import Client
from huawei_lte_api.Connection import Connection
from huawei_lte_api.AuthorizedConnection import AuthorizedConnection
from huawei_lte_api.exceptions import ResponseErrorException, LoginErrorAlreadyLoginException
from dotenv import load_dotenv
import os
import time
import pprint

load_dotenv()  # Loads the .env file

# Retrieve the username and password from environment variables
username = os.getenv('API_USER')
password = os.getenv('API_PASSWORD')

# Enter your modem's IP address and, if necessary, the port number here.
url = 'http://192.168.8.1/'

def attempt_login(max_retries=3):
    retries = 0
    while retries < max_retries:
        try:
            connection = AuthorizedConnection(url, username=username, password=password)
            client = Client(connection)
            print("Logged in!")
            return client
        except LoginErrorAlreadyLoginException:
            print("Already logged in, retrying after delay...")
            time.sleep(10)
            retries += 1
    raise Exception("Failed to login after several attempts.")

# Use the function
client = attempt_login()

def execute_method(client):
    while True:
        method_name = input("Enter the method you want to execute (e.g., 'monitoring.start_date'): ").strip()
        if method_name.lower() == 'exit':
            print("Exiting...")
            break
        try:
            # Dynamically access the method based on user input
            parts = method_name.split('.')
            func = client
            for part in parts:
                func = getattr(func, part)
            result = func()
            print("Method output:")
            pprint.pprint(result)
        except Exception as e:
            print(f"An error occurred: {e}")

execute_method(client)

# Logout at the end of the session
try:
    client.user.logout()
    print("Successfully logged out.")
except Exception as e:
    print(f"Error during logout: {e}")