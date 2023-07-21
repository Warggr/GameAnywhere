#include "pyagent.h"
#include <boost/python.hpp>
#include <cassert>
#include <iostream>

namespace py = boost::python;

void handle_python_exception() {
    PyErr_Print();
}

#define CATCH_PYTHON_EXCEPTION catch(py::error_already_set& err) { handle_python_exception(); throw Agent::Surrendered(); }

PythonAgent::PythonAgent(const char* module_path, const char* module_name) {
    try {
        Py_Initialize();
        py::list sysPath = py::extract<py::list>(py::object(py::handle<>(PySys_GetObject("path"))));
        sysPath.append( py::str(module_path));
        std::cout << (std::string)py::extract<std::string>( py::str( sysPath )) << '\n';

        auto module = py::import(module_name);
        auto agentClass = module.attr("Agent");
        agent = agentClass();
    } CATCH_PYTHON_EXCEPTION;
}

PythonAgent::~PythonAgent() {
    // Do not call Py_Finalize when using Boost.Python
}

std::string PythonAgent::getStringFromPython(std::string_view methodName) {
    try {
        auto method = agent[methodName];
        auto value = method();
        return py::extract<std::string>(value);
    } CATCH_PYTHON_EXCEPTION;
}

void PythonAgent::message(std::string_view message) const {
    try {
        agent.attr("on_message")(py::str(std::string(message)));
    } CATCH_PYTHON_EXCEPTION;
}

std::array<int, 2> PythonAgent::get2DChoice(std::array<int, 2> dimensions) {
    try {
        py::object result = agent.attr("get_2D_choice")(py::make_tuple(dimensions[0], dimensions[1]));
        if (py::len(result) != 2) {
            std::cerr << "Invalid return value from Python's get_2d_choice\n";
            throw Agent::Surrendered();
        }
        return std::array<int, 2>{py::extract<int>(result[0]), py::extract<int>(result[1])};
    } CATCH_PYTHON_EXCEPTION;
}
