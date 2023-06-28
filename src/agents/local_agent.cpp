#include "local_agent.hpp"
#include <iostream>
#include <typeinfo>

void LocalAgent::message(std::string_view message) const {
    std::cout << message << '\n';
}

template<typename T>
T getValue() {
    std::cout << "Please choose a value of type " << typeid(T).name() << ":";
    T result;
    std::cin >> result;
    return result;
}

std::array<int, 2> LocalAgent::get2DChoice(std::array<int, 2> dimensions) {
    std::array<int, 2> result;
    for(unsigned int i = 0; i<2; i++){
getValue:
        result[i] = getValue<int>();
        if(result[i] < 0 or result[i] >= dimensions[i]) goto getValue;
    }
    return result;
}
