#ifndef GAMEAWESOME_PYAGENT_H
#define GAMEAWESOME_PYAGENT_H

#include "core/agent.hpp"
#include <boost/python.hpp>
#include <string>

class PythonAgent: public Agent {
    boost::python::object agent;

    std::string getStringFromPython(std::string_view methodName);
public:
    PythonAgent(const char* module_path, const char* module_name);
    ~PythonAgent();

    void message(std::string_view message) const override;
    std::array<int, 2> get2DChoice(std::array<int, 2> dimensions) override;

    struct Init {
        const char* module_path, * module_name;
    };

    using InitializationPromise = Init*;
    static InitializationPromise startInitialization() { return new Init { "./scripts", "example_agent" }; }
    static std::unique_ptr<PythonAgent> awaitInitialization(InitializationPromise init) {
        auto result = std::make_unique<PythonAgent>(init->module_path, init->module_name );
        delete init;
        return result;
    }
};

#endif //GAMEAWESOME_PYAGENT_H
