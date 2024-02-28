import datetime
import json
import os

from Crypto.Hash.SHA256 import SHA256Hash
from Crypto.Hash import SHA256

from src.blockchain import Blockchain

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
CAPACITY = int(os.getenv("CAPACITY"))


class Block:

    def __init__(self, index: int, timestamp: datetime, transactions: list, validator: int,
                 previous_hash: str) -> None:
        self.index = index
        self.timestamp = timestamp
        self.transactions = transactions
        self.validator = validator
        self.previous_hash = previous_hash
        self.current_hash = self.hash_block().hexdigest()

    def stringify(self) -> str:
        block = {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": list(map(lambda transaction: transaction.serialize(), self.transactions)),
            "validator": self.validator,
            "previous_hash": self.previous_hash
        }
        return json.dumps(block)

    def hash_block(self) -> SHA256Hash:
        serialized_block = self.stringify().encode('utf-8')
        sha256_hash_object = SHA256.new(serialized_block)
        return sha256_hash_object

    def validate_block(self, blockchain: Blockchain, validator) -> bool:
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
        if self.current_hash != self.hash_block().hexdigest():
            print(f"[INVALID BLOCK]: Current hash field is not equal to the hash of the block.")
            return False
        
        # Verify the winner of the block
        if self.validator != validator:
            print(f"[INVALID BLOCK]: Validator field is not equal to the validator calculated."
                   f"Calculated: {validator} \n"
                   f"Given: {self.validator}")
            return False


        return True

    def serialize(self) -> str:
        block = {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": list(map(lambda transaction: transaction.serialize(), self.transactions)),
            "validator": self.validator,
            "previous_hash": self.previous_hash,
            "current_hash": self.current_hash
        }
        return json.dumps(block)
