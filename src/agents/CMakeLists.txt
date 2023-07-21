add_library(random.agent random_agent.cpp)
add_library(local.agent local_agent.cpp)

add_subdirectory(python)

add_library(agents agents.cpp)
target_link_libraries(agents random.agent local.agent python.agent)
