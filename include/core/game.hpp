#ifndef GAMEAWESOME_GAME_HPP
#define GAMEAWESOME_GAME_HPP

#include <vector>
#include <memory>

using AgentId = unsigned int;

struct GameSummary {
    static constexpr AgentId NO_WINNER = 0;

    virtual ~GameSummary() = default;
    virtual AgentId getWinner() = 0;
};

struct SimpleGameSummary: public GameSummary {
    AgentId winner;
    AgentId getWinner() override { return winner; }

    constexpr SimpleGameSummary(AgentId winner): winner(winner) {}
};

class Agent;

// Represents a game in progress. Most often has a gameState pointer
class Game {
protected:
    std::vector<std::unique_ptr<Agent>> agents;
public:
    Game(std::vector<std::unique_ptr<Agent>>&& agents): agents(std::move(agents)) {}
    virtual ~Game() = default;
    virtual std::unique_ptr<GameSummary> playGame() = 0;
};

#endif //GAMEAWESOME_GAME_HPP
