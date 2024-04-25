from huawei_lte_api.Client import Client
from huawei_lte_api.Connection import Connection
from huawei_lte_api.AuthorizedConnection import AuthorizedConnection
from huawei_lte_api.exceptions import ResponseErrorException, LoginErrorAlreadyLoginException
from dotenv import load_dotenv
import os
import time

load_dotenv()  # Loads the .env file

# Retrieve the username and password from environment variables
username = os.getenv('API_USER')
password = os.getenv('API_PASSWORD')

# Enter your modem's IP address and, if necessary, the port number here.
url = 'http://192.168.8.1/'
# Attempt to logout before making a new authorized connection

def attempt_login(max_retries=3):
    retries = 0
    while retries < max_retries:
        try:
            connection = AuthorizedConnection(url, username=username, password=password)
            client = Client(connection)
            print("Logged in!")
            return client  # Successful login, return the client
        except LoginErrorAlreadyLoginException:
            print("Already logged in, retrying after delay...")
            time.sleep(10)  # Wait for 10 seconds before retrying
            retries += 1
    # If we exhaust retries and still don't have a client, handle the situation:
    raise Exception("Failed to login after several attempts.")

# Use the function
client = attempt_login()

# Retrieve all messages from the SMS inbox.
sms_list = client.sms.get_sms_list()

# Check for SMS from 80112 that are unread and do not contain a specific text to mark and send.
exclude_text = "wurde erfolgreich aktiviert"
send_sms = False
for sms in sms_list['Messages']['Message']:
    if sms['Phone'] == '80112' and sms['Smstat'] == '0' and exclude_text not in sms['Content']:
        # Mark the SMS as read
        client.sms.set_read(sms['Index'])
        print(f"From: {sms['Phone']}, Message: {sms['Content']}")
        send_sms = True


# If there is a relevant SMS, send "WEITER" to 80112.
if send_sms:
    client.sms.send_sms(['80112'], 'WEITER')

#Inbox cleaning
for sms in sms_list['Messages']['Message']:
    if sms['Phone'] == '80112':
        print(f"SMS Deleted: From: {sms['Phone']}, Message: {sms['Content']}")
        client.sms.delete_sms(sms['Index'])

# Logout at the end of the script
try:
    client.user.logout()
    print("Successfully logged out.")
except Exception as e:
    print(f"Error during logout: {e}")