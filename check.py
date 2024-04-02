import requests

# ip_dict = {0: '192.168.1.1', 1: '192.168.1.2', 2: '192.168.1.3', 3: '192.168.1.4', 4: '192.168.1.5', 5: '192.168.1.1',
#            6: '192.168.1.2', 7: '192.168.1.3', 8: '192.168.1.4', 9: '192.168.1.5', 10: '192.168'}
# port_dict = {0: 5000, 1: 5000, 2: 5000, 3: 5000, 4: 5000, 5: 5001, 6: 5001, 7: 5001, 8: 5001, 9: 5001}
ip_dict = {0: '127.0.0.1', 1: '127.0.0.1', 2: '127.0.0.1', 3: '127.0.0.1', 4: '127.0.0.1'}
port_dict = {0: 5000, 1: 5001, 2: 5002, 3: 5003, 4: 5004}


def check_balance():
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

    if all(value == 50000.0 for value in totals):
        print("Balances are all 50000")
    elif all(value == totals[0] for value in totals):
        print(f"Balances are all the same but not 50000 ({totals[0]})")
    else:
        print(f"Balances are not good: {totals}")


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
        print("All pending_transaction lists have 4 transactions, but they are not the same.")
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

check_balance()
check_pending()
transaction_counts()
