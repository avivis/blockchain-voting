import socket
import json
import threading
import time
import argparse
from protocol import *
from block import *
import signal
import sys

#USAGE: python3 peer.py <tracker_ip> <tracker_port> <peer_port> <app_port>

"""
Flow:

1. connect_to_tracker()
    a. creates a socket and connects to the tracker node 
2. join_network()
    a. sends a message indicating that the peer is joining network
3. request_blockchain()
    a. calls get_peers() 
    b. then it gets first peer and it calls send_data() to peer to request blockchain
4. start_listen_peer()
    a. starts a new thread with listen_for_data() 
    b. listen_for_data()
        1. accepts new connections from other peers, each accepted connection represents 
           one message from a peer 
        2. elif iterates over different message types and handles them accordingly
            a. REQ_CHAIN: send blockchain back to the requester 
            b. RECV_CHAIN: set the blockchain to the received chain if empty (which should be the first a peer recvs)
            c. NEW_BLOCK: call validate_block() which checks to see if new_block prev_hash aligns with local chain, sends block_status and updates
               dictionary
            d. BLOCK_STATUS: indication from a peer that they have either added or rejected sent block, will update self.block_status_dict
            e. BLOCK_REJECT: will remove the rejected block from the end of the blockchain (assuming it is at the end)
5. start_listen_app() 
    a. create a new thread which calls listen_for_app_messages() 
        1. recieves new messages coming in from application over the designated socket
        2. elif iterates over different message types and handles them accordingly
            a. CAST_VOTE: calls create_new_block()
                I. create and mine a new block, broadcast it to all peers, wait until all peers have accepted/rejected and act accordingly 
            b. TALLY_VOTE:
                I. sends the blockchain back to the application using send_message_to_app()
            c. PEER_LEAVE_NETWORK:
                I. causes the peer to leave the network

"""


class Peer:
    def __init__(self, tracker_ip, tracker_port, peer_port, app_port):
        self.tracker_ip = tracker_ip
        self.tracker_port = tracker_port
        self.peer_port = peer_port
        self.app_port = app_port
        self.tracker_socket = None
        self.app_socket = None
        self.client_socket = None #for the currently-connected application
        self.my_ip = get_external_ip()
        self.blockchain = []

        ## Format: {block_id_1: {peer1: True, peer2: False}}
        self.block_status_dict = {}
        self.block_status_lock = threading.Lock()

        signal.signal(signal.SIGINT, self.signal_handler)
        
        
    def signal_handler(self, signal, frame):
        """
        leave network when interrupted by a Ctrl-C signal.
        """
        print("\nterminating...")
        if self.client_socket:
            termination_message = json.dumps([APP_LEAVE_NETWORK])
            self.send_message_to_app(termination_message)
        self.leave_network()
    

    def connect_to_tracker(self):
        """
        connect to the tracker
        """
        print("connecting to tracker")
        self.tracker_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tracker_socket.connect((self.tracker_ip, self.tracker_port))


    def join_network(self):
        """
        send a JOIN_NETWORK message to the tracker
        """
        print("joining the network")
        message = json.dumps([JOIN_NETWORK, self.my_ip])
        self.tracker_socket.sendall(message.encode('utf-8') + DELIMITER_BYTE)


    def leave_network(self):
        """
        send a LEAVE_NETWORK message to the tracker
        """
        print("leave the network...")
        message = json.dumps([LEAVE_NETWORK, self.my_ip])
        self.tracker_socket.sendall(message.encode('utf-8') + DELIMITER_BYTE)
        self.tracker_socket.close()
        if self.app_socket:
            self.app_socket.close()
        sys.exit(0)
    

    def start_listen_peer(self):
        """
        start listening for incoming messages from other peers
        """
        peer_listening_thread = threading.Thread(target=self.listen_for_data)
        peer_listening_thread.daemon = True
        peer_listening_thread.start()


    def start_listen_app(self):
        """
        start listening for incoming messages from apps
        """
        app_listening_thread = threading.Thread(target=self.listen_for_app_messages)
        app_listening_thread.start()


    def get_peers(self):
        """
        send a LIST_PEERS message to the tracker and receive a list of peers
        """
        message = json.dumps([LIST_PEERS, self.my_ip])
        self.tracker_socket.sendall(message.encode('utf-8') + DELIMITER_BYTE)
        peers_raw_data = recv_wrapper(self.tracker_socket)
        peers = json.loads(peers_raw_data)
        return peers


    def broadcast_data(self, data):
        """
        send data to all peers in the network
        """
        peers = self.get_peers()
        for peer_ip in peers:
            threading.Thread(target=self.send_data, args=(peer_ip, data)).start()


    def send_data(self, peer_ip, data):
        """
        send data to a specific peer
        """
        peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        peer_socket.connect((peer_ip, self.peer_port))
        peer_socket.sendall(data.encode('utf-8'))
        peer_socket.close()


    def listen_for_data(self):
        """
        listen for incoming messages from other peers
        """
        listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listening_socket.bind(('0.0.0.0', self.peer_port))
        listening_socket.listen(5)

        print("listening for incoming messages from peers...")

        while True:
            peer_socket, peer_address = listening_socket.accept()
            peer_ip = peer_address[0]
        
            raw_data = recv_wrapper(peer_socket)
            data = json.loads(raw_data)

            if data[0] == REQ_CHAIN:
                print(f"receiving data from peer {peer_ip}: requesting the blockchain")
                blockchain_dict = [block.to_dict() for block in self.blockchain]
                print(f"sending data to peer {peer_ip}: local blockchain")
                self.send_data(peer_ip, json.dumps([RECV_CHAIN, blockchain_dict]))
            elif data[0] == RECV_CHAIN:
                print(f"receiving data from peer {peer_ip}: receiving the blockchain")
                if len(self.blockchain) == 0:
                    blockchain = []
                    for block_dict in data[1]:
                        block = from_dict(block_dict)
                        blockchain.append(block)
                    self.blockchain = blockchain
            elif data[0] == NEW_BLOCK:
                print(f"receiving data from peer {peer_ip}: new block")
                new_block = from_dict(data[1])
                self.validate_block(new_block, peer_ip)
            elif data[0] == BLOCK_STATUS:
                print(f"receiving data from peer {peer_ip}: result of new block's verification")
                block_id = data[1]
                status = data[2]
                with self.block_status_lock:
                    if peer_ip not in self.block_status_dict[block_id]:
                        self.block_status_dict[block_id][peer_ip] = status
            elif data[0] == BLOCK_REJECT:
                print(f"receiving data from peer {peer_ip}: broadcast to reject the block")
                block_id_rejected = data[1]
                if self.blockchain:
                    if self.blockchain[-1].id == block_id_rejected:
                        self.blockchain.pop()
            peer_socket.close()



    def send_message_to_app(self, data):
        """
        send data to the application
        """
        if self.client_socket:
            self.client_socket.sendall(data.encode('utf-8'))
        else:
            print("No application currently connected")


    def listen_for_app_messages(self):
        """
        listen for incoming messages from the application
        """
        self.app_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.app_socket.bind(('0.0.0.0', self.app_port))
        self.app_socket.listen(5)

        print("listening for incoming messages from apps...")
        while True:
            try:
                self.client_socket, client_address = self.app_socket.accept()
                print("new application connected")

                self.handle_application_connection()
            except ConnectionResetError:
                print(f"Connection reset by peer: {client_address}")
                if self.client_socket:
                    self.client_socket.close()
                    self.client_Socket = None

            
    def handle_application_connection(self):
        """
        handle communication with a connected application
        """
        while True:
            raw_data = recv_wrapper(self.client_socket)
            if not raw_data:
                print("application has disconnected")
                self.client_socket.close()
                self.client_socket = None
                return

            data = json.loads(raw_data)

            if data[0] == CAST_VOTE:
                self.create_new_block(data[1], data[2])
                print_blockchain(self.blockchain)
            elif data[0] == TALLY_VOTE:
                blockchain_dict = [block.to_dict() for block in self.blockchain]
                self.send_message_to_app(json.dumps([RETURNED_BLOCKCHAIN, blockchain_dict]))
                print_blockchain(self.blockchain)


    def request_blockchain(self):
        """
        requests the blockchain from a peer when joining the network
        """
        peers = self.get_peers()
        if len(peers) == 0:
            # create the genesis block
            gen_block = Block(data=None, blockchain=self.blockchain)
            gen_block.mine()
            self.blockchain.append(gen_block)
            return
            
        peer_to_req = peers[0]
        data = json.dumps([REQ_CHAIN])
        print(f"sending data to peer {peer_to_req}: requesting their blockchain")
        self.send_data(peer_to_req, data)

    
    def create_new_block(self, data, attack):
        """
        creates a new block, mines for the nonce
        has an option to mess up the new block's previous hash, making it invalid
        broadcasts the block to all peers
        wait until all peers have accepted or rejected the block
        will either add the block to a local blockchain or broadcast a message for all peers to reject it
        sends message to user to indicate the result
        """
        new_block = Block(data=data, blockchain=self.blockchain)
        new_block.mine()
        if attack:
            new_block.prev_hash = self.attack_new_block(new_block)

        data = json.dumps([NEW_BLOCK, new_block.to_dict()])
        print("broadcasting to peers: new block")
        self.broadcast_data(data)
        peers = self.get_peers()
        with self.block_status_lock:
            self.block_status_dict[new_block.id] = {}
        
        while True:
            with self.block_status_lock:
                peer_statuses = self.block_status_dict[new_block.id]
                if len(peer_statuses) == len(peers):
                    break
        all_accepted = all(peer_statuses.values())
        if all_accepted:
            print("all peers have received and accepted the new block")
            self.blockchain.append(new_block)
        else:
            #some peers have rejected
            print("peers have REJECTED the new block")
            data = json.dumps([BLOCK_REJECT, new_block.id])
            print(f"broadcasting to peers: all should drop the new block if added")
            self.broadcast_data(data)

        result = json.dumps([TRANSACTION_STATUS, all_accepted])
        self.send_message_to_app(result)


    def attack_new_block(self, new_block):
        """
        creates a bad hash for a block
        """
        attacked_block_content = f"ATTACK{new_block.id}{new_block.prev_hash}{new_block.data}{new_block.nonce}"
        return hashlib.sha256(attacked_block_content.encode()).hexdigest()


    def validate_block(self, new_block, creator_ip):
        """
        validates a received block from another peer over the network
        if the hashes line up, it will add it to the local blockchain
        sends a message to the peer to indicate if it accepted or rejected it
        """
        if not self.blockchain:
            last_block_hash = None
        else:
            last_block_hash = self.blockchain[-1].hash

        if new_block.prev_hash == last_block_hash:
            status = True
            self.blockchain.append(new_block)
        else:
            print("REJECTED BLOCK")
            status = False

        data = json.dumps([BLOCK_STATUS, new_block.id, status])
        print(f"sending data to peer {creator_ip}: result of new block verification")
        self.send_data(creator_ip, data)


def print_blockchain(blockchain):
    """
    prints the blockchain
    """
    print("----------------------")
    if blockchain:
        for index, block in enumerate(blockchain):
            print(f"Block {index}:")
            print(block)
            print("----------------------")   
    else:
        print("   empty blockchain   ")
        print("----------------------")   
        

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='peer script')
    parser.add_argument('tracker_ip', type=str, help='tracker IP address')
    parser.add_argument('tracker_port', type=int, help='tracker port')
    parser.add_argument('peer_port', type=int, help='peer port')
    parser.add_argument('app_port', type=int, help='app port')

    args = parser.parse_args()

    tracker_ip = args.tracker_ip
    tracker_port = args.tracker_port
    peer_port = args.peer_port
    app_port = args.app_port

    peer = Peer(tracker_ip, tracker_port, peer_port, app_port)
    peer.connect_to_tracker()
    peer.join_network()
    peer.start_listen_peer()
    peer.request_blockchain()
    peer.start_listen_app()

