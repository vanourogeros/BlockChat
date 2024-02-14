import datetime
import time
from dotenv import load_dotenv
import os

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
CAPACITY = int(os.getenv("CAPACITY"))

class Block:

    def __init__(self, index, timestamp, transactions, validator, previous_hash, current_hash):
        self.index = index
        self.timestamp = timestamp
        self.transactions = transactions
        self.validator = validator
        self.previous_hash = previous_hash
        self.current_hash = current_hash

    def mint_block(self):
        # tha mpei kan edw? h sto wallet?
        pass
