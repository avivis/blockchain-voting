
# Testcases

## Testcase 1
#### Description

2 peers in the network, each connects 2 applications consecutively, so 4 applications will run over the course of the test.

Peer 1 will connect and its first application will cast a vote before Peer 2 joins. When Peer 2 has joined, its first application will already reflect the vote from Peer 1's first application.

On Peer 1, the second application will try to stage an attack before voting. The final state will reflect 4 votes in total from each of the 4 applications connected.

#### Video Link: https://youtu.be/tIhYgGJfddk

## Testcase 2
#### Description

3 peers in the network, Peer 2 and Peer 3 connect 1 application, Peer 1 connects 2 applications.

Peer 1, 2, and 3 will all join, 1 application will connect to each, cast a vote, and tally votes to see updates. Peer 3 will join at the same time as Peer 2, and it will collect updates before its application joins.

Peer 1 will disconnect from the network before rejoining and connecting its second application.

Peer 2's application will stage an attack on the blockchain after this, which will be rejected by Peer 1 and Peer 3.

The 4 votes will be reflected by all applications and peers in the final state.

#### Video Link: https://youtu.be/92rfwhWuGbA

## Testcase 3
#### Description

3 peers in the network, Peers 1 and 2 connect 2 applications, Peer 3 connects 1 application later on. Peer 1 will have a 3rd application connect at the end.

Peers 1 and 2 will join, then 2 applications will connect to Peer 1 sequentially, each casting a vote. Then, an application will connect to Peer 2, stage an attack, cast a vote, then exit. The second application will connect to Peer 2 and cast a vote.

Peer 1's application will exit. Then, Peer 3 will join finally and have an application connect, stage an attack, then vote and exit.

Peer 2 will exit the network, and then a new application will connect to Peer 1 and show that the state reflects all 5 previous votes.

#### Video Link: https://youtu.be/GVORmrsH6nw

## GUI Demo
#### Video Link: https://youtu.be/Bt9ogbe7MBw
