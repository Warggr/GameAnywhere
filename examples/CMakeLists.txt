add_subdirectory(tic_tac_toe)
target_link_libraries(tic_tac_toe agents)

add_executable(run_server run_server.cpp)
target_link_libraries(run_server server)
