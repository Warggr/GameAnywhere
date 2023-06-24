list(APPEND files
	http_session.cpp
	room.cpp
	server.cpp
)

add_library(base.network STATIC listener.cpp spectator.cpp)

add_library(network.agent STATIC network_agent.cpp)
target_link_libraries(network.agent PUBLIC base.agent base.network)

add_library(network STATIC ${files})
target_link_libraries(network PRIVATE base.network)

add_library(server.network STATIC ${files} launch_game.cpp)
target_compile_definitions(server.network PUBLIC HTTP_CONTROLLED_SERVER HTTP_SERVE_FILES)
target_link_libraries(server.network PRIVATE
		base.network
		setup
		control
		network.agent search.agent base.agent
		base.logging network.logging
		pthread
)

find_package( Boost REQUIRED )
