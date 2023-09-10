// Adapted from https://github.com/vinniefalco/CppCon2018
// Copyright (c) 2018 Vinnie Falco (vinnie dot falco at gmail dot com)
// Distributed under the Boost Software License, Version 1.0. (See copy at http://www.boost.org/LICENSE_1_0.txt)

#include "room.hpp"
#include "spectator.hpp"
#include "server.hpp"
#include <algorithm>
#include <iostream>

GameRoom::GameRoom(Server* server, RoomId): server(server) {
}

void ServerRoom::send(std::shared_ptr<const std::string> ss){
    for(const auto& session : spectators)
        session->send(ss);
    for(const auto& session : sessions)
        session.second->send(ss);
}

std::shared_ptr<Spectator> ServerRoom::addSpectator(tcp::socket& socket, AgentId id){
    if(id != 0){
        auto iter_agent = sessions.find(id);
        if(iter_agent == sessions.end()) return nullptr; //no such seat
        if(iter_agent->second->getState() != Spectator::state::FREE) return nullptr; //seat already claimed

        iter_agent->second->claim(std::move(socket));
        return iter_agent->second;
    } else {
        auto ptr = std::make_shared<Spectator>(*this);
        ptr->claim(std::move(socket));
        return ptr;
    }
}

void ServerRoom::onConnect(Spectator& spectator) {
    std::cout << "(async) spectator joined\n";
    if(spectator.id == 0)
        spectators.insert(spectator.shared_from_this());
    std::shared_ptr<const std::string> message = std::make_shared<const std::string>(
        "Welcome to the room!"
    );
    spectator.send(message);
}

void ServerRoom::reportAfk(Spectator& spec){
    if(spec.id == 0)
        spectators.erase(spec.shared_from_this());
}

void ServerRoom::interrupt() { //signals the game that it should end as soon as possible.
    for(auto& [i, session] : sessions)
        session->interrupt();
    for(const auto& spectator: spectators)
        spectator->interrupt();
}
