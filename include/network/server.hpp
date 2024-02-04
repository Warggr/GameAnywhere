#ifndef GAMEAWESOME_GAMEAWESOME_SERVER_HPP
#define GAMEAWESOME_GAMEAWESOME_SERVER_HPP

#include <string_view>

class Server;

namespace GameAwesome {

class Server {
    ::Server* impl;
public:
    Server(std::string_view ipAddress, unsigned short port);
    ~Server();
    void start();
    void stop();
};

}

#endif //GAMEAWESOME_GAMEAWESOME_SERVER_HPP
