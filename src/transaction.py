import json
from Crypto.Hash.SHA256 import SHA256Hash
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA


class Transaction:

    def __init__(self, sender_address: str, receiver_address: str, type_of_transaction: str, amount: float,
                 message: str, nonce: int) -> None:
        if type_of_transaction not in ["coins", "message"]:
            raise ValueError("Invalid argument type_of_transaction. It should be either 'coins' or 'message'.")

        self.sender_address = sender_address
        self.receiver_address = receiver_address
        self.type_of_transaction = type_of_transaction
        self.amount = amount
        self.message = message
        self.nonce = nonce
        self.transaction_id = self.__hash_transaction().hexdigest()
        self.signature = ''

        return

    def serialize(self) -> str:
        print(self)
        transaction = {
            "sender_address": self.sender_address,
            "receiver_address": self.receiver_address,
            "type_of_transaction": self.type_of_transaction,
            "amount": self.amount,
            "message": self.message,
            "nonce": self.nonce
        }

        return json.dumps(transaction)

    def __hash_transaction(self) -> SHA256Hash:
        serialized_transaction = self.serialize().encode('utf-8')
        sha256_hash_object = SHA256.new(serialized_transaction)

        return sha256_hash_object

    def sign_transaction(self, private_key: str) -> None:
        hash_obj = self.__hash_transaction()
        private_key_obj = RSA.import_key(private_key)
        signer = PKCS1_v1_5.new(private_key_obj)
        signature = signer.sign(hash_obj)
        self.signature = signature

        return

    def verify_signature(self, public_key: str) -> bool:
        hash_obj = self.__hash_transaction()
        public_key_obj = RSA.import_key(public_key)
        verifier = PKCS1_v1_5.new(public_key_obj)
        return verifier.verify(hash_obj, self.signature.encode('utf-8'))
