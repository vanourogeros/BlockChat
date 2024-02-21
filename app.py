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
from dotenv import load_dotenv

load_dotenv()

BOOTSTRAP_IP = os.getenv("BOOTSTRAP_IP")  # 127.0.0.1
BOOTSTRAP_PORT = int(os.getenv("BOOTSTRAP_PORT"))  # 5000
TOTAL_NODES = int(os.getenv("TOTAL_NODES"))

app = Flask(__name__)

ip_address = sys.argv[1]
port = int(sys.argv[2])

bootstrap = ip_address == BOOTSTRAP_IP and port == BOOTSTRAP_PORT

wallet = Wallet(ip_address, port, bootstrap)

network_full = threading.Event()


def broadcast_network_blockchain():
    network_full.wait()

    time.sleep(2)

    for node in wallet.blockchain_state.keys():
        if node == wallet.address:
            continue # We don't want to send the blockchain to the bootstrap (ourselves)

        node_ip = node.split(":")[0]
        node_port = node.split(":")[1]
        payload = json.dumps(wallet.blockchain_state)
        response = requests.post(f"http://{node_ip}:{node_port}/api/regular/receive_state",
                                 data=payload,
                                 headers={'Content-Type': 'application/json'})
        if response.status_code != 200:
            print("Error:", response)
            sys.exit(1)

        for block in wallet.blockchain.chain:
            payload = block.serialize()
            response = requests.post(f"http://{node_ip}:{node_port}/api/receive_block",
                                     data=payload,
                                     headers={'Content-Type': 'application/json'})
            if response.status_code != 200:
                print("Error:", response)
                sys.exit(1)

    print("All nodes have been registered and informed of the network state and blockchain.")
    print("Will now give 1000 coins to everyone.")
    give_coins_to_everyone()

def give_coins_to_everyone():
    for node in wallet.blockchain_state.keys():
        if node == wallet.address:
            continue
        node_ip = node.split(":")[0]
        node_port = node.split(":")[1]
        transaction = Transaction(wallet.address, node, "coins", 1000, None, wallet.nonce)
        wallet.broadcast_transaction(transaction)

    print("All nodes have been given 1000 coins.")

@app.route('/api/get_balance')
def get_balance():
    return jsonify({"balance": wallet.balance}), 200


@app.route('/api/get_last_block')
def get_last_block():
    return jsonify(wallet.blockchain.chain[-1].serialize()), 200


@app.route('/api/get_network_state')
def get_network_state():
    return jsonify(wallet.blockchain_state), 200

@app.route('/api/transaction', methods=['POST'])
def transaction():
    data = request.json
    if data is None:
        return jsonify({"error": "No JSON data provided"}), 400

    transaction = deserialize_trans(data['transaction'])
    wallet.create_transaction(transaction.sender_address, transaction.receiver_address, 
                              transaction.type_of_transaction, transaction.amount, 
                              transaction.message, transaction.nonce)
    
    # Verify the signature of the transaction
    if not transaction.verify_signature(wallet.blockchain_state[transaction.sender_address]["public_key"]):
        print("Invalid signature")
        return jsonify({"error": "Invalid signature"}), 400

    wallet.process_transaction(transaction)
    return jsonify({"message": "Transaction processed successfully"}), 200

@app.route('/api/receive_block', methods=['POST'])
def receive_block():
    data = request.json
    if data is None:
        return jsonify({"error": "No JSON data provided"}), 400

    transactions = []
    for transaction in data['transactions']:
        transactions.append(deserialize_trans(transaction))

    block = Block(data['index'], data['timestamp'], transactions, data['validator'], data['previous_hash'])

    wallet.blockchain.add_block(block)

    if not wallet.blockchain.validate_chain():
        return jsonify({"error": "Invalid blockchain"}), 400

    return jsonify({"message": "Block received successfully"}), 200


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
        print("will ! Received state")
        data = request.get_json()
        if data is None:
            return jsonify({"error": "No JSON data provided"}), 400
        wallet.blockchain_state = data
        return jsonify({'message': 'State received and updated successfully'}), 200

if __name__ == '__main__':
    app.run(host=ip_address, port=port)
