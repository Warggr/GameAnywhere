#ifndef REVELATION_NETWORK_AGENT_HPP
#define REVELATION_NETWORK_AGENT_HPP

#include "control/step_agent.hpp"
#include "spectator.hpp"
#include <vector>
#include <string>

class ServerRoom;

class NetworkAgent : public StepByStepAgent {
    std::shared_ptr<Session> sender;
protected:
    uint choose(const OptionList& list, const std::string_view& message) override;
public:
    NetworkAgent(uint myId, std::shared_ptr<Session> session);
    static std::unique_ptr<NetworkAgent> declareUninitializedAgent(ServerRoom& room, unsigned short int agentId);
    void sync_init() override;
};

#endif //REVELATION_NETWORK_AGENT_HPP
