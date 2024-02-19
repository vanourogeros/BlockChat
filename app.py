from flask import Flask, jsonify, request
from src.wallet import Wallet

import os
import sys
from dotenv import load_dotenv

load_dotenv()

BOOTSTRAP_IP = os.getenv("BOOTSTRAP_IP")  # 127.0.0.1
BOOTSTRAP_PORT = int(os.getenv("BOOTSTRAP_PORT"))  # 5000

app = Flask(__name__)

ip_address = sys.argv[1]
port = int(sys.argv[2])

bootstrap = ip_address == BOOTSTRAP_IP and port == BOOTSTRAP_PORT

wallet = Wallet(ip_address, port, bootstrap)

@app.route('/api/get_balance')
def get_balance():
    return jsonify({"balance": wallet.balance})

@app.route('/api/get_last_block')
def get_last_block():
    return jsonify(wallet.blockchain.chain[-1].serialize())

@app.route('/api/bootstrap/register_node', methods=['POST'])
def register_node():
    data = request.json
    if data is None:
        return jsonify({"error": "No JSON data provided"}), 400

    address = data.get('address')
    public_key = data.get('public_key')
    if address is None or public_key is None:
        return jsonify({"error": "Missing parameter(s)"}), 400

    wallet.register_node(address, public_key)
    return jsonify({"message": "Node registered successfully"})

if __name__ == '__main__':
    app.run(host=ip_address, port=port)
    
