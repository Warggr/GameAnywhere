#include "random_agent.hpp"

void RandomAgent::message(std::string_view message) const {
    (void) message;
}

std::pair<int, int> RandomAgent::get2DChoice(std::pair<int, int> dimensions) {
    (void) dimensions;
    return {0, 0};
}
