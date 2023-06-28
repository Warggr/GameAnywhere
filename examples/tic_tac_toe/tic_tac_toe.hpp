#ifndef GAMEAWESOME_TIC_TAC_TOE_HPP
#define GAMEAWESOME_TIC_TAC_TOE_HPP

#include "core/turn_based_game.hpp"
#include "components/board.hpp"
#include <array>

struct TicTacToeState {
    struct Field {
        bool empty = true;
        unsigned int player: 1;
        constexpr Field(): player(0) {};
        [[nodiscard]] char toString() const { return empty ? ' ' : player==0 ? 'O' : 'X'; }
    };
    static constexpr unsigned int BOARD_DIMENSION = 3;
    using BoardType = CheckerBoard<Field, BOARD_DIMENSION, BOARD_DIMENSION>;

    BoardType board;
};

class TicTacToe: public TurnBasedGame {
public:
    using SummaryType = SimpleGameSummary;
private:
    TicTacToeState state;
public:
    explicit TicTacToe(std::vector<std::unique_ptr<Agent>>&& agents): TurnBasedGame(std::move(agents)) {};

    std::optional<SimpleGameSummary> turn_impl();
    std::optional<std::unique_ptr<GameSummary>> turn() override {
        auto turn = turn_impl();
        return turn ? std::make_optional( std::make_unique<SimpleGameSummary>(*turn) ) : std::nullopt;
    }
};

#endif //GAMEAWESOME_TIC_TAC_TOE_HPP
