#ifndef GAMEAWESOME_RUN_GAME_HPP
#define GAMEAWESOME_RUN_GAME_HPP

#include "core/game.hpp"
#include "core/agent_descriptor.hpp"

template<typename GameType>
std::unique_ptr<GameSummary> run_game(int argc, const char** argv) {
    auto agentDescriptions = parseAgentDescription(argc, argv);

    //TODO does agentDescription have an acceptable size?

    std::vector<AbstractAgentDescriptor::Promise> initializations;
    for(const auto& descr: agentDescriptions)
        initializations.push_back(descr->startInitialization());

    std::vector<std::unique_ptr<Agent>> agents;
    for(unsigned int i = 0; i<agentDescriptions.size(); i++)
        agents.push_back(agentDescriptions[i]->awaitInitialization(initializations[i]));

    GameType game(std::move(agents));
    return game.playGame();
}

#endif //GAMEAWESOME_RUN_GAME_HPP
