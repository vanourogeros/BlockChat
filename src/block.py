import datetime
import json
import os

from Crypto.Hash.SHA256 import SHA256Hash
from Crypto.Hash import SHA256

from src.blockchain import Blockchain
from src.transaction import Transaction

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
CAPACITY = int(os.getenv("CAPACITY"))


class Block:

    def __init__(self, index: int, timestamp: datetime, transactions: list, validator: int,
                 previous_hash: SHA256Hash) -> None:
        self.index = index
        self.timestamp = timestamp
        self.transactions = transactions
        self.validator = validator
        self.previous_hash = previous_hash
        self.current_hash = self.hash_block()

    def serialize(self) -> str:
        block = {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": list(map(lambda transaction: transaction.serialize(), self.transactions)),
            "validator": self.validator,
            "previous_hash": str(self.previous_hash.digest()),
        }
        return json.dumps(block)

    def hash_block(self) -> SHA256Hash:
        serialized_block = self.serialize().encode('utf-8')
        sha256_hash_object = SHA256.new(serialized_block)
        return sha256_hash_object

    def validate_block(self, blockchain: Blockchain) -> bool:
        # For the genesis block we don't need to validate.
        # We suppose that the genesis block has a validator value of 0
        if self.validator == 0:
            return True

            # Fetch the previous block in the blockchain
        previous_block = blockchain.chain[self.index - 1]
        # Verify Hashes
        if self.previous_hash != previous_block.current_hash:
            print(
                f"(pid={os.getpid}) [INVALID BLOCK]: Previous hash field is not equal to the hash field of the last "
                f"block in the blockchain.")
            return False
        if self.current_hash != self.hash_block():
            print(f"(pid={os.getpid}) [INVALID BLOCK]: Current hash field is not equal to the hash of the block.")
            return False
        return True

    def mint_block(self):
        # tha mpei kan edw? h sto wallet?
        pass
