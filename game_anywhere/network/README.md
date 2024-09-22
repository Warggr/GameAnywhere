# Websocket server

## Exceptions

A server room can stop for 3 possible reasons:
- the game ends
- an agent disconnects
- the server is killed

The shutdown flow handles all these cases and goes like this:
```
(network-thread)
,--- The server dies -> interrupts all rooms and asks them to disconnect the agents
* The server closes the I/O context. No asynchronous operations are possible anymore.
|,--- an agent disconnects
* Agent disconnected
|
|  (game thread)
|  * The next time the game tries to ask that agent, it raises an exception and ends the game.
|  |,--- The game ends naturally
|  * The game ends
|  * The game asks the server to close the room (asynchronously). Then the game thread ends.
|
* If the I/O context is closed, the request is ignored.
|    If not, the server interrupts the room and asks him to disconnect all agents. (They were possibly already disconnected)
|
| / The game thread is joined, the room is closed and removed from the room list.
\`--
```
