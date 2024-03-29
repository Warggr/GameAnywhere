# Project structure

This repository is intended as a library: it does not have a single executable, but instead it exports a set of functions and classes that other applications can use.

This repository comprises the following files and folders:
- `include`: public interface of the library. Python applications are supposed to `import` only from `game_anywhere.include`.
    - `core`: the core definitions of the library, e.g. `Agent` and `Game`
    - `components`: reusable components that can be used in different games, e.g. checkerboards or decks of cards
- `src`: private implementation of the library. Applications should not care about this part.
    - `network`: classes for a web server and client sessions. Used in `src/agents/network_agent.py`
    - `agent`: different agent implementations
- `client`: Files for the web client. The web client connects to the server implemented in `src/network` and remotely controls a `NetworkAgent`.
- `examples`: some example applications that are built on top of this library.
    - e.g. `examples/chess` and `examples/tic_tac_toe` for some example games. Running `examples/chess/chess.py` runs a single chess game.
    - `examples/run_server.py` runs a web server on which different games can be launched

## Intro
In my opinion, the best way to get familiar with the code is to go through the following files:
- `include/core/game.py`
- `include/core/agent.py`
- `examples/tic_tac_toe/tic_tac_toe.py` (start from `class TicTacToe`)
