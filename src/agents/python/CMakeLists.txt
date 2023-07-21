find_package(Python3 REQUIRED COMPONENTS Interpreter Development)
find_package(Boost REQUIRED COMPONENTS python)

add_library(python.agent STATIC pyagent.cpp)
target_include_directories(python.agent PUBLIC ${Python3_INCLUDE_DIRS})
target_link_libraries(python.agent PRIVATE ${Python3_LIBRARIES} ${Boost_LIBRARIES})
