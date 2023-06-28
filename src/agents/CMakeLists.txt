add_library(random.agent random_agent.cpp)

add_library(agents agents.cpp)
target_link_libraries(agents random.agent)
