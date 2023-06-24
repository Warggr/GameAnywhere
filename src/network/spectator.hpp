// Adapted from https://github.com/vinniefalco/CppCon2018
// Copyright (c) 2018 Vinnie Falco (vinnie dot falco at gmail dot com)
// Distributed under the Boost Software License, Version 1.0. (See copy at http://www.boost.org/LICENSE_1_0.txt)
#ifndef CPPCON2018_WEBSOCKET_SESSION_HPP
#define CPPCON2018_WEBSOCKET_SESSION_HPP

#include "net.hpp"
#include <boost/beast.hpp>
#include <memory>
#include <string>
#include <queue>
#include <mutex>
#include <cassert>

class ServerRoom;
class NetworkAgent;

namespace beast = boost::beast;
namespace http = boost::beast::http;
namespace websocket = boost::beast::websocket;

/** Represents an active WebSocket connection to the server. */
class Spectator : public std::enable_shared_from_this<Spectator> {
public:
    enum state { FREE, CLAIMED, CONNECTED, INTERRUPTED_BY_SERVER };
protected:
    beast::flat_buffer buffer; //Only used for reading
    std::unique_ptr<websocket::stream<tcp::socket>> ws;
    std::queue<std::shared_ptr<const std::string>> writing_queue; //All messages that haven't been sent yet
    std::mutex protectReadingQueue;
    std::condition_variable signalReadingQueue;
    std::queue<std::string> reading_queue; //All messages that haven't been read yet
    bool listening = false;
    ServerRoom& room;
    enum state state = FREE;
    bool previouslyConnected = false;
    void on_connect(error_code ec);
    void on_write(error_code ec, std::size_t bytes_transferred);
    void on_read(error_code ec, std::size_t bytes_transferred);
    void fail(error_code ec, char const* what);
    Spectator(ServerRoom& room, AgentId id);
public:
    const AgentId id; //Is 0 when we're not an agent, but only a spectator

    Spectator(ServerRoom& room): Spectator(room, 0){};
    ~Spectator();
    Spectator& claim(tcp::socket&& socket);
    void interrupt();

    //Accepts the websocket handshake asynchronously
    template<class Body, class Allocator>
    void connect(http::request<Body, http::basic_fields<Allocator>> req){
        ws->async_accept( req, [sp=shared_from_this()](error_code ec){ sp->on_connect(ec); } );
    }

    void send(std::shared_ptr<const std::string> message);
    void send(const std::string& message){ send(std::make_shared<const std::string>(message)); }
    void send_sync(std::shared_ptr<const std::string> message);

    bool isConnected() const { return state == CONNECTED; }
    bool isClaimed() const { return state == CLAIMED; }
    enum state getState() const { return state; }
    bool wasPreviouslyConnected() const { return previouslyConnected; }
};

class Session: public Spectator {
public:
    Session(ServerRoom& room, AgentId id): Spectator(room, id){
        assert(id != 0);
    }
    void awaitReconnect();
    std::string get_sync();
};

#endif
