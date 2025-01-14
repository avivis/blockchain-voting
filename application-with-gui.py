import tkinter as tk
from tkinter import messagebox, simpledialog
import json
import socket
from protocol import *
import signal
import sys
from block import *
import uuid
import time

# USAGE: python3 application-with-gui.py <app_port>

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
            messagebox.showinfo("Info", "Peer is leaving the network, exiting...")
            self.peer_connection_socket.close()
            self.peer_connection_socket = None
            sys.exit(0)
        else:
            messagebox.showerror("Error", "Invalid message from a peer")
    
    def cast_a_vote(self, staged_attack):
        """
        let the user cast a vote which will go down to the peer's blockchain
        wait for confirmation of whether the vote went through

        Parameters:
        - staged_attack (bool): A flag indicating whether the vote is part of a staged attack.
        """
        if self.has_voted and not staged_attack:
            messagebox.showinfo("Info", "You have already cast your vote.")
            return

        vote = simpledialog.askstring("", "Enter your vote:")
        timestamp = time.time()
        vote_obj = Vote(self.user_id, vote, timestamp, self.name)
        message = json.dumps([CAST_VOTE, vote_obj.__dict__, staged_attack])
        self.peer_connection_socket.sendall(message.encode('utf-8'))

        raw_data = recv_wrapper(self.peer_connection_socket)

        data = json.loads(raw_data)

        if data[0] == TRANSACTION_STATUS:
            if data[1] == True:
                self.has_voted = True
                messagebox.showinfo("Info", "Vote cast successfully.")
            else:
                messagebox.showinfo("Info", "Vote failed, please try again")
        elif data[0] == APP_LEAVE_NETWORK:
            messagebox.showinfo("Info", "peer has left the network, exiting...")
            self.peer_connection_socket.close()
            sys.exit(0)
        else:
            messagebox.showinfo("Info", "invalid message from a peer")

    def tally_votes(self, raw_blockchain):
        """
        Print out the current statistics of the votes based on the provided blockchain.

        Parameters:
        - raw_blockchain (list of dict): A list of dictionaries representing blocks in the blockchain.
        """
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
        result = "----------------------\nCurrent Voting Results:\n"
        if votes:
            for key, num_votes in votes.items():
                if num_votes > 1:
                    result += f"{key} has {num_votes} votes\n"
                else:
                    result += f"{key} has {num_votes} vote\n"
            max_votes = max(votes.values())
            leading_candidates = [candidate for candidate, votes in votes.items() if votes == max_votes]
            if len(leading_candidates) == 1:
                result += f"{leading_candidates[0]} is in the lead\n"
            else:
                leading_candidates_str = ", ".join(leading_candidates)
                result += f"{leading_candidates_str} are tied\n"
        else:
            result += "No one has cast a vote yet.\n"
        result += "----------------------"
        messagebox.showinfo("Voting Results", result)

class VotingAppGUI:
    def __init__(self, app_port):
        """
        Initializes the VotingAppGUI.

        Parameters:
        - app_port (int): The port number for the application.
        """
        self.root = tk.Tk()
        self.root.title("Blockchain Voting App")
        self.app_port = app_port
        self.user_id = None
        self.name = None
        self.voting_app = None

        self.setup_connection_screen()

    def setup_connection_screen(self):
        """
        Sets up the connection screen for the application.
        """
        self.connection_frame = tk.Frame(self.root)
        self.connection_frame.pack(pady=20)

        tk.Label(self.connection_frame, text="Welcome to Blockchain Voting App!", font=("Helvetica", 16)).pack()
        tk.Label(self.connection_frame, text="Please enter your name:", font=("Helvetica", 12)).pack()
        self.name_entry = tk.Entry(self.connection_frame, font=("Helvetica", 12))
        self.name_entry.pack(pady=10)
        connect_button = tk.Button(self.connection_frame, text="Connect", command=self.connect_to_voting_app, font=("Helvetica", 12))
        connect_button.pack(pady=10)

    def connect_to_voting_app(self):
        """
        Establishes connection to the Blockchain Voting application.
        """
        self.name = self.name_entry.get().strip()
        if not self.name:
            messagebox.showerror("Error", "Please enter your name.")
            return
        self.user_id = str(uuid.uuid4())
        self.connection_frame.destroy()
        self.setup_voting_screen()
        self.voting_app = BlockchainVoting(self.app_port, self.user_id, self.name)
        self.voting_app.connect_to_peer()

    def setup_voting_screen(self):
        """
        Sets up the main voting screen.
        """
        self.voting_frame = tk.Frame(self.root)
        self.voting_frame.pack(pady=20)

        tk.Label(self.voting_frame, text=f"Welcome, {self.name}!", font=("Helvetica", 16)).pack()
        button_width = 20  
        vote_button = tk.Button(self.voting_frame, text="Cast a Vote", command=self.cast_vote, font=("Helvetica", 12), width=button_width)
        vote_button.pack(pady=5)
        tally_button = tk.Button(self.voting_frame, text="Tally Votes", command=self.ask_for_tally, font=("Helvetica", 12), width=button_width)
        tally_button.pack(pady=5)
        attack_button = tk.Button(self.voting_frame, text="Stage Attack", command=self.stage_attack, font=("Helvetica", 12), width=button_width)
        attack_button.pack(pady=5)
        quit_button = tk.Button(self.voting_frame, text="Quit", command=self.quit_app, font=("Helvetica", 12), width=button_width)
        quit_button.pack(pady=5)

    def cast_vote(self):
        """
        Initiates the process of casting a vote.
        """
        if self.voting_app:
            self.voting_app.cast_a_vote(False)

    def ask_for_tally(self):
        """
        Requests the current tally of votes.
        """
        if self.voting_app:
            self.voting_app.ask_for_tally()

    def stage_attack(self):
        """
        Initiates the process of staging an attack.
        """
        if self.voting_app:
            self.voting_app.cast_a_vote(True)

    def quit_app(self):
        """
        Quits the application.
        """
        if self.voting_app and self.voting_app.peer_connection_socket:
            self.voting_app.peer_connection_socket.close()
        self.root.destroy()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Blockchain Voting Application')
    parser.add_argument('app_port', type=int, help='app port')
    args = parser.parse_args()
    app_port = args.app_port

    app = VotingAppGUI(app_port)
    app.root.geometry("400x300") 
    app.root.resizable(False, False) 
    app.root.mainloop()
