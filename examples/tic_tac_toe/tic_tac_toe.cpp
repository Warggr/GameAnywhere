#include "tic_tac_toe.hpp"
#include "run_game.hpp"
#include "core/agent.hpp"
#include <string>

int main(int argc, const char** argv) {
    run_game<TicTacToe>(argc, argv);
}

inline bool hasRow(unsigned int player, const TicTacToeState::BoardType& board, std::array<std::size_t, 2> start, std::array<short int, 2> step) {
    for(unsigned int i = 0; i < TicTacToeState::BOARD_DIMENSION; i++){
        if(board[start].empty or board[start].player != player) return false;
        for(unsigned int j = 0; j<start.size(); j++)
            start[j] += step[j];
    }
    return true;
}

std::optional<SimpleGameSummary> TicTacToe::turn_impl() {
    constexpr unsigned int TOTAL_MOVES = decltype(state.board)::getSize();
    constexpr auto BOARD_DIMENSIONS_UNSIGNED = decltype(state.board)::getDimensions();
    constexpr std::array<int, 2> BOARD_DIMENSIONS = { BOARD_DIMENSIONS_UNSIGNED[0], BOARD_DIMENSIONS_UNSIGNED[1] };

    if(getCurrentTurn() == TOTAL_MOVES) return { GameSummary::NO_WINNER };

    TicTacToeState::Field* field;
    do {
        auto position = getCurrentAgent().get2DChoice(BOARD_DIMENSIONS);
        field = &state.board[position[0]][position[1]];
    } while(not field->empty);
    field->empty = false;
    field->player = getCurrentAgentIndex();

    std::string message = "-------\n";
    for(const auto& row: state.board.board){
        for(const auto& cell: row){
            message.append(1, '|').append(1, cell.toString());
        }
        message.append("|\n-------\n");
    }
    for(const auto& agent: agents){
        agent->message(message);
    }

    //check rows
    for(unsigned int row = 0; row<TicTacToeState::BOARD_DIMENSION; row++){
        if(hasRow(getCurrentAgentIndex(), state.board, {row, 0}, {0, 1}))
            return { getCurrentAgentId() };
    }
    //check columns
    for(unsigned int col = 0; col<TicTacToeState::BOARD_DIMENSION; col++){
        if(hasRow(getCurrentAgentIndex(), state.board, {0, col}, {1, 0}))
            return { getCurrentAgentId() };
    }
    //check diagonals
    if(hasRow(getCurrentAgentIndex(), state.board, {0, 0}, {1, 1}))
        return { getCurrentAgentId() };
    if(hasRow(getCurrentAgentIndex(), state.board, {0, TicTacToeState::BOARD_DIMENSION-1}, {1, -1}))
        return { getCurrentAgentId() };

    return std::nullopt;
}
