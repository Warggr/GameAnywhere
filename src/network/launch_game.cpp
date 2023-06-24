#include "room.hpp"
#include "network_agent.hpp"
#include "server_impl.hpp"
#include "logging/file_logger.hpp"
#include "logging/network_logger.hpp"
#include "control/game.hpp"
#include "control/agent.hpp"
#include "control/timeout.hpp"
#include "search/search.hpp"
#include "setup/agent_setup.hpp"
#include <array>
#include <memory>
#include <fstream>
#include <iostream>
#include <cassert>

Agents agentsFromDescription(AgentDescription&& descr, ServerRoom& room){
    Agents retVal;
    for(uint i = 0; i<NB_AGENTS; i++){
        switch(descr[i].type){
            case AgentDescriptor::BOT: retVal[i] = std::unique_ptr<SearchAgent>(reinterpret_cast<SearchAgent*>(descr[i].data)); break;
            case AgentDescriptor::LOCAL: retVal[i] = std::make_unique<HumanAgent>(i); break;
            case AgentDescriptor::RANDOM: retVal[i] = std::make_unique<RandomAgent>(i); break;
            case AgentDescriptor::NETWORK: retVal[i] = NetworkAgent::declareUninitializedAgent(room, i); break;
            case AgentDescriptor::TIMEOUT_PROXY: retVal[i] = std::unique_ptr<AgentTimeoutProxy>(reinterpret_cast<AgentTimeoutProxy*>(descr[i].data)); break;
            default: assert(false);
        }
    }
    return retVal;
}

void GameRoom_impl::launchGame(RoomId id, GameDescription&& gameDescr){
    std::cout << "(network thread) Launching game\n";
    Agents agents = agentsFromDescription(std::move(gameDescr.agents), *this);
    myThread = std::thread([this,id,gameDescr] (Agents agents) {
        std::cout << "(game thread) Launching game thread, waiting for agents...\n";
        GameSummary results;
        try {
            for (auto &agent: agents)
                agent->sync_init();
            std::array<const Team*, NB_AGENTS> teams = { nullptr };
            for(unsigned i = 0; i<NB_AGENTS; i++){
                const auto& teamsMap = server->repo.getTeams();
                if(gameDescr.teams[i]){
                    auto found = teamsMap.find(gameDescr.teams[i].value());
                    if(found != teamsMap.end()){ teams[i] = &found->second; continue; }
                    else{ std::cerr << "!Team not found: " << gameDescr.teams[i].value() << '\n'; }
                }
                teams[i] = &agents[i]->getTeam(server->repo);
            }
            GeneratorSeed seed = gameDescr.seed ? gameDescr.seed.value() : getRandom();
            //! The file needs to be created before the Game and the Logger, so that it stays open longer!
            std::ofstream logFile(path_cat(server->doc_root, std::string("/log_room_") + std::to_string(id) + ".json") );
            std::array<Agent*, NB_AGENTS> agentRefs = { agents[0].get(), agents[1].get() };
            Game game(teams, agentRefs, seed);
            game.logger.addSubLogger<FileLogger>(logFile)
                    .addSubLogger<LiveServerAndLogger>(*this);
            std::cout << "(game thread) ...agents found, game in progress...\n";
            results = game.play();
            std::cout << "(game thread) ...game finished, ask server for deletion\n";
        }
        catch (TimeoutException &) {}
        catch (DisconnectedException &) {}
        server->controlRoom.send(std::string("FINISH: ") + std::to_string(id) + " {\"winner\":" + std::to_string(results.whoWon) + " }");
        server->askForRoomDeletion(id);
    },
    std::move(agents));
}
