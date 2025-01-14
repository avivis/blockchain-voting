"""
class definition for a Block in blockchain

"""
import hashlib 
import uuid
import random

DIFFICULTY = 3

class Block:
    def __init__(self, data=None, blockchain=None, id=None, nonce=None, prev_hash=None, hash=None):
        self.id = id if id is not None else str(uuid.uuid4())
        self.nonce = nonce if nonce is not None else random.randint(0, 2**32)
        if prev_hash:
            self.prev_hash = prev_hash
        else:
            if blockchain:
                self.prev_hash = blockchain[-1].hash
            else:
                self.prev_hash = "0000000000000000000000000000000000000000000000000000000000000000"
        self.data = data
        self.hash = hash
    

    def calculate_hash(self):
        """
        creates a hash of everything in the block
        """
        block_content = f"{self.id}{self.prev_hash}{self.data}{self.nonce}"
        return hashlib.sha256(block_content.encode()).hexdigest()
    

    def mine(self):
        """
        mines for the correct nonce to match the difficulty
        """
        while not self.is_valid():
            self.nonce += 1
            self.hash = self.calculate_hash()


    def is_valid(self):
        """
        checks if the hash matches the difficulty
        """
        if self.hash is None:
            return False
        return self.hash.startswith('0' * DIFFICULTY)
    

    def to_dict(self):
        """
        converts a Block to a dictionary
        used for sending over the network
        """
        return {
            "id": self.id,
            "nonce": self.nonce,
            "prev_hash": self.prev_hash,
            "data": self.data,
            "hash": self.hash
        }

    def __str__(self):
        return f"Block ID: {self.id}\nPrevious Hash: {self.prev_hash}\nNonce: {self.nonce}\nData: {self.data}\nHash: {self.hash}"


def from_dict(block_dict):
    """
    creates a Block from a dictionary
    used for receiving a block over the network  
    """
    id = block_dict.get('id')
    nonce = block_dict.get('nonce')
    prev_hash = block_dict.get('prev_hash')
    data = block_dict.get('data')
    hash = block_dict.get('hash')
    return Block(data=data, blockchain=None, id=id, nonce=nonce, prev_hash=prev_hash, hash=hash)