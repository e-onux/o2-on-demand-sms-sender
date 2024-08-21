import os
import time
import datetime
from huawei_lte_api.Client import Client
from huawei_lte_api.Connection import Connection
from huawei_lte_api.AuthorizedConnection import AuthorizedConnection
from huawei_lte_api.exceptions import ResponseErrorException, LoginErrorAlreadyLoginException
from dotenv import load_dotenv

load_dotenv()  # Load the .env file

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

client = attempt_login()

def read_last_sms_info():
    try:
        with open('last_sms_info.txt', 'r') as file:
            last_data = file.read().split(',')
            last_byte = int(last_data[0])
            last_time = float(last_data[1])
            return last_byte, last_time
    except FileNotFoundError:
        return 0, 0  # Defaults if file does not exist

def write_last_sms_info(total_data):
    with open('last_sms_info.txt', 'w') as file:
        file.write(f"{total_data},{time.time()}")

def reset_data_usage(client):
    month_stats = client.monitoring.month_statistics()
    last_clear_time = month_stats['MonthLastClearTime']
    today = datetime.datetime.now().strftime('%Y-%m-%d')

    # Tarih formatını düzeltme
    last_clear_time_formatted = datetime.datetime.strptime(last_clear_time, '%Y-%m-%d').strftime('%Y-%m-%d')

    print(f"Last clear time: {last_clear_time_formatted}, Today: {today}")

    if today != last_clear_time_formatted:
        client.monitoring.set_clear_traffic()
        write_last_sms_info(0);
        print("Data usage has been reset.")
    else:
        print("No reset needed, already cleared today.")

def check_data_usage_and_send_sms(client):
    month_stats = client.monitoring.month_statistics()
    total_data = int(month_stats['CurrentMonthDownload']) + int(month_stats['CurrentMonthUpload'])
    total_usage_gb = total_data / (1024**3)  # Convert bytes to GB
    print(f"Current usage: {total_usage_gb:.2f} GB")
    last_byte, last_time = read_last_sms_info()
    last_usage_gb = last_byte / (1024**3)  # Convert bytes to GB
    print(f"Last usage: {last_usage_gb:.2f} GB - {int((time.time()-last_time)/60)} min ago.")

    if total_usage_gb >= last_usage_gb + 1.9:  # Check for 2GB increase
        client.sms.send_sms(['80112'], 'WEITER')
        write_last_sms_info(total_data)
        print("SMS sent due to 2GB data usage threshold exceeded.")

# Daily data usage reset check
reset_data_usage(client)

# Check data usage and send SMS based on thresholds
check_data_usage_and_send_sms(client)

# Clear the SMS inbox
sms_list = client.sms.get_sms_list()
for sms in sms_list['Messages']['Message']:
    if sms['Phone'] == '80112':
        client.sms.delete_sms(sms['Index'])
        print(f"SMS Deleted: From: {sms['Phone']}, Message: {sms['Content']}")

# Logout at the end of the script
try:
    client.user.logout()
    print("Successfully logged out.")
except Exception as e:
    print(f"Error during logout: {e}")