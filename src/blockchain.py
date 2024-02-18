#from src.block import Block
#from src.transaction import Transaction
import time
import json

class Blockchain:
    def __init__(self) -> None:
        self.chain = []
        # self.create_genesis_block() # isws auto na ginetai apo th wallet??

    # def create_genesis_block(self): #perhaps declared in wallet in bootstrap
    #     #we call the create transaction function (the same as init of transaction)
    #     tran = create_transaction(sender_address: '0',
    #                               receiver_address: "bootstrap address", 
    #                               type_of_transaction: "coins", 
    #                               amount: 1000*nodes,
    #                               message: "Genesis block",
    #                               nonce: 0)
    #     genesis_block = Block(index=0, timestamp=time.time(),
    #                           transactions=[tran], validator=0, current_hash='', previous_hash=1)
    #     self.chain.append(genesis_block)


    def view_block(self):
        if len(self.chain) == 0:
            print("Blockchain empty")
            return
        
        last_block = self.chain[-1]
        print("Validator of last block", last_block.validator)
        for tran in last_block.transactions:
            print(tran)
        return


    def add_block(self, block): #thn eftiaxa na yparxxei
        self.chain.append(block)

    def validate_chain(self):
        curr_index = 0 #genesis block is handled in validate_block

        while curr_index < len(self.chain):
            curr_block = self.chain[curr_index]
            if not curr_block.validate_block(self):
                return False
            curr_index += 1
        
        return True