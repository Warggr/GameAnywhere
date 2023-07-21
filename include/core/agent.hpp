#ifndef GAMEAWESOME_AGENT_HPP
#define GAMEAWESOME_AGENT_HPP

#include <string_view>
#include <array>
#include <exception>

class Agent {
public:
    virtual ~Agent() = default;

    virtual void message(std::string_view message) const = 0;
    virtual std::array<int, 2> get2DChoice(std::array<int, 2> dimensions) = 0;

    class Surrendered: public std::exception {};
};

#endif //GAMEAWESOME_AGENT_HPP
