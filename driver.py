import sys
import os
import time
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
TOTAL_NODES = int(os.getenv("TOTAL_NODES"))
BOOTSTRAP_IP = os.getenv("BOOTSTRAP_IP")

if TOTAL_NODES == 5 and BOOTSTRAP_IP == '192.168.1.1':
    # Case of 5 nodes in a private network of 5 machines
    ip_dict = {0: '192.168.1.1', 1: '192.168.1.2', 2: '192.168.1.3', 3: '192.168.1.4', 4: '192.168.1.5'}
    port_dict = {0: 5000, 1: 5000, 2: 5000, 3: 5000, 4: 5000}

elif TOTAL_NODES == 10 and BOOTSTRAP_IP == '192.168.1.1':
    # Case of 10 nodes in a private network of 5 machines
    ip_dict = {0: '192.168.1.1', 1: '192.168.1.2', 2: '192.168.1.3', 3: '192.168.1.4', 4: '192.168.1.5',
               5: '192.168.1.1',
               6: '192.168.1.2', 7: '192.168.1.3', 8: '192.168.1.4', 9: '192.168.1.5', 10: '192.168'}
    port_dict = {0: 5000, 1: 5000, 2: 5000, 3: 5000, 4: 5000, 5: 5001, 6: 5001, 7: 5001, 8: 5001, 9: 5001}

elif TOTAL_NODES == 5 and BOOTSTRAP_IP == '127.0.0.1':
    # Case of 5 nodes in 1 machine
    ip_dict = {0: '127.0.0.1', 1: '127.0.0.1', 2: '127.0.0.1', 3: '127.0.0.1', 4: '127.0.0.1'}
    port_dict = {0: 5000, 1: 5001, 2: 5002, 3: 5003, 4: 5004}

elif TOTAL_NODES == 10 and BOOTSTRAP_IP == '127.0.0.1':
    # Case of 10 nodes in 1 machine
    ip_dict = {0: '127.0.0.1', 1: '127.0.0.1', 2: '127.0.0.1', 3: '127.0.0.1', 4: '127.0.0.1', 5: '127.0.0.1',
               6: '127.0.0.1', 7: '127.0.0.1', 8: '127.0.0.1', 9: '127.0.0.1'}
    port_dict = {0: 5000, 1: 5001, 2: 5002, 3: 5003, 4: 5004, 5: 5005, 6: 5006, 7: 5007, 8: 5008, 9: 5009}

else:
    print("Invalid configuration. Please check the TOTAL_NODES and BOOTSTRAP_IP in the .env file.")
    sys.exit(1)


def new_message(address, receiver_address, message):
    data = {
        "sender_address": f"{address}",
        "receiver_address": receiver_address,
        "amount": 0,
        "type": "message",
        "message": message
    }
    payload = json.dumps(data)
    response = requests.post(f"http://{address}/api/make_transaction", data=payload,
                             headers={'Content-Type': 'application/json'})
    if response.status_code != 200:
        print("Error:", response)
        return


def execute_commands(input_file):
    # Read the content of the input file
    with open(input_file, "r") as f:
        tx_counter = 0
        start = time.time()
        for line in f:
            recipient_id, *message_parts = line.strip().split(" ", 1)
            tx_counter += 1
            message = " ".join(message_parts)

            # Determine the recipient ID
            recipient_id = int(recipient_id[2:])

            # Determine the port based on recipient ID
            recipient_id = recipient_id - 5 if recipient_id >= 5 else recipient_id

            new_message(f"{sys.argv[2]}", f"{ip_dict[recipient_id]}:{port_dict[recipient_id]}", message)
    end = time.time()
    elapsed_time = end - start
    print(f"\nSent {tx_counter} transactions in {elapsed_time} s.\n")


# Specify the input file (e.g., "trans0.txt")
input_file = f"5nodes/trans{sys.argv[1]}.txt" if TOTAL_NODES == 5 else f"10nodes/trans{sys.argv[1]}.txt"

# if sys.argv[1] == '0':
#     os.system(f"python cli.py --address {sys.argv[2]} stake 100")

print("In 2s, starting commands")
print(datetime.now())
time.sleep(2)
# Execute the commands
execute_commands(input_file)
