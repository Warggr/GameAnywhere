#ifndef GAMEAWESOME_RANDOM_AGENT_HPP
#define GAMEAWESOME_RANDOM_AGENT_HPP

#include "core/agent.hpp"
#include "core/agent_descriptor.hpp"
#include <random>

class RandomAgent: public Agent {
    // TODO: seed
public:
    void message(std::string_view message) const override;
    std::array<int, 2> get2DChoice(std::array<int, 2> dimensions) override;

    using InitializationPromise = void*;
    static InitializationPromise startInitialization() { return nullptr; }
    static std::unique_ptr<RandomAgent> awaitInitialization(InitializationPromise) { return std::make_unique<RandomAgent>(); }
};

#endif //GAMEAWESOME_RANDOM_AGENT_HPP
