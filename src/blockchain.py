import threading
from dotenv import load_dotenv
import os

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
CAPACITY = int(os.getenv("CAPACITY"))


class Blockchain:
    def __init__(self) -> None:
        self.chain = []
        self.lock = threading.Lock()

    def view_block(self) -> None:
        if len(self.chain) == 0:
            print("Blockchain empty")
            return

        last_block = self.chain[-1]
        print("Validator of last block", last_block.validator)
        for tran in last_block.transactions:
            print(tran)
        return

    def add_block(self, block) -> None:
        self.lock.acquire()
        self.chain.append(block)
        self.lock.release()

    def validate_chain(self) -> bool:
        curr_index = 0  # genesis block is handled in validate_block

        while curr_index < len(self.chain):
            curr_block = self.chain[curr_index]
            if not curr_block.validate_block(self):
                return False
            curr_index += 1

        return True

    # For debugging purposes
    def print_block_lengths(self):
        print("Blockchain length:", len(self.chain))
        for block in self.chain:
            if len(block.transactions) != CAPACITY:
                print("Block length:", len(block.transactions))

        for block in self.chain:
            print(f"\n\nBLOCK {block.index}\n")
            for transaction in block.transactions:
                print(f"{transaction.sender_address} - {transaction.nonce}")
            print()
        return
