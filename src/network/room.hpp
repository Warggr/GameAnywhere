// Adapted from https://github.com/vinniefalco/CppCon2018
// Copyright (c) 2018 Vinnie Falco (vinnie dot falco at gmail dot com)
// Distributed under the Boost Software License, Version 1.0. (See copy at http://www.boost.org/LICENSE_1_0.txt)

#ifndef CPPCON2018_SHARED_STATE_HPP
#define CPPCON2018_SHARED_STATE_HPP

#include "spectator.hpp"
#include "net.hpp"
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <memory>
#include <cassert>
#include <mutex>

class Session;
class Spectator;
class Server_impl;
class Server;

class ServerRoom {
protected:
    std::string greeterMessage; //The message that will be sent to every new spectator
    bool isGameRoom = false;
    std::unordered_set<std::shared_ptr<Spectator>> spectators;
    std::unordered_map<AgentId, std::shared_ptr<Session>> sessions;
    Server* const server; // TODO optimize: this is unnecessary
    ServerRoom(Server* server, bool isGameRoom): isGameRoom(isGameRoom), server(server) {}
public:
    ServerRoom(Server* server): ServerRoom(server, false) {};
    std::shared_ptr<Session> addSession(AgentId agentId){
        auto [iter, success] = sessions.insert({ agentId, std::make_shared<Session>(*this, agentId) });
        assert(success);
        return iter->second;
    }

    //Create a Spectator and allows it to join once it has done the websocket handshake
    std::shared_ptr<Spectator> addSpectator(tcp::socket& socket, AgentId id = 0);

    void setGreeterMessage(const std::string& message){ greeterMessage = message; }

    void interrupt();

    void reportAfk(Spectator& spec);

    void onConnect(Spectator& spectator);

    const std::unordered_set<std::shared_ptr<Spectator>>& getSpectators() const { return spectators; }

    const std::unordered_map<AgentId, std::shared_ptr<Session>>& getSessions() const { return sessions; }

    void send(std::shared_ptr<const std::string> message);
    void send(const std::string& message){ send(std::make_shared<const std::string>(message)); }

    Server* getServer() const { return server; }
};

/* Represents a room on the server on which a game takes place (or will take place shortly) */
class GameRoom: public ServerRoom {
    bool firstStep = true;
public:
    GameRoom(Server_impl* server, RoomId id);

    void setGreeterMessage(const std::string& greeterMessage);

    void send(const std::string& message);
};

#ifdef HTTP_CONTROLLED_SERVER
#include "setup/agent_setup.hpp"
#include <thread>
#include <array>
struct Team;
class Agent;
#endif

class GameRoom_impl : public GameRoom {
#ifdef HTTP_CONTROLLED_SERVER
    std::thread myThread;
#endif
    Server_impl* const server;
public:
    template<class... Args>
    GameRoom_impl(Server_impl* server, Args&&... args): GameRoom(server, args...), server(server) {}
    GameRoom_impl(GameRoom_impl&& move) = default;
#ifdef HTTP_CONTROLLED_SERVER
    ~GameRoom_impl(){
        if(myThread.joinable()) myThread.join();
    }
    void launchGame(RoomId id, GameDescription&& gameDescr);
#endif
};

#endif
