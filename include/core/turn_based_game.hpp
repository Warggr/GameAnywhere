#ifndef GAMEAWESOME_TURN_BASED_GAME_HPP
#define GAMEAWESOME_TURN_BASED_GAME_HPP

#include "game.hpp"
#include <optional>

class TurnBasedGame: public Game {
    unsigned int totalTurn = 0;
protected:
    [[nodiscard]] unsigned int getCurrentAgentIndex() const { return totalTurn % agents.size(); }
    [[nodiscard]] AgentId getCurrentAgentId() const { return getCurrentAgentIndex() + 1; }
    [[nodiscard]] Agent& getCurrentAgent() const { return *agents[getCurrentAgentIndex()]; }
    [[nodiscard]] unsigned int getCurrentTurn() const { return totalTurn; }

    virtual std::optional<std::unique_ptr<GameSummary>> turn() = 0;
public:
    TurnBasedGame(std::vector<std::unique_ptr<Agent>>&& agents): Game(std::move(agents)) {}
    std::unique_ptr<GameSummary> playGame() override {
        for(totalTurn = 0; true; totalTurn++) {
            auto winner = turn();
            if(winner) return std::move(winner.value());
        }
    }
};

#endif //GAMEAWESOME_TURN_BASED_GAME_HPP
