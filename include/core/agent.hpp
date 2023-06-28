#ifndef GAMEAWESOME_AGENT_HPP
#define GAMEAWESOME_AGENT_HPP

#include <string_view>
#include <utility>

class Agent {
public:
    virtual ~Agent() = default;
    virtual void message(std::string_view message) const = 0;
    virtual std::pair<int, int> get2DChoice(std::pair<int, int> dimensions) = 0;
};

#endif //GAMEAWESOME_AGENT_HPP
