#ifndef GAMEAWESOME_LOCAL_AGENT_HPP
#define GAMEAWESOME_LOCAL_AGENT_HPP

#include "core/agent.hpp"
#include <memory>

class LocalAgent: public Agent {
public:
    void message(std::string_view message) const override;
    std::array<int, 2> get2DChoice(std::array<int, 2> dimensions) override;

    using InitializationPromise = void*;
    static InitializationPromise startInitialization() { return nullptr; }
    static std::unique_ptr<LocalAgent> awaitInitialization(InitializationPromise) { return std::make_unique<LocalAgent>(); }
};

#endif //GAMEAWESOME_LOCAL_AGENT_HPP
