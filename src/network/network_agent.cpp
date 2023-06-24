#include "network_agent.hpp"
#include "spectator.hpp"
#include "room.hpp"
#include <algorithm>

NetworkAgent::NetworkAgent(uint myId, std::shared_ptr<Session> session)
: StepByStepAgent(myId), sender(std::move(session))
{
}

std::unique_ptr<NetworkAgent> NetworkAgent::declareUninitializedAgent(ServerRoom& room, unsigned short agentId){
    auto session = room.addSession(agentId+1);
    return std::make_unique<NetworkAgent>(agentId, session);
}

void NetworkAgent::sync_init(){
    sender->awaitReconnect();
}

// Adapted from https://en.cppreference.com/w/cpp/string/basic_string/replace
void replace_all(std::string& inout, char what, std::string_view with){
    std::string::size_type pos = 0;
    while(true){
        pos = inout.find(what, pos);
        if(pos == inout.npos) break;
        inout.replace(pos, 1, with);
        pos += with.length();
    }
}

uint NetworkAgent::choose(const OptionList& options, const std::string_view& message) {
    std::string optionList = std::string("[");
    for(const auto& [ keys, optionText ] : options){
        optionList += '"';
        optionList += optionText;
        optionList += "\",";
    }
    optionList += '"';
    optionList += message;
    optionList += "\"]";
    auto message_shared = std::make_shared<const std::string>(std::move(optionList));
show_options:
    sender->send_sync(message_shared);

#define SHARE(str) std::make_shared<std::string>(str)

    input_loop:
        std::string str;
        try {
            str = sender->get_sync();
        } catch(DisconnectedException&){
            throw AgentSurrenderedException(myId);
        }
        if(str == "?") goto show_options;
        if(str == StepByStepAgent::SURRENDER) throw AgentSurrenderedException(myId);
        auto [ value, success ] = StepByStepAgent::inputValidation( options, str );
        if(not success){
            replace_all(str, '\\', "\\\\");
            replace_all(str, '"', "\\\""); //Escape the string to make it valid json
            sender->send_sync(SHARE(std::string("\"!Wrong value: `") + str + "`\""));
            goto input_loop;
        }
    sender->send_sync(SHARE("\"Ok\""));
    return value;
}
