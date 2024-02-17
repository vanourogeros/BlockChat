import time
from block import Block
from transaction import Transaction
from blockchain import Blockchain
import requests

from Crypto.PublicKey import RSA

from dotenv import load_dotenv
import os

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
CAPACITY = int(os.getenv("CAPACITY"))
TOTAL_NODES = int(os.getenv("TOTAL_NODES"))

class Wallet:

    def __init__(self, ip_address: str, port: int, bootstrap=False) -> None:
        self.ip_address = ip_address
        self.port = port
        self.address = f"{ip_address}:{port}"
        self.bootstrap = bootstrap
        self.balance = 0
        self.stake = 0
        self.public_key, self.private_key = self.generate_wallet()

        """
        State will contain a list of all the nodes' 
        {ip_address:port, balance, stake} dictionaries
        """
        self.blockchain_state = []

        self.transactions_pending = []
        self.blockchain = Blockchain()

        if bootstrap:
            self.blockchain_state.append({"address": self.address, "balance":0, "stake":0})
            self.create_genesis_block()

    def create_genesis_block(self):
        #we call the create transaction function (the same as init of transaction)
        tran = self.create_transaction(sender_address='0',
                                      receiver_address=self.address, 
                                      type_of_transaction="coins", 
                                      amount=1000*TOTAL_NODES,
                                      message="Genesis block",
                                      nonce=0)
        # We don't verify the transaction because it's the genesis block, so we process it directly
        self.process_transaction(tran)
        genesis_block = Block(index=0, timestamp=time.time(),
                              transactions=[tran], validator=0, previous_hash=1)
        self.blockchain.add_block(genesis_block)


    @staticmethod
    def generate_wallet() -> tuple:
        rsa_keypair = RSA.generate(2048)
        private_key = rsa_keypair.export_key()
        public_key = rsa_keypair.publickey().export_key()
        return (private_key.decode(), public_key.decode())
    
    def process_transaction(self, transaction: Transaction) -> None:
        # Update the balance of the wallet for a verified transaction
        if transaction.type_of_transaction == "coins":
            if transaction.receiver_address == self.address:
                self.balance += transaction.amount
            elif transaction.sender_address == self.address:
                self.balance -= transaction.amount
        self.add_transaction(transaction)
        return

    def get_network_state(self):
        if self.bootstrap:
            return self.blockchain_state
        else:
            #TODO: This is not right lmao
            response = requests.post(f"http://{self.ip_address}:{self.port}/api/get_network_state")
            if response.status_code == 200:
                return response.json()["data"]
            else:
                return []


    def register_node(self, ip_address: str, port: int) -> None:
        self.blockchain_state.append((ip_address, port, 0))
        self.stakes.append(0)
    
    def create_transaction(self, sender_address: str, receiver_address: str, 
                           type_of_transaction: str, amount: float, message: str, nonce: int
                           ) -> Transaction:
        transaction = Transaction(sender_address, receiver_address, type_of_transaction, amount, message, nonce)
        transaction.sign_transaction(self.private_key)
        return transaction
    
    def add_transaction(self, transaction: Transaction) -> None:
        self.transactions_pending.append(transaction)
        
    def mine_block(self):
        if len(self.transactions_pending) == 0:
            print(f"(pid={os.getpid}) [INVALID BLOCK]: No transactions to mine (pending transactions list is empty)")
            return False
        
        last_block = self.blockchain.chain[-1]
        new_block = Block(index=last_block.index + 1, timestamp=time.time(), transactions=self.transactions_pending,
                          validator=self.public_key, previous_hash=last_block.current_hash)
        new_block.current_hash = new_block.__hash_block()
        self.blockchain.add_block(new_block)
        self.transactions_pending = []
        return new_block