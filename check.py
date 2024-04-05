import requests
import json
import os
import sys
from dotenv import load_dotenv

load_dotenv()
INITIAL_COINS = int(os.getenv("INITIAL_COINS"))
TOTAL_NODES = int(os.getenv("TOTAL_NODES"))
BOOTSTRAP_IP = os.getenv("BOOTSTRAP_IP")
PRINT_BLOCKCHAIN = int(os.getenv("PRINT_BLOCKCHAIN"))  # 1 for printing

TOTAL_BALANCE = INITIAL_COINS * TOTAL_NODES

if TOTAL_NODES == 5 and BOOTSTRAP_IP == '192.168.1.1':
    # Case of 5 nodes in a private network of 5 machines
    ip_dict = {0: '192.168.1.1', 1: '192.168.1.2', 2: '192.168.1.3', 3: '192.168.1.4', 4: '192.168.1.5'}
    port_dict = {0: 5000, 1: 5000, 2: 5000, 3: 5000, 4: 5000}

elif TOTAL_NODES == 10 and BOOTSTRAP_IP == '192.168.1.1':
    # Case of 10 nodes in a private network of 5 machines
    ip_dict = {0: '192.168.1.1', 1: '192.168.1.2', 2: '192.168.1.3', 3: '192.168.1.4', 4: '192.168.1.5',
               5: '192.168.1.1', 6: '192.168.1.2', 7: '192.168.1.3', 8: '192.168.1.4', 9: '192.168.1.5'}
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


def check_balance_hard():
    totals = []
    for ip, port in zip(ip_dict.values(), port_dict.values()):
        total = 0
        url = f"http://{ip}:{port}/api/get_network_state_hard"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                for ip_inner, port_inner in zip(ip_dict.values(), port_dict.values()):
                    total += response.json()[f'{ip_inner}:{port_inner}']['balance']
                totals.append(total)
            else:
                print("Error:", response.status_code)
        except requests.exceptions.RequestException as e:
            print("Error:", e)

    if all(value == TOTAL_BALANCE for value in totals):
        print(f"Balances from hard state are all {TOTAL_BALANCE}.")
    elif all(value == totals[0] for value in totals):
        print(f"Balances from hard state are all the same but NOT {TOTAL_BALANCE} ({totals[0]}).")
    else:
        print(f"Balances from hard state are NOT good: {totals}.")


def check_balance_soft():
    totals = []
    for ip, port in zip(ip_dict.values(), port_dict.values()):
        total = 0
        url = f"http://{ip}:{port}/api/get_network_state"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                for ip_inner, port_inner in zip(ip_dict.values(), port_dict.values()):
                    total += response.json()[f'{ip_inner}:{port_inner}']['balance']
                totals.append(total)
            else:
                print("Error:", response.status_code)
        except requests.exceptions.RequestException as e:
            print("Error:", e)

    if all(value == totals[0] for value in totals):
        print(f"Balances from soft state are all the same.")
    else:
        print(f"Balances from soft state are NOT all the same: {totals}.")
    return totals


def check_pending():
    pending_sets = []
    for ip, port in zip(ip_dict.values(), port_dict.values()):
        pending_set = set()
        url = f"http://{ip}:{port}/api/pending_transactions"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                for tran in response.json():
                    pending_set.add(tran)
                pending_sets.append(pending_set)
            else:
                print("Error:", response.status_code)
        except requests.exceptions.RequestException as e:
            print("Error:", e)

    frozen_sets = [frozenset(s) for s in pending_sets]
    if len(set(frozen_sets)) == 1 and all(len(s) == 4 for s in pending_sets):
        print("All pending_transaction lists have the same 4 transactions.")
    elif len(set(frozen_sets)) == 1 and not all(len(s) == 4 for s in pending_sets):
        print(f"All pending_transaction lists have the same transactions, but there are {len(pending_sets[0])}"
              f" transactions.")
    elif not len(set(frozen_sets)) == 1 and all(len(s) == 4 for s in pending_sets):
        print("All pending_transaction lists have 4 transactions, but they are NOT the same.")
    else:
        print("Shit is bad.")


def transaction_counts():
    transactions_sent = []
    transactions_received = []
    transactions_accepted = []
    for ip, port in zip(ip_dict.values(), port_dict.values()):
        url = f"http://{ip}:{port}/api/transaction_counts"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                transactions = response.json()
                transactions_sent.append(transactions['sent'])
                transactions_received.append(transactions['received'])
                transactions_accepted.append(transactions['accepted'])

            else:
                print("Error:", response.status_code)
        except requests.exceptions.RequestException as e:
            print("Error:", e)

    print(f"Sent: {transactions_sent}")
    print(f"Received: {transactions_received}")
    print(f"Validated: {transactions_accepted}")


def calc_reward_from_pending(totals):
    rewards = []
    for ip, port in zip(ip_dict.values(), port_dict.values()):
        reward = 0
        url = f"http://{ip}:{port}/api/pending_transactions"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                for tran in response.json():
                    reward += len(json.loads(tran)['message'])
                rewards.append(reward)
            else:
                print("Error:", response.status_code)
        except requests.exceptions.RequestException as e:
            print("Error:", e)

    new_totals = [x + y for x, y in zip(totals, rewards)]
    if all(value == TOTAL_BALANCE * 1.0 for value in new_totals):
        print(f"Balances from soft state are {TOTAL_BALANCE} - reward from pending.")
    else:
        print(f"Balances from soft state are NOT {TOTAL_BALANCE} - reward from pending.")


def get_blockchain():
    for ip, port in zip(ip_dict.values(), port_dict.values()):
        url = f"http://{ip}:{port}/api/print_block_lengths"
        try:
            response = requests.get(url)
            if response.status_code != 200:
                print("Error:", response.status_code)
        except requests.exceptions.RequestException as e:
            print("Error:", e)


check_pending()
check_balance_hard()
soft_totals = check_balance_soft()
calc_reward_from_pending(soft_totals)
transaction_counts()
if PRINT_BLOCKCHAIN ==1:
    get_blockchain()
