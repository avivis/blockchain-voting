# Overview
BlockchainVoting is a distributed voting application that relies on blockchain.

There is an underlying peer-to-peer network that lets peer nodes connect to each other with the help of a tracker node. Each application will connect to a peer node on the same machine and run the BlockchainVoting program. Users can cast new votes which will reflect on all applications running, tally votes to see who is in the lead, and stage an attack by creating an invalid new block.


## How to run

Example commands are given below each step:
1. On one VM, run `tracker.py`: `python3 tracker.py <tracker_port>`

        python3 tracker.py 50000
    It will print out the the IP address that each peer should connect to.

2. On another VM, run `peer.py`: `python3 peer.py <tracker_ip> <tracker_port> <peer_port> <app_port>`

        python3 peer.py 35.223.113.107 50000 60000 61000

    Run multiple peers by running each one on its own VM.
3. On each VM running a peer, run `application.py` in a new window: `python3 application.py <app_port>`

        python3 application.py 61000

NOTE: The tracker, peer, and application will run infinitely. Do CTRL-C to terminate the each program when you would like it to end. A peer can handle multiple sequential applications and the tracker handles peers coming and going, but if the tracker is killed, the peers and their connected applications will fail when trying to interact with other peers.

The applications and peers do not have to join the network at the same time to have the shared blockchain ledger. Repeat steps 2 and 3 on another VM to add more peers and applications.


### Application with a GUI

Demo of Application with GUI: https://youtu.be/Bt9ogbe7MBw
  
To run the application with a GUI, it requires Python3, installation of `tkinter` on every VM running it, and X11 forwarding set up. *Note that there will be slight lag due to the forwarding.*

Install `tkinter` with Python3 on a VM:

- `sudo apt install python3-tk`

Follow [this guide](https://static.us.edusercontent.com/files/xva4E15tnSNksMG9acQhWP65) to set up X11 forwarding

SSH into the your VM with this command:

- `ssh -X -o 'Compression no' -i ~/.ssh/<private-key-file> <username>@<IP>`

Then, run:

- `python3 application-with-gui.py <app_port>`, with `application-with-gui.py` instead of `application.py` in the step 3 above.

## Description of Files

`tracker.py`
* tracker program that serves as a centralized tracker for nodes in the P2P network

`peer.py`
* peer program that connects to the tracker and serves as a node in the P2P network
* implements and stores the local blockchain with associated functions to create and validate blocks
* communicates with the tracker, other peers, and applications over TCP sockets

`block.py`
* Block class implementation and associated functions

`protocol.py`
* outlines the various types of messages used in the protocols between the programs
* specifies delimiters and looping `recv()` wrapper to receive lengthy data over sockets
* contains `get_external_ip()` function used by peers and the tracker

`application.py`
* Vote class implementation
* BlockchainVoting application where users can cast votes, check live voting results, and stage attacks

`application-with-gui.py`
* Vote class implementation
* BlockchainVoting application **with a GUI** where users can cast votes, check live voting results, and stage attacks 


## Assumptions

We chose to a client-server connection model for peers to communicate. Each peer will act as a server by listening on the `peer_port` and accept connections in a loop, where each connection is one message from another peer. If another peer wants to send a message, it will connect as a client, send the message, and then close the socket. Therefore, each peer is both a client and a server over the `peer_port`.
Although there is significant overhead and poor scalability if each peer has to connect, send data, and close a TCP connection to send a message to another peer, this implementation was most simple to do for the scope of this project and network size. In reality, peers would not send data to every other peer in the network, but instead send to a few and let it propagate.

We assumed that a peer will not disconnect from the network and rejoin again quickly, or else it will have issues with binding to the same port.

We assumed that only one application will connect to a peer at a time. Multiple applications can connect to a peer, but it has to be sequentially, not concurrently.

When tallying the votes in the application, we only use the node's local blockchain to get the data, since all blockchains will be the same.
