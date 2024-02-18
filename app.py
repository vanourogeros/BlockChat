from flask import Flask, jsonify
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


if __name__ == '__main__':
    app.run(host=ip_address, port=port)
