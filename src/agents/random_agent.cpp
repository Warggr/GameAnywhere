#include "random_agent.hpp"

void RandomAgent::message(std::string_view message) const {
    (void) message;
}

std::array<int, 2> RandomAgent::get2DChoice(std::array<int, 2> dimensions) {
    (void) dimensions;
    return {0, 0};
}
