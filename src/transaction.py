import json
from Crypto.Hash.SHA256 import SHA256Hash
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA


class Transaction:

    def __init__(self, sender_address: str, receiver_address: str, type_of_transaction: str, amount: float,
                 message: str, nonce: int, transaction_id: str = None, signature: str = None) -> None:
        if type_of_transaction not in ["coins", "message"]:
            raise ValueError("Invalid argument type_of_transaction. It should be either 'coins' or 'message'.")

        self.sender_address = sender_address
        self.receiver_address = receiver_address
        self.type_of_transaction = type_of_transaction
        self.amount = amount
        self.message = message
        self.nonce = nonce
        if transaction_id is None:
            self.transaction_id = self.hash_transaction().hexdigest()
        else:
            self.transaction_id = transaction_id
        if signature is None:
            self.signature = 'empty'
        else:
            self.signature = signature

        return

    def stringify(self) -> str:
        transaction = {
            "sender_address": self.sender_address,
            "receiver_address": self.receiver_address,
            "type_of_transaction": self.type_of_transaction,
            "amount": self.amount,
            "message": self.message,
            "nonce": self.nonce
        }

        return json.dumps(transaction)

    def hash_transaction(self) -> SHA256Hash:
        serialized_transaction = self.stringify().encode('utf-8')
        sha256_hash_object = SHA256.new(serialized_transaction)

        return sha256_hash_object

    def sign_transaction(self, private_key: str) -> None:
        hash_obj = self.hash_transaction()
        private_key_obj = RSA.import_key(private_key)
        signer = PKCS1_v1_5.new(private_key_obj)
        signature = signer.sign(hash_obj).hex()
        self.signature = signature

        return

    def verify_signature(self, public_key: str) -> bool:
        hash_obj = self.hash_transaction()
        public_key_obj = RSA.import_key(public_key)
        verifier = PKCS1_v1_5.new(public_key_obj)
        return verifier.verify(hash_obj, bytes.fromhex(self.signature))

    def verify_balance(self, sender_balance: int, stake: int) -> bool:
        paid_amount = 1.03 * self.amount if self.type_of_transaction == "coins" else len(self.message)
        if paid_amount <= sender_balance - stake:
            return True
        else:
            print(f"Insufficient balance - Balance: {sender_balance}. Amount: {self.amount}. Stake: {stake}.")
            return False

    def serialize(self) -> str:
        transaction = {
            "sender_address": self.sender_address,
            "receiver_address": self.receiver_address,
            "type_of_transaction": self.type_of_transaction,
            "amount": self.amount,
            "message": self.message,
            "nonce": self.nonce,
            "transaction_id": self.transaction_id,
            "signature": self.signature
        }

        return json.dumps(transaction)


def deserialize_trans(data: str) -> Transaction:
    trans = json.loads(data)
    return Transaction(trans["sender_address"], trans["receiver_address"], trans["type_of_transaction"],
                       trans["amount"], trans["message"], trans["nonce"], trans["transaction_id"], trans["signature"])
