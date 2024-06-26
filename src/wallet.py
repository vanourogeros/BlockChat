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
import threading

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
CAPACITY = int(os.getenv("CAPACITY"))
TOTAL_NODES = int(os.getenv("TOTAL_NODES"))
BOOTSTRAP_IP = os.getenv("BOOTSTRAP_IP")  # 127.0.0.1
BOOTSTRAP_PORT = int(os.getenv("BOOTSTRAP_PORT"))  # 5000
INITIAL_COINS = int(os.getenv("INITIAL_COINS"))  # 1000
PRINT_TRANS = int(os.getenv("PRINT_TRANS")) # for printing
UNFAIR = int(os.getenv("UNFAIR"))

INITIAL_STAKE = 10.0

class Wallet:

    def __init__(self, ip_address: str, port: int, bootstrap=False) -> None:
        self.ip_address = ip_address
        self.port = port
        self.address = f"{ip_address}:{port}"
        self.bootstrap = bootstrap
        self.balance = 0.0
        self.stake = INITIAL_STAKE if not (UNFAIR and self.bootstrap) else 100.0
        self.nonce = 0  # counter for the number of transactions
        self.private_key, self.public_key = self.generate_wallet()

        self.blockchain_state = {}  # soft state
        """
        State will contain a dictionary of all the nodes:
        {address: {public_key, id, balance, stake} dictionaries}}
        """
        self.blockchain_state_hard = {}  # hard state

        self.transactions_pending = {}  # received transactions that have not been added to a block yet
        self.transactions_rejected = {}  # rejected transactions
        # missing transaction: transactions that were contained in a received block
        # but we have not yet received them individually
        self.transactions_missing = {}

        self.pending_blocks = {}  # list of blocks that have been received out of order

        self.blockchain = Blockchain()

        # lock that protects shared resources of the wallet object from race conditions
        # due to simultaneous access from multiple threads
        self.total_lock = threading.Lock()
        # event that is set when the received (and pending) transactions exceed the capacity of the blocks
        self.capacity_full = threading.Event()
        # event that is set whenever a block is added to the chain,
        # in order to check if out of order blocks can now be added
        self.received_block = threading.Event()

        self.nonce_sets = {}  # nonce sets for each node

        # for debugging purposes
        self.transaction_history = []
        self.processed_transactions = {}

        # for debugging purposes
        self.received_transactions_count = 0
        self.accepted_transactions_count = 0

        if bootstrap:
            self.id = 0
            self.given_id = 0
            self.blockchain_state[self.address] = {"public_key": self.public_key,
                                                   "id": self.id,
                                                   "balance": 0.0,
                                                   "stake": INITIAL_STAKE if not UNFAIR else 100.0} # Initial stake is 5 coins, and 100 for the fairness experiment

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
                print("Error:", response.json())
                sys.exit(1)

            print("Bootstrap is notified of new node.")
            self.id = response.json()['id']
            print(f"New node ID is {self.id}.")

    def create_genesis_block(self):
        # we call the create transaction function (the same as init of transaction)
        tran = self.create_transaction(sender_address='0',
                                       receiver_address=self.address,
                                       type_of_transaction="coins",
                                       amount=INITIAL_COINS * TOTAL_NODES,
                                       message="Genesis block",
                                       nonce=self.nonce)
        # We don't verify the transaction because it's the genesis block, so we process it directly
        self.process_transaction(tran)
        genesis_block = Block(index=0, timestamp=time.time(),
                              transactions=[tran], validator=-1, previous_hash='1')
        self.blockchain.add_block(genesis_block)

    @staticmethod
    def generate_wallet() -> tuple:
        rsa_keypair = RSA.generate(2048)
        private_key = rsa_keypair.export_key()
        public_key = rsa_keypair.publickey().export_key()
        return private_key.decode(), public_key.decode()

    def process_transaction(self, transaction: Transaction, use_soft=True) -> None:
        # Case: Stake, check also self.stake
        if transaction.receiver_address == "0":
            if use_soft:
                self.blockchain_state[transaction.sender_address]["stake"] = transaction.amount
            else:
                self.blockchain_state_hard[transaction.sender_address]["stake"] = transaction.amount
            if transaction.sender_address == self.address:
                self.stake = transaction.amount

        # Case: Coins
        elif transaction.type_of_transaction == "coins":
            # Check if self is receiving/sending
            if transaction.receiver_address == self.address:
                self.balance += transaction.amount
            elif transaction.sender_address == self.address:
                self.balance -= transaction.amount

            # Update the blockchain state balance for the sender
            if transaction.sender_address != "0":
                if use_soft:
                    self.blockchain_state[transaction.sender_address]["balance"] -= transaction.amount
                else:
                    self.blockchain_state_hard[transaction.sender_address]["balance"] -= transaction.amount
                # 3% fee for the sender (the initial 1000 BCC transactions don't have a fee)
                fee = round(transaction.amount * 0.03, 3) if transaction.message != "Initial Transaction" else 0
                if use_soft:
                    self.blockchain_state[transaction.sender_address]["balance"] -= fee
                else:
                    self.blockchain_state_hard[transaction.sender_address]["balance"] -= fee
                if transaction.sender_address == self.address:
                    self.balance -= fee

            # Update blockchain state for receiver
            if use_soft:
                self.blockchain_state[transaction.receiver_address]["balance"] += transaction.amount
            else:
                self.blockchain_state_hard[transaction.receiver_address]["balance"] += transaction.amount

        elif transaction.type_of_transaction == "message":
            fee = len(transaction.message)
            if use_soft:
                self.blockchain_state[transaction.sender_address]["balance"] -= fee
            else:
                self.blockchain_state_hard[transaction.sender_address]["balance"] -= fee
            if transaction.sender_address == self.address:
                self.balance -= transaction.amount

        self.balance = round(self.balance, 3)

        if not use_soft:
            self.accepted_transactions_count += 1

        return

    def register_node(self, address: str, public_key: str) -> None:
        self.blockchain_state[address] = {"public_key": public_key,
                                          "id": self.given_id,
                                          "balance": 0.0,
                                          "stake": INITIAL_STAKE}
        return

    @staticmethod
    def create_transaction(sender_address: str, receiver_address: str,
                           type_of_transaction: str, amount: float, message: str, nonce: int
                           ) -> Transaction:
        transaction = Transaction(sender_address, receiver_address, type_of_transaction, amount, message, nonce)
        return transaction

    def broadcast_transaction(self, transaction: Transaction) -> bool:
        # Increment the nonce of the wallet to keep track of the number of transactions
        # and prevent replay attacks/double spending
        self.nonce += 1
        transaction.nonce = self.nonce

        self.transaction_history.append(transaction)

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
            response = requests.post(f"http://{node_ip}:{node_port}/api/receive_transaction",
                                     data=payload,
                                     headers={'Content-Type': 'application/json'})
            if response.status_code != 200:
                print("Error:", response.json())
                return False

        self.total_lock.acquire()
        
        self.nonce_sets[transaction.sender_address].add(self.nonce)

        # If, before we add our own transaction to pending list, we receive it from a block, it will be in missing list
        # Then, do not process it, just return.
        if transaction.transaction_id in self.transactions_missing:
            del self.transactions_missing[transaction.transaction_id]
            self.total_lock.release()
            return True

        if transaction.sender_address != '0':
            self.transactions_pending[transaction.transaction_id] = transaction
        self.process_transaction(transaction)
        if len(self.transactions_pending) >= CAPACITY:
            self.capacity_full.set()

        self.total_lock.release()

        return True

    def stake_amount(self, amount: int) -> bool:
        """Stake a certain amount of coins to be able to mine a block
           A transaction is created to stake the amount of coins
           with a receiver address of '0' 
        """
        if amount > self.balance:
            print(f"Insufficient balance. You have {self.balance} coins. Requested stake: {amount} coins")
            return False

        transaction = self.create_transaction(sender_address=self.address,
                                              receiver_address='0',
                                              type_of_transaction="coins",
                                              amount=amount,
                                              message="",
                                              nonce=self.nonce)
        if self.broadcast_transaction(transaction):
            return True
        print("Error: Transaction was not broadcasted.")
        return False

    def mine_block(self) -> bool:
        self.total_lock.acquire()
        CURRENT_BLOCK_TRANSACTIONS = list(self.transactions_pending.values())[:CAPACITY]

        last_block = self.blockchain.chain[-1]
        validator = self.lottery()
        # recheck if there are enough transactions because the miner thread might wake up due to timeout
        if validator != self.id or len(list(self.transactions_pending)) <= CAPACITY:
            self.total_lock.release()
            return True

        new_block = Block(index=last_block.index + 1, timestamp=time.time(),
                          transactions=CURRENT_BLOCK_TRANSACTIONS, validator=validator,
                          previous_hash=last_block.current_hash)

        broadcast_result = self.broadcast_block(new_block)
        if broadcast_result:
            reward = new_block.calculate_reward()
            self.balance += reward
            self.blockchain_state[self.address]["balance"] += reward
        else:
            self.total_lock.release()
            return False
        self.blockchain.add_block(new_block)

        # update hard state only with the transactions that were contained inside the broadcast block
        for transaction in CURRENT_BLOCK_TRANSACTIONS:
            self.process_transaction(transaction, False)
            if PRINT_TRANS == 1:
                file_path = f"{self.id}-trans.txt"
                with open(file_path, 'a') as file:
                    file.write(f"{transaction.sender_address} - {transaction.nonce}\n")
                file_path = f"{self.id}-trans-place.txt"
                with open(file_path, 'a') as file:
                    file.write(f"{transaction.sender_address} - {transaction.nonce} FROM MINE_BLOCK\n")

        if PRINT_TRANS == 1:
            file_path = f"{self.id}-trans.txt"
            with open(file_path, 'a') as file:
                file.write(f"{self.address} is given {reward}\n")
            file_path = f"{self.id}-trans-place.txt"
            with open(file_path, 'a') as file:
                file.write(f"{self.address} is given {reward} FROM MINE_BLOCK\n")
        self.blockchain_state_hard[self.address]["balance"] += reward

        self.transactions_pending = dict(list(self.transactions_pending.items())[CAPACITY:])

        self.total_lock.release()

        return True

    def broadcast_block(self, block: Block) -> bool:
        payload = block.serialize()
        response = None
        for node in self.blockchain_state.keys():
            if node == self.address:
                continue
            node_ip = node.split(":")[0]
            node_port = node.split(":")[1]
            response = requests.post(f"http://{node_ip}:{node_port}/api/receive_block",
                                     data=payload,
                                     headers={'Content-Type': 'application/json'})
            if response.status_code != 200:
                print("Error:", response.json())
                break
        if response.status_code == 200:
            return True
        else:
            return False

    def lottery(self, idx=0):
        """Select a random node to mine a block"""
        # Create a lottery where the probability of winning is proportional to the stake of each node
        lottery = []
        id_list = [entry['id'] for entry in self.blockchain_state.values()]
        nodes = self.blockchain_state.keys()
        for id, node in zip(id_list, nodes):
            lottery += [id] * int(100 * (self.blockchain_state[node]["stake"]))

        # If there are no stakes, select a random node
        if not lottery:
            lottery = id_list

        # Set the seed to be the hash of the last block (or the previous block if an idx is given)
        random.seed(self.blockchain.chain[idx - 1].current_hash)
        winner = lottery[random.randint(0, len(lottery) - 1)]
        return winner
