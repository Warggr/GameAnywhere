#ifndef GAMEAWESOME_AGENT_DESCRIPTOR_HPP
#define GAMEAWESOME_AGENT_DESCRIPTOR_HPP

#include <memory>
#include <vector>

class Agent;

struct AbstractAgentDescriptor {
    using Promise = void*;

    virtual ~AbstractAgentDescriptor() = default;
    virtual Promise startInitialization() const = 0;
    virtual std::unique_ptr<Agent> awaitInitialization(Promise initialization) const = 0;
};

template<typename T>
struct AgentDescriptor: public AbstractAgentDescriptor {
    Promise startInitialization() const override {
        return reinterpret_cast<void*>(T::startInitialization());
    }
    std::unique_ptr<Agent> awaitInitialization(Promise initialization) const override {
        auto promise = reinterpret_cast<typename T::InitializationPromise>(initialization);
        return T::awaitInitialization(promise);
    }
};

std::vector<std::unique_ptr<AbstractAgentDescriptor>> parseAgentDescription(int argc, const char** argv);

#endif //GAMEAWESOME_AGENT_DESCRIPTOR_HPP
