import socket
import threading
import json
import argparse
from protocol import *


#USAGE: python3 tracker.py <tracker_port>

class Tracker:
    def __init__(self, port):
        self.peers = []
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(('0.0.0.0', port))
        self.server_socket.listen(5)
        self.my_ip = get_external_ip()
        print(f"tracker is listening on port {port}, peers should join to ip address: {self.my_ip}")


    def start(self):
        """
        start accepting incoming peers
        """
        while True:
            peer_sock, addr = self.server_socket.accept()
            peer_handler = threading.Thread(target=self.peer_handler, args=(peer_sock,))
            peer_handler.start()


    def peer_handler(self, peer_sock):
        """
        handle connections from peers
        """
        while True:
            raw_data = peer_sock.recv(1024).decode('utf-8')
            if not raw_data:
                break

            packets = raw_data.split(DELIMITER_STR)
            packets = packets[:-1]
            for packet in packets:
                data = json.loads(packet)
                if data[0] == 'JOIN_NETWORK':
                    peer_ip = data[1]
                    self.add_peer(peer_ip)
                elif data[0] == 'LEAVE_NETWORK':
                    peer_ip = data[1]
                    self.remove_peer(peer_ip)
                elif data[0] == 'LIST_PEERS':
                    peer_ip = data[1]
                    self.list_peers(peer_sock, peer_ip)
                else:
                    print("invalid message from a peer")

        peer_sock.close()


    def add_peer(self, peer_ip):
        """
        add a new peer to the tracker's list
        """
        if peer_ip not in self.peers:
            self.peers.append(peer_ip)
            print(f"peer {peer_ip} joined")


    def remove_peer(self, peer_ip):
        """
        remove a peer from the tracker's list when it's leaving
        """
        if peer_ip in self.peers:
            self.peers.remove(peer_ip)
            print(f"peer {peer_ip} left")


    def list_peers(self, peer_sock, requester_ip):
        """
        send a list of all peers in the network back over the socket to the peer in an array
        do not include the ip of the requester peer in what is sent
        """
        peer_ips = [ip for ip in self.peers if ip != requester_ip]
        peers = json.dumps(peer_ips).encode('utf-8')
        peer_sock.sendall(peers)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='tracker script')
    parser.add_argument('tracker_port', type=int, help='tracker port')

    args = parser.parse_args()

    tracker_port = args.tracker_port

    tracker = Tracker(tracker_port)
    tracker.start()