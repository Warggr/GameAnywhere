#ifndef REVELATION_SERVER_IMPL_HPP
#define REVELATION_SERVER_IMPL_HPP

#include "server.hpp"
#include "room.hpp"
#include <string>

#ifdef HTTP_SERVE_FILES
#include "setup/units_repository.hpp"
#endif

class Server_impl: public Server {
    RoomId lastUsedIdentifier = 0;
    std::unordered_map<RoomId, GameRoom_impl> rooms; //Each room contains a list of established WebSocket connections.
public:
#ifdef HTTP_SERVE_FILES
    const std::string doc_root;
#endif
#ifdef HTTP_CONTROLLED_SERVER
    UnitsRepository repo;
    ServerRoom controlRoom;
#endif

    Server_impl(const char* ipAddress, unsigned short port
#ifdef HTTP_SERVE_FILES
            , std::string_view doc_root
#endif
    );

    void start();

    void stop();

    void askForRoomDeletion(RoomId id);
    std::pair<RoomId, GameRoom_impl&> addRoom(RoomId newRoomId);
    std::pair<RoomId, GameRoom_impl&> addRoom(){ return addRoom(++lastUsedIdentifier); }
    std::unordered_map<RoomId, GameRoom_impl>& getRooms() { return rooms; }
    const std::unordered_map<RoomId, GameRoom_impl>& getRooms() const { return rooms; }
};

std::string path_cat(std::string_view base, std::string_view path);

#endif //REVELATION_SERVER_IMPL_HPP
