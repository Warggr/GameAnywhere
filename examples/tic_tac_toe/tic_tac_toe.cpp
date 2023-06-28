#include "tic_tac_toe.hpp"
#include "run_game.hpp"
#include "core/agent.hpp"

int main(int argc, const char** argv) {
    run_game<TicTacToe>(argc, argv);
}

inline bool hasRow(unsigned int player, const TicTacToeState::BoardType& board, std::pair<unsigned int, unsigned int> start, std::pair<unsigned int, unsigned int> step) {
    for(unsigned int i = 0; i < TicTacToeState::BOARD_DIMENSION; i++){
        if(board[start].empty or board[start].player != player) return false;
        start.first += step.first;
        start.second += step.second;
    }
    return true;
}

std::optional<SimpleGameSummary> TicTacToe::turn_impl() {
    constexpr unsigned int TOTAL_MOVES = decltype(state.board)::getSize();
    constexpr auto BOARD_DIMENSIONS = decltype(state.board)::getDimensions();

    if(getCurrentTurn() == TOTAL_MOVES) return { GameSummary::NO_WINNER };

    auto position = getCurrentAgent().get2DChoice(BOARD_DIMENSIONS);
    state.board[position].empty = false;
    state.board[position].player = getCurrentAgentIndex();

    //check rows
    for(unsigned int row = 0; row<TicTacToeState::BOARD_DIMENSION; row++){
        if(hasRow(getCurrentAgentIndex(), state.board, std::make_pair(row, 0), std::make_pair(0, 1)))
            return { getCurrentAgentId() };
    }
    //check columns
    for(unsigned int col = 0; col<TicTacToeState::BOARD_DIMENSION; col++){
        if(hasRow(getCurrentAgentIndex(), state.board, std::make_pair(0, col), std::make_pair(1, 0)))
            return { getCurrentAgentId() };
    }
    //check diagonals
    if(hasRow(getCurrentAgentIndex(), state.board, std::make_pair(0, 0), std::make_pair(1, 1)))
        return { getCurrentAgentId() };
    if(hasRow(getCurrentAgentIndex(), state.board, std::make_pair(0, TicTacToeState::BOARD_DIMENSION-1), std::make_pair(1, -1)))
        return { getCurrentAgentId() };

    return std::nullopt;
}
