import json
import argparse
import socket
from protocol import *
import signal
import sys
from block import *
import uuid
import time

# USAGE: python3 application.py <app_port>

class Vote:
    def __init__(self, user_id, vote, timestamp, name):
        """
        Initializes a Vote object.
        
        Parameters:
        - user_id (str): The unique identifier of the user who cast the vote.
        - vote (str): The vote cast by the user.
        - timestamp (int): The timestamp when the vote was cast.
        - name (str): The name associated with the user.
        """
        self.user_id = user_id
        self.vote = vote
        self.name = name
        self.timestamp = timestamp

class BlockchainVoting:
    
    def __init__(self, app_port, user_id, name):
        """
        Initializes a BlockchainVoting object.

        Parameters:
        - app_port (int): The port number for the application.
        - user_id (str): The unique identifier of the user participating in the voting process.
        - name (str): The name associated with the user.
        """
        self.app_port = app_port
        self.peer_connection_socket = None
        self.has_voted = False
        self.user_id = user_id
        self.name = name
        signal.signal(signal.SIGINT, self.signal_handler)


    def signal_handler(self, signal, frame):
        """
        handle termination of the app when interrupted by Ctrl-C
        """
        if self.peer_connection_socket:
            self.peer_connection_socket.close()
        sys.exit(0)


    def connect_to_peer(self):
        """
        connect to the peer
        """
        self.peer_connection_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.peer_connection_socket.connect(("127.0.0.1", self.app_port))


    def ask_for_tally(self):
        """
        ask the peer for its local blockchain
        """
        message = json.dumps([TALLY_VOTE])
        self.peer_connection_socket.sendall(message.encode('utf-8'))

        raw_data = recv_wrapper(self.peer_connection_socket)
        data = json.loads(raw_data)

        if data[0] == RETURNED_BLOCKCHAIN:
            self.tally_votes(data[1])
        elif data[0] == APP_LEAVE_NETWORK:
            print("peer is leaving the network, exiting...")
            self.peer_connection_socket.close()
            self.peer_connection_socket = None
            sys.exit(0)
        else:
            print("invalid message from a peer")


    def cast_a_vote(self, staged_attack):
        """
        let the user cast a vote which will go down to the peer's blockchain
        wait for confirmation of whether the vote went through

        Parameters:
        - staged_attack (bool): A flag indicating whether the vote is part of a staged attack.
        """
        if self.has_voted and not staged_attack:
            print("you have already cast your vote.")
            return

        vote = input("enter your vote: ")
        timestamp = time.time()
        vote_obj = Vote(self.user_id, vote, timestamp, self.name)
        message = json.dumps([CAST_VOTE, vote_obj.__dict__, staged_attack])
        self.peer_connection_socket.sendall(message.encode('utf-8'))

        raw_data = recv_wrapper(self.peer_connection_socket)

        data = json.loads(raw_data)

        if data[0] == TRANSACTION_STATUS:
            if data[1] == True:
                self.has_voted = True
                print("Vote cast successfully.")
            else:
                print("Vote failed, please try again")
        elif data[0] == APP_LEAVE_NETWORK:
            print("peer has left the network, exiting...")
            self.peer_connection_socket.close()
            sys.exit(0)
        else:
            print("invalid message from a peer")


    def tally_votes(self, raw_blockchain):
        """
        Print out the current statistics of the votes based on the provided blockchain.

        Parameters:
        - raw_blockchain (list of dict): A list of dictionaries representing blocks in the blockchain.
        """
        #parse the blockchain
        blockchain = []
        for block_dict in raw_blockchain:
            block = from_dict(block_dict)
            blockchain.append(block)

        votes = {}
        for block in blockchain:
            if block.data:
                voted_for = block.data['vote']
                if voted_for in votes:
                    votes[voted_for] += 1
                else:
                    votes[voted_for] = 1

        print("----------------------")
        print("Current Voting Results:")
        if votes:
            for key, num_votes in votes.items():
                if num_votes > 1:
                    print(f"   {key} has {num_votes} votes")
                else:
                    print(f"   {key} has {num_votes} vote")
            max_votes = max(votes.values())
            leading_candidates = [candidate for candidate, votes in votes.items() if votes == max_votes]

            if len(leading_candidates) == 1:
                print(f"{leading_candidates[0]} is in the lead")
            else:
                leading_candidates_str = ", ".join(leading_candidates)
                print(f"{leading_candidates_str} are tied")
        else:
            print("No one has cast a vote yet.")
        print("----------------------")




if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='application script')
    parser.add_argument('app_port', type=int, help='app port')

    args = parser.parse_args()
    app_port = args.app_port

    print("Hello! Welcome to BlockchainVoting!")
    name = input("What is your name? ")
    user_id = str(uuid.uuid4())

    voting_app = BlockchainVoting(app_port, user_id, name)
    voting_app.connect_to_peer()

    while True:
        print("\nMenu Options:")
        print("   C: cast a vote")
        print("   T: tally votes")
        print("   S: stage attack")
        print("   Q: quit")

        option = input("Choose an option: ").upper()

        if option == "C":
            voting_app.cast_a_vote(False)
        elif option == "T":
            voting_app.ask_for_tally()
        elif option == "S":
            print("This will stage an attack by creating an invalid block that other peers will then reject.")
            voting_app.cast_a_vote(True)
        elif option == "Q":
            if voting_app.peer_connection_socket:
                voting_app.peer_connection_socket.close()
            sys.exit(0)
        else:
            print("invalid option. please try again!")
