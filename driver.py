import sys
import os
import time
from datetime import datetime
import random

# ip_dict = {0: '192.168.1.1', 1: '192.168.1.2', 2: '192.168.1.3', 3: '192.168.1.4', 4: '192.168.1.5', 5: '192.168.1.1',
#            6: '192.168.1.2', 7: '192.168.1.3', 8: '192.168.1.4', 9: '192.168.1.5', 10: '192.168'}
# port_dict = {0: 5000, 1: 5000, 2: 5000, 3: 5000, 4: 5000, 5: 5001, 6: 5001, 7: 5001, 8: 5001, 9: 5001}
ip_dict = {0: '127.0.0.1', 1: '127.0.0.1', 2: '127.0.0.1', 3: '127.0.0.1', 4: '127.0.0.1'}
port_dict = {0: 5000, 1: 5001, 2: 5002, 3: 5003, 4: 5004}


def execute_commands(input_file):
    # Read the content of the input file
    with open(input_file, "r") as f:
        for line in f:
            recipient_id, *message_parts = line.strip().split(" ", 1)
            message = " ".join(message_parts)

            # Determine the recipient ID
            recipient_id = int(recipient_id[2:])

            # Determine the port based on recipient ID
            recipient_id = recipient_id - 5 if recipient_id >= 5 else recipient_id

            # Generate the command
            command = f"python cli.py --address {sys.argv[2]} m {ip_dict[recipient_id]}:{port_dict[recipient_id]} \"{message}\" 2>&1 > /dev/null"

            # Execute the command (print for demonstration)
            # print(command)
            os.system(command)
            # time.sleep(0.1)


# Specify the input file (e.g., "trans0.txt")
input_file = f"5nodes/trans{sys.argv[1]}.txt"

# if sys.argv[1] == '0':
#     os.system(f"python cli.py --address {sys.argv[2]} stake 100")

print("In 2s, starting commands")
print(datetime.now())
time.sleep(2)
# Execute the commands
execute_commands(input_file)
