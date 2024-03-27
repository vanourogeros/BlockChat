from flask import Flask, jsonify, request
from src.wallet import Wallet
from src.block import Block
from src.blockchain import Blockchain
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
            sys.exit(1)

        for block in wallet.blockchain.chain:
            payload = block.serialize()
            response = requests.post(f"http://{node_ip}:{node_port}/api/receive_block",
                                     data=payload,
                                     headers={'Content-Type': 'application/json'})
            if response.status_code != 200:
                print("Error:", response.json())
                sys.exit(1)

    wallet.blockchain_state_hard = deepcopy(wallet.blockchain_state)

    print("All nodes have been registered and informed of the network state and blockchain.")
    print("Will now give 1000 coins to everyone.")
    give_coins_to_everyone()

    # run script
    script_path = './driver.py'
    address = f"{wallet.ip_address}:{wallet.port}"
    wallet_id = str(wallet.id)
    process = subprocess.Popen(['python', script_path, wallet_id, address])


def give_coins_to_everyone():
    for node in wallet.blockchain_state.keys():
        if node == wallet.address:
            continue
        transaction = Transaction(wallet.address, node, "coins", 1000,
                                  "Initial Transaction", wallet.nonce)
        wallet.broadcast_transaction(transaction)

    print("All nodes have been given 1000 coins.")


def process_incoming_transaction(transaction: Transaction):
    if transaction.sender_address != '0':
        wallet.transactions_pending[transaction.transaction_id] = transaction
    wallet.process_transaction(transaction)
    if len(wallet.transactions_pending) >= CAPACITY:
        wallet.capacity_full.set()
    return


def miner_thread_func():
    while True:
        wallet.capacity_full.wait()
        wallet.mine_block()
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


@app.route('/api/receive_transaction', methods=['POST'])
def receive_transaction():
    data = request.json
    if data is None:
        return jsonify({"error": "No JSON data provided"}), 400

    transaction = deserialize_trans(data['transaction'])

    if not verify_trans(transaction):
        print("Invalid signature or balance")
        return jsonify({"error": "Invalid signature or balance"}), 400

    process_incoming_transaction(transaction)

    # run script
    global flag
    if flag:
        flag = False
        script_path = './driver.py'
        address = f"{wallet.ip_address}:{wallet.port}"
        wallet_id = str(wallet.id)
        process = subprocess.Popen(['python', script_path, wallet_id, address])

    return jsonify({"message": "Transaction processed successfully"}), 200


@app.route('/api/receive_block', methods=['POST'])
def receive_block():
    data = request.json
    if data is None:
        return jsonify({"error": "No JSON data provided"}), 400

    transactions = []
    wallet.blockchain_state = deepcopy(wallet.blockchain_state_hard)
    wallet.mutex.acquire()
    for transaction in data['transactions']:
        trans_object = deserialize_trans(transaction)
        transactions.append(trans_object)
        if trans_object.sender_address != '0':
            wallet.process_transaction(trans_object)
        try:
            del wallet.transactions_pending[trans_object.transaction_id]
        except KeyError:
            continue
        except Exception:
            wallet.mutex.release()
            return jsonify({"message": "Some error occurred"}), 400
    wallet.mutex.release()

    block = Block(data['index'], data['timestamp'], transactions, data['validator'], data['previous_hash'])

    if data['previous_hash'] == '1':
        validator = 0
    else:
        validator = wallet.lottery(data['index'])

    if not block.validate_block(wallet.blockchain, validator):
        return jsonify({"error": "Invalid block"}), 400

    wallet.blockchain.add_block(block)

    # update the validator balance
    for key, value in wallet.blockchain_state.items():
        if value['id'] == validator:
            wallet.blockchain_state[key]['balance'] += block.calculate_reward()
            break

    print(f"Validator {validator} has been given {block.calculate_reward()} coins for validating the block.")
    wallet.blockchain_state_hard = deepcopy(wallet.blockchain_state)

    for trans_id, trans_obj in wallet.transactions_pending.items():
        if not verify_trans(trans_obj):
            del wallet.transactions_pending[trans_id]
        else:
            wallet.process_transaction(trans_obj)

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
    wallet.broadcast_transaction(transaction)

    return jsonify({"message": "Transaction broadcasted successfully"}), 200


@app.route('/api/pending_transactions', methods=['GET'])
def pending_transactions():
    transactions_list = []
    for transaction in wallet.transactions_pending.values():
        transactions_list.append(transaction.serialize())
    return jsonify(transactions_list), 200


@app.route('/api/test_transaction', methods=['GET'])
def my_transaction():
    """
    Send some coins to the bootstrap node
    """
    receiver_address = '127.0.0.1:5000'
    amount = int(request.args.get('amount'))
    message = ""

    if receiver_address is None or amount is None:
        return jsonify({"error": "Missing parameter(s)"}), 400

    transaction = wallet.create_transaction(wallet.address, receiver_address, "coins", amount, message, wallet.nonce)
    wallet.broadcast_transaction(transaction)

    return jsonify({"message": "Transaction broadcasted successfully"}), 200


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
        data = request.get_json()
        if data is None:
            return jsonify({"error": "No JSON data provided"}), 400
        wallet.blockchain_state = data
        wallet.blockchain_state_hard = deepcopy(wallet.blockchain_state)
        return jsonify({'message': 'State received and updated successfully'}), 200

if __name__ == '__main__':
    miner_thread = threading.Thread(target=miner_thread_func).start()
    app.run(host=ip_address, port=port)
