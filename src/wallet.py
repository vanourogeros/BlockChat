import json
import time

from src.block import Block
from src.transaction import Transaction
from src.blockchain import Blockchain
import requests

from Crypto.PublicKey import RSA

from dotenv import load_dotenv
import os
import sys

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
CAPACITY = int(os.getenv("CAPACITY"))
TOTAL_NODES = int(os.getenv("TOTAL_NODES"))
BOOTSTRAP_IP = os.getenv("BOOTSTRAP_IP")  # 127.0.0.1
BOOTSTRAP_PORT = int(os.getenv("BOOTSTRAP_PORT"))  # 5000


class Wallet:

    def __init__(self, ip_address: str, port: int, bootstrap=False) -> None:
        self.ip_address = ip_address
        self.port = port
        self.address = f"{ip_address}:{port}"
        self.bootstrap = bootstrap
        self.balance = 0
        self.stake = 0
        self.nonce = 0 # counter for the number of transactions
        self.private_key, self.public_key = self.generate_wallet()

        """
        State will contain a dictionary of all the nodes:
        {address: {public_key, balance, stake} dictionaries}}
        """
        self.blockchain_state = {}

        self.transactions_pending = []
        self.blockchain = Blockchain()

        if bootstrap:
            self.id = 0
            self.given_id = 0
            self.blockchain_state[self.address] = {"public_key": self.public_key,
                                                   "id": self.id,
                                                   "balance": 0,
                                                   "stake": 0}
                                          
            self.create_genesis_block()
        else:
            # Communicate with the bootstrap node to register in the blockchain
            data = {
                "address": self.address,
                "public_key": self.public_key
            }
            payload = json.dumps(data)
            response = requests.post(f"http://{BOOTSTRAP_IP}:{BOOTSTRAP_PORT}/api/bootstrap/register_node",
                                     data=payload,
                                     headers={'Content-Type': 'application/json'})
            if response.status_code != 200:
                print("Error:", response)
                sys.exit(1)

            print("Bootstrap is notified of new node.")
            self.id = response.json()['id']
            print(f"New node ID is {self.id}.")

    def create_genesis_block(self):
        # we call the create transaction function (the same as init of transaction)
        tran = self.create_transaction(sender_address='0',
                                       receiver_address=self.address,
                                       type_of_transaction="coins",
                                       amount=1000 * TOTAL_NODES,
                                       message="Genesis block",
                                       nonce=self.nonce)
        # We don't verify the transaction because it's the genesis block, so we process it directly
        self.process_transaction(tran)
        genesis_block = Block(index=0, timestamp=time.time(),
                              transactions=[tran], validator=0, previous_hash='1')
        self.blockchain.add_block(genesis_block)

    @staticmethod
    def generate_wallet() -> tuple:
        rsa_keypair = RSA.generate(2048)
        private_key = rsa_keypair.export_key()
        public_key = rsa_keypair.publickey().export_key()
        return private_key.decode(), public_key.decode()

    def process_transaction(self, transaction: Transaction) -> None:
        # Update the balance of the wallet for a verified transaction
        if transaction.type_of_transaction == "coins":
            if transaction.receiver_address == self.address:
                self.balance += transaction.amount
            elif transaction.sender_address == self.address:
                self.balance -= transaction.amount
        self.add_transaction(transaction)

        # Update the blockchain state balance for the sender and receiver
        if transaction.sender_address != "0":
            self.blockchain_state[transaction.sender_address]["balance"] -= transaction.amount
        if transaction.receiver_address != "0":
            self.blockchain_state[transaction.receiver_address]["balance"] += transaction.amount
        return

    def get_network_state(self):
        if self.bootstrap:
            return self.blockchain_state
        else:
            data = {
                "address": self.address,
                "public_key": self.public_key
            }
            payload = json.dumps(data)
            print(payload)
            response = requests.post(f"http://{self.ip_address}:{self.port}/api/get_network_state",
                                     data=payload,
                                     headers={'Content-Type': 'application/json'})
            if response.status_code == 200:
                return response.json()["data"]
            else:
                return []

    def register_node(self, address: str, public_key: str) -> None:
        self.blockchain_state[address] = {"public_key": public_key,
                                                 "id": self.given_id,
                                                 "balance": 0,
                                                 "stake": 0}
        
        return

    def create_transaction(self, sender_address: str, receiver_address: str,
                           type_of_transaction: str, amount: float, message: str, nonce: int
                           ) -> Transaction:
        transaction = Transaction(sender_address, receiver_address, type_of_transaction, amount, message, nonce)
        return transaction

    def broadcast_transaction(self, transaction: Transaction) -> None:
        # Increment the nonce of the wallet to keep track of the number of transactions
        # and prevent replay attacks/double spending
        self.nonce += 1
        transaction.sign_transaction(self.private_key)

        data = {
            "transaction": transaction.serialize()
        }
        payload = json.dumps(data)
        for node in self.blockchain_state.keys():
            if node == self.address:
                continue
            node_ip = node.split(":")[0]
            node_port = node.split(":")[1]
            response = requests.post(f"http://{node_ip}:{node_port}/api/transaction",
                                    data=payload,
                                    headers={'Content-Type': 'application/json'})
            if response.status_code != 200:
                print("Error:", response)
                break
        if response.status_code == 200:
            # If the transaction was broadcasted successfully, add it to the pending transactions list and process it
            self.process_transaction(transaction)
            #self.add_transaction(transaction)
        return response

    def add_transaction(self, transaction: Transaction) -> None:
        self.transactions_pending.append(transaction)

    def mine_block(self):
        if len(self.transactions_pending) == 0:
            print(f"(pid={os.getpid}) [INVALID BLOCK]: No transactions to mine (pending transactions list is empty)")
            return False

        last_block = self.blockchain.chain[-1]
        new_block = Block(index=last_block.index + 1, timestamp=time.time(), transactions=self.transactions_pending,
                          validator=self.public_key, previous_hash=last_block.current_hash)
        new_block.current_hash = new_block.hash_block()
        self.blockchain.add_block(new_block)
        self.transactions_pending = []
        return new_block
