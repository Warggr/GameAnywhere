#ifndef GAMEAWESOME_GAMEAWESOME_SERVER_HPP
#define GAMEAWESOME_GAMEAWESOME_SERVER_HPP

#include "server.h"
#include <string_view>
#include <memory>
#include <string>

namespace GameAwesome {

class Server {
    GameAwesome_Server* impl;
public:
    Server(std::string_view ipAddress, unsigned short port)
    : impl( GameAwesome_Server_construct(std::string(ipAddress).c_str(), port) )
    {
    }
    ~Server(){
        GameAwesome_Server_destruct(impl);
    }
    void start(){
        GameAwesome_Server_start(impl);
    }
    void stop(){
        GameAwesome_Server_stop(impl);
    }
};

}

#endif //GAMEAWESOME_GAMEAWESOME_SERVER_HPP
