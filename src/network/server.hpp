#ifndef REVELATION_SERVER_HPP
#define REVELATION_SERVER_HPP

#include "listener.hpp"
#include <unordered_set>
#include <utility>

class HttpSession;

/**
 * Class Server must be completely agnostic of whether the server is http-controlled or not.
 * If in the future, the server needs to know something about the dependent properties of Server_impl,
 * we can use a bridge pattern (every Server must contain a pointer to a Server_impl)
 */
class Server {
protected:
    net::io_context ioc; // The io_context is required for all I/O
    //ioc needs to be initialized before listener, that's why it comes first in the file
    Listener listener; // The Listener listens for new clients and adds them to the Rooms
    std::unordered_set<HttpSession*> sessions; //all these pointers are owning

public:
    Server(const char* ipAddress, unsigned short port);

    ~Server();

    void addSession(tcp::socket&& socket);

    void askForHttpSessionDeletion(HttpSession* session);

    template<typename Function>
    void async_do(Function&& fun){
        net::post(ioc, std::forward<Function>(fun));
    }
};

#endif //REVELATION_SERVER_HPP
