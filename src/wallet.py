import json
import random
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
        self.nonce = 0  # counter for the number of transactions
        self.private_key, self.public_key = self.generate_wallet()
        self.total_rewards = 0

        """
        State will contain a dictionary of all the nodes:
        {address: {public_key, id, balance, stake} dictionaries}}
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
            # 3% fee for the sender (stakes and the initial 1000 BCC transactions don't have a fee)
            fee = transaction.amount * 0.03 if transaction.receiver_address != "0" and \
                                               transaction.message != "Initial Transaction" else 0
            self.blockchain_state[transaction.sender_address]["balance"] -= fee
            self.total_rewards += fee
        if transaction.receiver_address != "0":
            self.blockchain_state[transaction.receiver_address]["balance"] += transaction.amount
        
        # If the transaction is a stake (receiver address is '0'), update the blockchain state stake for the sender
        if transaction.receiver_address == "0":
            self.blockchain_state[transaction.sender_address]["stake"] += transaction.amount
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

    @staticmethod
    def create_transaction(sender_address: str, receiver_address: str,
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
        response = None
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
            self.add_transaction(transaction)

    def add_transaction(self, transaction: Transaction) -> None:
        self.transactions_pending.append(transaction)
        if len(self.transactions_pending) >= CAPACITY:
            self.mine_block()
        return

    def stake_amount(self, amount: int) -> bool:
        """Stake a certain amount of coins to be able to mine a block
           A transaction is created to stake the amount of coins
           with a receiver address of '0' 
        """
        if amount > self.balance:
            print("Insufficient balance to stake")
            return False

        transaction = self.create_transaction(sender_address=self.address,
                                              receiver_address='0',
                                              type_of_transaction="coins",
                                              amount=amount,
                                              message=None,
                                              nonce=self.nonce)
        self.broadcast_transaction(transaction)
        print(f"({self.address}) Staked successfully {amount} coins")
        return True
    
    def mine_block(self):
        if len(self.transactions_pending) == 0:
            print(f"({self.address}) [INVALID BLOCK]: No transactions to mine (pending transactions list is empty)")
            return False

        last_block = self.blockchain.chain[-1]
        validator = self.lottery()
        if validator != self.address:
            print(f"({self.address}) Not the winner of the lottery :(")
            self.transactions_pending = []
            return
        
        print(f"({self.address}) Winner of the lottery! Mining a block...")

        new_block = Block(index=last_block.index + 1, timestamp=time.time(), transactions=self.transactions_pending,
                          validator=validator, previous_hash=last_block.current_hash)
        new_block.current_hash = new_block.hash_block()
        broadcast_result = self.broadcast_block(new_block)
        if broadcast_result:
            print(f"({self.address}) Block mined successfully! Received {self.total_rewards} coins for mining the block.")
            self.balance += self.total_rewards
            self.blockchain_state[self.address]["balance"] += self.total_rewards
            self.total_rewards = 0
        else:
            print(f"({self.address}) Block mined successfully but failed to broadcast")
            self.transactions_pending = []
            return None
        self.blockchain.add_block(new_block)
        self.transactions_pending = []
        return new_block
    
    def broadcast_block(self, block: Block) -> bool:
        payload = block.stringify()
        response = None
        for node in self.blockchain_state.keys():
            if node == self.address:
                continue
            node_ip = node.split(":")[0]
            node_port = node.split(":")[1]
            response = requests.post(f"http://{node_ip}:{node_port}/api/block",
                                     data=payload,
                                     headers={'Content-Type': 'application/json'})
            if response.status_code != 200:
                print("Error:", response)
                break
        if response.status_code == 200:
            print(f"({self.address}) Block broadcasted successfully")
            return True
        else:
            return False

    def lottery(self, idx=0):
        """Select a random node to mine a block"""
        # Create a lottery where the probability of winning is proportional to the stake of each node
        lottery = []
        for node in self.blockchain_state.keys():
            lottery += [node] * self.blockchain_state[node]["stake"]

        # If there are no stakes, select a random node
        if lottery == []:
            lottery = list(self.blockchain_state.keys())

        # Set the seed to be the hash of the last block (or the previous block if an idx is given)
        random.seed(self.blockchain.chain[idx-1].current_hash)
        winner = lottery[random.randint(0, len(lottery) - 1)]
        return winner

