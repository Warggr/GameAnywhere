// Adapted from https://github.com/vinniefalco/CppCon2018
// Copyright (c) 2018 Vinnie Falco (vinnie dot falco at gmail dot com)
// Distributed under the Boost Software License, Version 1.0. (See copy at http://www.boost.org/LICENSE_1_0.txt)

#ifndef CPPCON2018_SHARED_STATE_HPP
#define CPPCON2018_SHARED_STATE_HPP

#include "spectator.hpp"
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <memory>
#include <thread>
#include <cassert>

class Session;
class Spectator;
class Server;

class ServerRoom {
protected:
    std::unordered_set<std::shared_ptr<Spectator>> spectators;
    std::unordered_map<AgentId, std::shared_ptr<Session>> sessions;
public:
    std::shared_ptr<Session> addSession(AgentId agentId){
        auto [iter, success] = sessions.insert({ agentId, std::make_shared<Session>(*this, agentId) });
        assert(success);
        return iter->second;
    }

    //Create a Spectator and allows it to join once it has done the websocket handshake
    std::shared_ptr<Spectator> addSpectator(tcp::socket& socket, AgentId id = 0);

    void interrupt();

    void reportAfk(Spectator& spec);

    void onConnect(Spectator& spectator);

    const std::unordered_set<std::shared_ptr<Spectator>>& getSpectators() const { return spectators; }
    const std::unordered_map<AgentId, std::shared_ptr<Session>>& getSessions() const { return sessions; }

    void send(std::shared_ptr<const std::string> message);
    void send(const std::string& message){ send(std::make_shared<const std::string>(message)); }
};

using RoomId = unsigned short int;

class GameRoom: public ServerRoom {
    std::thread myThread;
    Server* const server;
public:
    GameRoom(Server* server, RoomId roomId);
    ~GameRoom(){
        if(myThread.joinable()) myThread.join();
    }
};

#endif
