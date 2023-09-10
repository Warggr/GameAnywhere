// Adapted from https://github.com/vinniefalco/CppCon2018
// Copyright (c) 2018 Vinnie Falco (vinnie dot falco at gmail dot com)
// Distributed under the Boost Software License, Version 1.0. (See copy at http://www.boost.org/LICENSE_1_0.txt)
#include "server.hpp"
#include "room.hpp"
#include "base/router.hpp"
#include "network/server.hpp"
#include <thread>
#include <cassert>
#include <iostream>

GameAwesome::Server::Server(std::string_view ipAddress, unsigned short port) {
    impl = std::make_unique<::Server>(ipAddress, port);
}
GameAwesome::Server::~Server() = default;
void GameAwesome::Server::start() { impl->start(); }
void GameAwesome::Server::stop() { impl->stop(); }

bool read_request_path(std::string_view& str, unsigned short& retVal);

Server::Server(std::string_view ipAddress, unsigned short port)
    : server(ipAddress, port, router)
{
    router.addRule([&](const Request& request, std::unique_ptr<HttpSession>& session) -> bool {
        if (request.target() == "/room" and request.method() == http::verb::post) {
            addRoom();
            http::response<http::empty_body> res { http::status::no_content, request.version() };
            RESPOND(std::move(res));
        } else
        if (request.target() == "/room/" and request.method() == http::verb::get) {
            std::string res;
            for(const auto& room : getRooms()) {
                res += room.first; // TODO display some info about the rooms
            }
            RESPOND(textResponse(request, res));
        } else
        // See if it is a WebSocket Upgrade
        if(websocket::is_upgrade(request)) {
            std::cout << "(async http) websocket upgrade heard! " << request.target() << '\n';
            // The websocket connection is established! Transfer the socket and the request to the server
            std::string_view request_path = request.target();

            GameRoom* room = nullptr;
            RoomId roomId;
            AgentId agentId;
            if (read_request_path(request_path, roomId)
                and read_request_path(request_path, agentId)) {
                if (getRooms().find(roomId) == getRooms().end()) RESPOND(not_found(request));
                room = &getRooms().find(roomId)->second;
            } else RESPOND(bad_request(request, "Wrong path"));

            auto socket = HttpSession::decay(std::move(session));
            auto spec = room->addSpectator(socket, agentId);
            if (!spec) RESPOND(bad_request(request, "Room did not accept you"));

            spec->connect(request);
            return true;
        } else
            return false;
    });
}

void Server::start(){
    // Capture SIGINT and SIGTERM to perform a clean shutdown
    boost::asio::signal_set signals(server.getContext(), SIGINT, SIGTERM);
    signals.async_wait([&](boost::system::error_code const&, int signal){
        std::cout << "(OS-level handler) Received signal " << signal << ". Stopping...\n";
        // Stop the io_context. This will cause run()
        // to return immediately, eventually destroying the
        // io_context and any remaining handlers in it.
        stop();
    });

    std::cout << "(network) Starting server...\n";
    server.start();
}

void Server::stop(){
    std::cout << "(network) ...stopping server and interrupting rooms\n";
    for(auto& [id, room] : rooms){
        room.interrupt();
    }
    server.stop(); //Stop io_context. Now the only things that can block are in the game threads.
    rooms.clear(); //Closing all rooms (some might wait for their game to end)
}

std::pair<RoomId, GameRoom&> Server::addRoom(RoomId newRoomId) {
    std::cout << "(main) Add room to server\n";
    auto [iter, success] = rooms.insert(std::make_pair<RoomId, GameRoom>(std::move(newRoomId), GameRoom(newRoomId)));
    assert(success and iter->first == newRoomId);
    return { newRoomId, iter->second };
}

void Server::askForRoomDeletion(RoomId id) {
    std::cout << "(main server) room deletion requested\n";

    server.async_do([&,id=id] {
        GameRoom& room = rooms.find(id)->second;
        room.interrupt();
    });
    server.async_do([&,id=id]{
        std::cout << "(async server) room deletion in progress...\n";
        rooms.erase(id);
        std::cout << "(async server) ...room deleted!\n";
    });
}

//Writes the read values to @param roomId and @param agentId and returns a bool to indicate errors, C-style.
bool read_request_path(std::string_view& str, unsigned short& retVal){
    unsigned int iter = 0;
    if(str[iter++] != '/') return false;
    retVal = 0;
    do{
        char digit = str[iter++] - '0';
        if(0 > digit or digit > 9) return false;
        retVal = 10*retVal + digit;
    } while(iter < str.size() and str[iter] != '/');
    str = str.substr(iter);
    return true;
}
