#ifndef REVELATION_SERVER_IMPL_HPP
#define REVELATION_SERVER_IMPL_HPP

#include "base/base_server.hpp"
#include "base/router.hpp"
#include "room.hpp"
#include <string_view>
#include <unordered_map>

using RoomId = unsigned short int;

class Server {
    BaseServer server;
    std::unordered_map<RoomId, GameRoom> rooms; //Each room contains a list of established WebSocket connections.
    RoomId lastUsedIdentifier = 0;
public:
    Router router;

    Server(std::string_view ipAddress, unsigned short port);

    void start(); // Similarly to BaseServer::start, this runs indefinitely and needs to be interrupted by stop() from outside
    void stop();

    void askForRoomDeletion(RoomId id);
    std::pair<RoomId, GameRoom&> addRoom(RoomId newRoomId);
    std::pair<RoomId, GameRoom&> addRoom(){ return addRoom(++lastUsedIdentifier); }
    std::unordered_map<RoomId, GameRoom>& getRooms() { return rooms; }
    const std::unordered_map<RoomId, GameRoom>& getRooms() const { return rooms; }
};

#endif //REVELATION_SERVER_IMPL_HPP
