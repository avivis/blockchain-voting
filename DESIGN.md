
# General Structure

The diagrams below represent the TCP connections between the three various programs. 

A directed arrow between two programs indicates the source program calling `connect()` over the socket as a client and the destination program calling `accept()` over the socket as a server. 

The navy connections are formed once at the beginning of each program and will `recv()` and `sendall()` in a loop, while the lighter blue connections are formed when a peer needs to send a message to another peer. This means that each new connection from a sending peer will go through `connect()`, `sendall()`, and `close()` in successtion to send a message, while the receiving peer will `accept()` in a loop for each new socket connection made (and singular message sent). Each peer will be listening on `peer_port` for incoming connections in a loop for the duration of the program.

The gray boxes around programs represent them running on the same VM. Essentially, each peer and connecting application will run on the same machine, and the tracker will run on its own machine. This aligns with how we designed the app-peer communication to always use IP address 127.0.0.1 to make the connection locally over port `app_port`.

### Architecture with 2 peers
<img src="https://github.com/csee4119-spring-2024/project-chainchicks/blob/main/2-peer-diagram.jpg" alt="Network with 2 peers" width="600" />

### Architecture with 3 peers
<img src="https://github.com/csee4119-spring-2024/project-chainchicks/blob/main/3-peer-diagram.jpg" alt="Network with 3 peers" width="600" />

## P2P (implemented in `peer.py` and `tracker.py`)

### Peer node (`peer.py`, using `protocol.py`):
Each peer is one node in the P2P network. They first connect to the tracker node to join the network and be able to interact with other peers. Each peer can also have an application connected to it to send down new transactions to create Blocks for. Each peer has a connection to the tracker, brief connections to other peers, and potentially a connection to an application. They use these three levels of communication to update the blockchain in sync with one another.

`signal_handler()`
* signal handler for CTRL-C (SIGINT) to send disconnect message to client and leave the network before exiting

`connect_to_tracker()`
* Opens a TCP socket and connects to the tracker over the tracker's port

`join_network()`
* sends a JOIN_NETWORK message to the tracker to join the network

`leave_network()`
* sends a LEAVE_NETWORK message to the tracker to leave the network

`start_listen_peer()`
* creates a new thread for `listen_for_data()` to accept incoming TCP connections and messages from peers

`start_listen_app()`
* creates a new thread for `listen_for_app_messages()` to receive incoming messages from the application

`get_peers()`
* requests the list of peers from the tracker and returns them

`broadcast_data()`
* gets all peers in the network using `get_peers()`
* creates a new thread for `send_data()` to send data to each peer

`send_data()`
* creates a TCP socket and connects to a specific peer
* sends data to the peer
* closes the socket

`listen_for_data()`
* creates a TCP socket to listen on
* iterates in a loop to accept all incoming connections and data from peers
* receives and parses various message types from peers

`send_message_to_app()`
* sends data over the connected app socket, it there is one connected

`listen_for_app_messages()`
* creates a new socket on localhost to designated port and listens for incoming application connections
* for each new application connected, calls `handle_application_connection()`

`handle_application_connection()`
* receives new messages from an application in a loop
* parses message types and acts accordingly


### Tracker node (`tracker.py`, using `protocol.py`):
There is a centralized tracker node that manages the network by keeping a list of all peers connected. Peers can make requests to join or leave the network, also to get the IPs of other peers connected at the moment.

`start()`
* starts a loop of accepting connections from peers to the tracker
* creates a new thread for `peer_handler()` for each peer accepted

`peer_handler()`
* receives data from a given peer
* parses the message type between JOIN_NETWORK, LEAVE_NETWORK, or LIST_PEERS
* calls the associated function below

`add_peer()`
* adds a new peer to the tracker's node list

`remove_peer()`
* removes a given peer from the tracker's node list

`list_peers()`
* gets a list of all peers in the network, not including the node that is requesting
* sends a list of the peers' ip addresses over the socket back to the requesting node


## Blockchain (implemented in `peer.py` and `block.py`)
We use a simple blockchain that is an array of Blocks. The Block class is outligned below under the Data Structures section. Peer nodes request the blockchain from other peers when joining, and do collective updates based on validation of new blocks added.

`request_blockchain()`
* gets the list of peers from tracker node 
* if there are no peers, then create and append the genesis block to the blockchain 
* otherwise sends a REQ_CHAIN message to all the peers using the send_data() function

`create_new_block()`
* creates a new instance of Block and sends the block to all peers in the network
* may call `attack_new_block()` if `attack` is true to create an invalid `prev_hash`
* waits to receive accept/reject responses from peers
* if all accept, append to blockchain, otherwise, we broadcast to all peers to reject the block

`attack_new_block()`
* creates a bad prev_hash for a block

`validate_new_block()`
* checks to see if the new block's prev_hash aligns with the local blockchain copy
* if it aligns, it will add the new block to the local blockchain
* sends block_status back to the peer who created it

`print_blockchain()`
* prints the local blockchain


#### Block functions:

`calculate_hash()`
* creates a hash for a block based on the id, data, nonce, and previous hash

`is_valid()`
* checks if a block is valid, meaning the hash aligns with the difficulty 

`mine()`
* loops and increments the nonce until the block is valid


## Application (`application.py`)
Our application is a distributed, decentralized voting application built on top of the blockchain. The application establishes a connection with a peer node using a TCP socket and communicates with the peer through the socket with encoded messages with encodings defined in `protocol.py`. Rather than using the peer's functions directly, generalized socket communication allows multiple instances of the application to connect and disconnect from the same instance of the peer.

Our application has a distributed UI that a user can interact with on the command line of their machine. When the program is initially run, it first asks the user to enter their name, then establishes a connection to a peer node on the same machine.

Once connected, the user will be welcomed with a screen and a description of the actions they will be able to perform: casting a vote (entering C), seeing the vote tallies (entering T), staging an attack with an invalid block (entering S), and quitting the application (entering Q)

`Vote` class
* The vote object has four parameters with essential metadata about the vote: `user_id`, `vote`, `timestamp`, and `name`

`signal_handler()`
* signal handler for CTRL-C (SIGINT) to close the peer socket and then exit

`connect_to_peer()`
* connects to the peer node running on the same machine over localhost and `app_port`

`ask_for_tally()`
* requests the local blockchain from the peer node and initiates the tallying process.
* It sends a message to the peer node requesting its local blockchain. Upon receiving the blockchain data, it calls `tally_votes()` to process and display the voting statistics. If the peer leaves the network, it handles the termination appropriately.

`tally_votes()` 
* computes and displays the current voting statistics based on the provided blockchain data.
* It takes a list of dictionaries representing blocks in the blockchain (raw_blockchain) as input and iterates through each block, extracting voting data and tallying the votes for each candidate.
* Finally, it prints out the current voting results, including the number of votes for each option and any leading candidates.

`cast_a_vote()`
* allows a user to cast a vote, ensuring that each user can vote only once
* It prompts the user to enter their vote and creates a Vote object containing the necessary information (user ID, vote, timestamp, and name). Then, it serializes the vote object into a JSON message and broadcasts it to all peers in the network. After receiving confirmation of the vote status, it updates the `has_voted` flag to prevent duplicate voting.
* If a user wants to simulate launching an attack on the blockchain and the distributed voting system, they can pass in `True` as the `staged_attack` parameter, which will mess up the `prev_hash` field of a vote that it will cast, which will then be rejected by other nodes in the blockchain.

## Application with GUI (`application-with-gui.py`)
This is a version of application with an easy-to-interact-with graphical user interface. Rather than interacting with the application directly on the command line, a GUI built using the `tkinter` library pops up, prompting the user for their name. On the subsequent screens, a button interface is used to be able to cast a vote, tally votes, attempt to launch an attack, and quit the application. The functionality of all of the above actions is the same are the same as in `application.py`. Note that the machine running `application-with-gui.py` must have a screen (or screen forwarding set up in the case of a VM)


# Protocols

All forms of communication between programs will send an array, where the first element is the message type and the following arguments are the data. Therefore, a given message sent or received between any of the 3 channels of communication, the first element in the message will contain the type.

Additionally, the newline character is used as a delimiter between messages in the peer->tracker protocol (`DELIMITER_STR = "\n"` and `DELIMITER_BYTE = b'\n'` in `protocol.py`)

## Peer - Tracker
Peer -> Tracker
* `JOIN_NETWORK`: Peer wants to join the network
* `LEAVE_NETWORK`: Peer wants to leave the network
* `LIST_PEERS`: Peer is requesting a list of other connected peers in the network

Peer -> Peer
* `REQ_CHAIN`: Peer is requesting the blockchain from another peer
* `RECV_CHAIN`: Peer is receiving the blockchain from another peer
* `NEW_BLOCK`: Peer is broadcasting a newly created block to other peers
* `BLOCK_STATUS`: Peer is sending back the result of validating a new block to the peer who created it
* `BLOCK_REJECT`: Peer is broadcasting for all other peers to reject a block

## Peer - App
Peer -> App
* `RETURNED_BLOCKCHAIN`: Peer is returning up the local blockchain to the app
* `TRANSACTION_STATUS`: Peer is returning the result of a new vote being cast and added to the blockchain
* `APP_LEAVE_NETWORK`: Peer is leaving the network, signaling for the app to exit

App -> Peer:
* `CAST_VOTE`: App is sending a new vote transaction to the peer running the blockchain
* `TALLY_VOTE`: App is requesting the peer's local blockchain copy to tally the votes stored

# Data Structures
## Block
Fields

* `id`: the id of the block, using UUIDv4
* `nonce`: the complimentary nonce of the block to align the hash with the difficulty
* `prev_hash`: the hash of the previous block in the blockchain
* `data`: the transaction data of the block
* `hash`: the hash of the block


## Vote
Fields

* `user_id`: the id of the user, using UUIDv4
* `vote`: who the user voted for
* `name`: the name of the user
* `timestamp`: the timestamp of the vote
