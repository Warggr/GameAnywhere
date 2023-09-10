find_package( Boost REQUIRED )

add_subdirectory(base)

add_library(server server.cpp room.cpp spectator.cpp)
target_link_libraries(server base.network)
