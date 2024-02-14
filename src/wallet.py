from block import Block
from transaction import Transaction
from blockchain import Blockchain

from Crypto.PublicKey import RSA

class Wallet:

    def __init__(self, ip_address: str, port: int, bootstrap=False) -> None:
        self.ip_address = ip_address
        self.port = port
        self.public_key, self.private_key = self.generate_wallet()

    @staticmethod
    def generate_wallet():
        rsa_keypair = RSA.generate(2048)
        private_key = rsa_keypair.export_key()
        public_key = rsa_keypair.publickey().export_key()
        return (private_key.decode(), public_key.decode())