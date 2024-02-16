import time
from block import Block
from transaction import Transaction
from blockchain import Blockchain

from Crypto.PublicKey import RSA

class Wallet:

    def __init__(self, ip_address: str, port: int, bootstrap=False) -> None:
        self.ip_address = ip_address
        self.port = port
        self.public_key, self.private_key = self.generate_wallet()

        """
        State will contain a list of the users and their balances
        """
        self.blockchain_state = []

        """
        Each node will have a list of the stakes of all nodes
        """
        self.stakes = []
        self.transactions_pending = []
        self.blockchain = Blockchain()

    @staticmethod
    def generate_wallet() -> tuple:
        rsa_keypair = RSA.generate(2048)
        private_key = rsa_keypair.export_key()
        public_key = rsa_keypair.publickey().export_key()
        return (private_key.decode(), public_key.decode())
    
    def create_transaction(self, sender_address: str, receiver_address: str, 
                           type_of_transaction: str, amount: float, message: str, nonce: int
                           ) -> Transaction:
        transaction = Transaction(sender_address, receiver_address, type_of_transaction, amount, message, nonce)
        transaction.sign_transaction(self.private_key)
        return transaction
    
    def add_transaction(self, transaction: Transaction) -> None:
        self.transactions_pending.append(transaction)
        
    def mine_block(self):
        if not self.transactions_pending:
            print("No transactions to mine")
            return False
        
        last_block = self.blockchain.chain[-1]
        new_block = Block(index=last_block.index + 1, timestamp=time.time(), transactions=self.transactions_pending,
                          validator=self.public_key, previous_hash=last_block.current_hash)
        new_block.current_hash = new_block.__hash_block()
        self.blockchain.add_block(new_block)
        self.transactions_pending = []
        return new_block