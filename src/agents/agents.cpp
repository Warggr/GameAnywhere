#include "core/agent_descriptor.hpp"
#include "random_agent.hpp"
#include "local_agent.hpp"

std::vector<std::unique_ptr<AbstractAgentDescriptor>> parseAgentDescription(int argc, const char** argv){
    (void) argc; (void) argv; // TODO
    std::vector<std::unique_ptr<AbstractAgentDescriptor>> result;
    result.push_back( std::make_unique<AgentDescriptor<LocalAgent>>() );
    result.push_back( std::make_unique<AgentDescriptor<LocalAgent>>() );
    return result;
}
