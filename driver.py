import sys
import os

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
            port = 5000 if recipient_id < 5 else 5001

            # Generate the command
            command = f"python cli.py --address {sys.argv[2]} m node{recipient_id}:{port} '{message}'"

            # Execute the command (print for demonstration)
            print(command)

# Specify the input file (e.g., "trans0.txt")
input_file = f"input/trans{sys.argv[1]}.txt"

# Execute the commands
execute_commands(input_file)
