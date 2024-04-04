from flask import Flask, jsonify, request
from src.wallet import Wallet
from src.block import Block
from src.transaction import Transaction, deserialize_trans

import os
import sys
import json
import requests
import threading
import time
import subprocess
from copy import deepcopy
from dotenv import load_dotenv

load_dotenv()

BOOTSTRAP_IP = os.getenv("BOOTSTRAP_IP")  # 127.0.0.1
BOOTSTRAP_PORT = int(os.getenv("BOOTSTRAP_PORT"))  # 5000
TOTAL_NODES = int(os.getenv("TOTAL_NODES"))
CAPACITY = int(os.getenv("CAPACITY"))
INITIAL_COINS = int(os.getenv("INITIAL_COINS"))  # 1000

app = Flask(__name__)

ip_address = sys.argv[1]
port = int(sys.argv[2])

bootstrap = ip_address == BOOTSTRAP_IP and port == BOOTSTRAP_PORT

wallet = Wallet(ip_address, port, bootstrap)

network_full = threading.Event()

flag = True


def broadcast_network_blockchain():
    network_full.wait()

    time.sleep(2)

    wallet.total_lock.acquire()

    for node in wallet.blockchain_state.keys():
        if node == wallet.address:
            continue  # We don't want to send the blockchain to the bootstrap (ourselves)

        node_ip = node.split(":")[0]
        node_port = node.split(":")[1]
        payload = json.dumps(wallet.blockchain_state)
        response = requests.post(f"http://{node_ip}:{node_port}/api/regular/receive_state",
                                 data=payload,
                                 headers={'Content-Type': 'application/json'})
        if response.status_code != 200:
            print("Error:", response.json())
            wallet.total_lock.release()
            sys.exit(1)

        for block in wallet.blockchain.chain:
            payload = block.serialize()
            response = requests.post(f"http://{node_ip}:{node_port}/api/receive_block",
                                     data=payload,
                                     headers={'Content-Type': 'application/json'})
            if response.status_code != 200:
                print("Error:", response.json())
                wallet.total_lock.release()
                sys.exit(1)

    wallet.blockchain_state_hard = deepcopy(wallet.blockchain_state)

    wallet.total_lock.release()

    print("All nodes have been registered and informed of the network state and blockchain.")
    print("Will now give 1000 coins to everyone.")
    give_coins_to_everyone()

    # run script
    script_path = './driver.py'
    address = f"{wallet.ip_address}:{wallet.port}"
    wallet_id = str(wallet.id)
    process = subprocess.Popen(['python3', script_path, wallet_id, address])


def give_coins_to_everyone():
    for node in wallet.blockchain_state.keys():
        if node == wallet.address:
            continue
        transaction = Transaction(wallet.address, node, "coins", INITIAL_COINS,
                                  "Initial Transaction", wallet.nonce)
        if wallet.broadcast_transaction(transaction):
            print(f"Node {node} has been given {INITIAL_COINS} coins.")
        else:
            print("Some error occurred")
            sys.exit(1)


def process_incoming_transaction(transaction: Transaction):
    if transaction.sender_address != '0':
        wallet.transactions_pending[transaction.transaction_id] = transaction
    wallet.process_transaction(transaction)
    if len(wallet.transactions_pending) >= CAPACITY:
        wallet.capacity_full.set()

    return


def miner_thread_func():
    """
    We use a separate thread for mining that wakes up when an event is set (with timeout for solving lost-wakeup problem).
    """
    while True:
        wallet.capacity_full.wait(timeout=0.05)
        if len(wallet.transactions_pending) >= CAPACITY:
            if not wallet.mine_block():
                print("Mining failed, exiting...")
                sys.exit(1)
        wallet.capacity_full.clear()


def verify_trans(transaction: Transaction):
    # Verify the signature of the transaction
    if not transaction.verify_signature(wallet.blockchain_state[transaction.sender_address]["public_key"]):
        return False

    # Verify transaction balance
    if not transaction.verify_balance(wallet.blockchain_state[transaction.sender_address]["balance"],
                                      wallet.blockchain_state[transaction.sender_address]["stake"]):
        return False

    return True


@app.route('/api/get_balance')
def get_balance():
    return jsonify({"balance": wallet.balance}), 200


@app.route('/api/view_block', methods=['GET'])
def view_block():
    # Needed to convert the block to JSONifiable dictionary
    block = json.loads(wallet.blockchain.chain[-1].serialize())
    block["transactions"] = list(map(lambda transaction: json.loads(transaction), block["transactions"]))

    return jsonify(block), 200


@app.route('/api/get_network_state')
def get_network_state():
    return jsonify(wallet.blockchain_state), 200


@app.route('/api/get_network_state_hard')
def get_network_state_hard():
    return jsonify(wallet.blockchain_state_hard), 200


# For debugging purposes
@app.route('/api/transactions_history')
def transactions_history():
    transactions_list = []
    for transaction in wallet.transaction_history:
        transactions_list.append(transaction.serialize())
    return jsonify(transactions_list), 200


# For debugging purposes
@app.route('/api/transaction_counts')
def transaction_counts():
    wallet.blockchain.print_block_lengths()
    return jsonify({"sent": wallet.nonce, "received": wallet.received_transactions_count,
                    "accepted": wallet.accepted_transactions_count}), 200


@app.route('/api/receive_transaction', methods=['POST'])
def receive_transaction():
    data = request.json
    if data is None:
        return jsonify({"error": "No JSON data provided"}), 400

    transaction = deserialize_trans(data['transaction'])

    wallet.total_lock.acquire()

    wallet.received_transactions_count += 1

    if transaction.transaction_id in wallet.transactions_missing:
        del wallet.transactions_missing[transaction.transaction_id]
        wallet.total_lock.release()
        return jsonify({"message": "Transaction already processed from previous block"}), 200

    if not verify_trans(transaction):
        wallet.transactions_rejected[transaction.transaction_id] = transaction
        wallet.total_lock.release()
        return jsonify({"error": "Invalid signature or balance"}), 400

    process_incoming_transaction(transaction)

    wallet.total_lock.release()

    # run script
    global flag
    if flag and not bootstrap:
        flag = False
        script_path = './driver.py'
        address = f"{wallet.ip_address}:{wallet.port}"
        wallet_id = str(wallet.id)
        process = subprocess.Popen(['python3', script_path, wallet_id, address])

    return jsonify({"message": "Transaction processed successfully"}), 200


@app.route('/api/receive_block', methods=['POST'])
def receive_block():
    """
    Receive a block and update hard_state with the transactions contained inside it.
    """
    data = request.json
    if data is None:
        return jsonify({"error": "No JSON data provided"}), 400

    transactions = []

    wallet.total_lock.acquire()

    wallet.blockchain_state = deepcopy(wallet.blockchain_state_hard)
    for transaction in data['transactions']:
        # If a transaction has been already received, remove it from transactions_pending.
        # Else, check if it has been rejected. If yes, remove it from the rejected list (validator forces acceptance).
        # If not, add it to missing transactions (have not received it yet)
        trans_object = deserialize_trans(transaction)
        transactions.append(trans_object)
        if trans_object.sender_address != '0':
            wallet.process_transaction(trans_object)
        try:
            del wallet.transactions_pending[trans_object.transaction_id]
        except KeyError:
            if trans_object.sender_address == "0":
                continue
            else:
                if trans_object.transaction_id in wallet.transactions_rejected:
                    del wallet.transactions_rejected[trans_object.transaction_id]
                    continue
                else:
                    wallet.transactions_missing[trans_object.transaction_id] = trans_object
                    continue
        except Exception:
            wallet.total_lock.release()
            return jsonify({"message": "Some error occurred"}), 400

    block = Block(data['index'], data['timestamp'], transactions, data['validator'], data['previous_hash'])

    # If a block has been received out of order, wait until the previous block has been added.
    while data['index'] != len(wallet.blockchain.chain):
        wallet.total_lock.release()
        wallet.received_block.wait(timeout=0.05)
        wallet.received_block.clear()
        wallet.total_lock.acquire()

    if data['previous_hash'] == '1':
        validator = 0
    else:
        validator = wallet.lottery(data['index'])

    if not block.validate_block(wallet.blockchain, validator):
        wallet.total_lock.release()
        return jsonify({"error": "Invalid block"}), 400

    wallet.blockchain.add_block(block)
    wallet.received_block.set()

    # update the validator balance
    for key, value in wallet.blockchain_state.items():
        if value['id'] == validator:
            wallet.blockchain_state[key]['balance'] += block.calculate_reward()
            break

    wallet.blockchain_state_hard = deepcopy(wallet.blockchain_state)

    # Process again the remaining pending transactions because their effect has been canceled,
    # when soft_state became hard_state.
    for transaction in wallet.transactions_pending.values():
        wallet.process_transaction(transaction)

    wallet.total_lock.release()

    return jsonify({"message": "Block received successfully"}), 200


@app.route('/api/stake_amount', methods=['POST', 'GET'])
def stake_amount():
    data = request.json
    amount = data["amount"]
    if amount is None:
        return jsonify({"error": "Missing parameter(s)"}), 400

    result = wallet.stake_amount(amount)
    if not result:
        return jsonify({"error": "Insufficient balance"}), 400
    return jsonify({"message": "Stake successful"}), 200


@app.route('/api/make_transaction', methods=['POST'])
def make_transaction():
    data = request.json
    if data is None:
        return jsonify({"error": "No JSON data provided"}), 400

    receiver_address = data['receiver_address']
    amount = data['amount']
    message = data['message']
    type = data['type']

    if receiver_address is None or amount is None:
        return jsonify({"error": "Missing parameter(s)"}), 400

    transaction = wallet.create_transaction(wallet.address, receiver_address, type, amount, message, wallet.nonce)
    if wallet.broadcast_transaction(transaction):
        return jsonify({"message": "Transaction broadcasted successfully"}), 200
    else:
        return jsonify({"message": "Some error occurred"}), 400


@app.route('/api/pending_transactions', methods=['GET'])
def pending_transactions():
    transactions_list = []
    for transaction in wallet.transactions_pending.values():
        transactions_list.append(transaction.serialize())
    return jsonify(transactions_list), 200


@app.route('/api/rejected_transactions', methods=['GET'])
def rejected_transactions():
    transactions_list = []
    for transaction in wallet.transactions_rejected.values():
        transactions_list.append(transaction.serialize())
    return jsonify(transactions_list), 200


if bootstrap:
    broadcast_thread = threading.Thread(target=broadcast_network_blockchain).start()


    @app.route('/api/bootstrap/register_node', methods=['POST'])
    def register_node():
        data = request.json
        if data is None:
            return jsonify({"error": "No JSON data provided"}), 400

        address = data.get('address')
        public_key = data.get('public_key')
        if address is None or public_key is None:
            return jsonify({"error": "Missing parameter(s)"}), 400

        wallet.given_id += 1
        wallet.register_node(address, public_key)

        if wallet.given_id == TOTAL_NODES - 1:
            network_full.set()

        return jsonify({"message": "Node registered successfully", "id": wallet.given_id}), 200

if not bootstrap:
    @app.route('/api/regular/receive_state', methods=['POST'])
    def receive_state():
        wallet.total_lock.acquire()
        data = request.get_json()
        if data is None:
            wallet.total_lock.release()
            return jsonify({"error": "No JSON data provided"}), 400
        wallet.blockchain_state = data
        wallet.blockchain_state_hard = deepcopy(wallet.blockchain_state)
        wallet.total_lock.release()
        return jsonify({'message': 'State received and updated successfully'}), 200

if __name__ == '__main__':
    miner_thread = threading.Thread(target=miner_thread_func).start()
    app.run(host=ip_address, port=port)
