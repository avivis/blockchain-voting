#Message types from app -> peer
CAST_VOTE = "CAST_VOTE"
TALLY_VOTE = "TALLY_VOTE"


#Message types from peer -> app
RETURNED_BLOCKCHAIN = "RETURNED_BLOCKCHAIN"
TRANSACTION_STATUS = "TRANSACTION_STATUS"
APP_LEAVE_NETWORK = "APP_LEAVE_NETWORK"


#Message types from peer -> peer
REQ_CHAIN = "REQ_CHAIN"
RECV_CHAIN = "RECV_CHAIN"
NEW_BLOCK = "NEW_BLOCK"
BLOCK_STATUS= "BLOCK_STATUS"
BLOCK_REJECT = "BLOCK_REJECT"


#Message types from peer -> tracker
JOIN_NETWORK = "JOIN_NETWORK"
LEAVE_NETWORK = "LEAVE_NETWORK"
LIST_PEERS = "LIST_PEERS"


#Delimiters in between messages for tracker-peer communication
DELIMITER_BYTE = b'\n'
DELIMITER_STR = "\n"


SOCKET_MAX_BYTES = 1024

def recv_wrapper(socket):
    """
    wrapper for recv that will ensure it reads the entire data sent at that time,
    not just enough to fill up 1 buffer
    """
    message_data = b''
    while True:
        chunk = socket.recv(SOCKET_MAX_BYTES)
        if not chunk:
            return None
        message_data += chunk
        if len(chunk) < SOCKET_MAX_BYTES: #received the full message
            break
    return message_data.decode('utf-8')


import urllib.request
import json

def get_external_ip():
    """
    get the external ip for the vm
    """
    with urllib.request.urlopen('https://httpbin.org/ip') as url:
        data = json.loads(url.read().decode())
        return data['origin']