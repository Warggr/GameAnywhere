// Adapted from https://github.com/vinniefalco/CppCon2018
// Copyright (c) 2018 Vinnie Falco (vinnie dot falco at gmail dot com)
// Distributed under the Boost Software License, Version 1.0. (See copy at http://www.boost.org/LICENSE_1_0.txt)
#include "server_impl.hpp"
#include "http_session.hpp"
#include <thread>
#include <cassert>
#include <iostream>

#ifdef HAS_ROOM_ZERO_STAYS_OPEN
#include "setup/team.hpp"
constexpr bool roomZeroStaysOpen = true;
#endif

Server::Server(const char* ipAddress, unsigned short port)
    : listener( *this, ioc, tcp::endpoint{net::ip::make_address(ipAddress), port} )
{
    std::cout << "(main) Starting server\n";
}

Server::~Server(){
    for(const HttpSession* session : sessions){
        delete session;
    }
}

Server_impl::Server_impl(const char* ipAddress, unsigned short port
#ifdef HTTP_SERVE_FILES
        , std::string_view doc_root
#endif
)
        : Server(ipAddress, port)
#ifdef HTTP_SERVE_FILES
, doc_root(doc_root)
#endif
#ifdef HTTP_CONTROLLED_SERVER
, controlRoom(this)
#endif
{
#ifdef HTTP_CONTROLLED_SERVER
    repo.mkDefaultTeams();
    controlRoom.setGreeterMessage("MSG: Welcome to the Control Room!");
#endif
}

void Server_impl::start(){
    std::cout << "(network) Starting server...\n";
    listener.listen();

#ifdef HAS_ROOM_ZERO_STAYS_OPEN
    if(roomZeroStaysOpen) addRoom(0).second.launchGame({ mkEurope(), mkNearEast() }, 0);
#endif
    // Capture SIGINT and SIGTERM to perform a clean shutdown
    net::signal_set signals(ioc, SIGINT, SIGTERM);
    signals.async_wait([&](boost::system::error_code const&, int signal){
        std::cout << "Received signal " << signal << ". Stopping...\n";
        // Stop the io_context. This will cause run()
        // to return immediately, eventually destroying the
        // io_context and any remaining handlers in it.
        stop();
    });

    //! this function runs indefinitely.
    //! To stop it, you need to call stop() (presumably from another thread)
    ioc.run();
}

void Server_impl::stop(){
    std::cout << "(network) ...stopping server and interrupting rooms\n";
    for(auto& [id, room] : rooms){
        room.interrupt();
    }
#ifdef HTTP_CONTROLLED_SERVER
    controlRoom.interrupt();
#endif
    ioc.stop(); //Stop io_context. Now the only things that can block are in the game threads.
    rooms.clear(); //Closing all rooms (some might wait for their game to end)
}

std::pair<RoomId, GameRoom_impl&> Server_impl::addRoom(RoomId newRoomId) {
    std::cout << "(main) Add room to server\n";
    auto [iter, success] = rooms.insert({newRoomId, GameRoom_impl(this, newRoomId)});
    assert(success and iter->first == newRoomId);
    return { newRoomId, iter->second };
}

void Server_impl::askForRoomDeletion(RoomId id) {
    std::cout << "(main server) room deletion requested\n";

    async_do([&,id=id] {
        GameRoom_impl& room = rooms.find(id)->second;
        room.interrupt();
    });
    async_do([&,id=id]{
        std::cout << "(async server) room deletion in progress...\n";
        rooms.erase(id);
        std::cout << "(async server) ...room deleted!\n";
#ifdef HAS_ROOM_ZERO_STAYS_OPEN
        if(roomZeroStaysOpen and id == 0)
            addRoom(0).second.launchGame({ mkEurope(), mkNearEast() }, 0);
#endif
    });
}

void Server::addSession(tcp::socket&& socket){
    auto session = new HttpSession(std::move(socket), static_cast<Server_impl&>(*this));
    sessions.insert(session);
    session->run();
}

void Server::askForHttpSessionDeletion(HttpSession* session){
    sessions.erase(session);
    delete session;
}
