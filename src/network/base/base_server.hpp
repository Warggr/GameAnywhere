#ifndef GAMEAWESOME_BASESERVER_HPP
#define GAMEAWESOME_BASESERVER_HPP

#include <boost/asio/ip/tcp.hpp>
#include <boost/asio.hpp>
#include <string_view>
#include "router.hpp"

class Server;

using boost::system::error_code;
using boost::asio::ip::tcp;

class BaseServer {
protected:
    boost::asio::io_context ioc; // The io_context is required for all I/O
    //ioc needs to be initialized before everything else, that's why it comes first in the file

    // These listen to incoming HTTP connections
    tcp::acceptor acceptor;
    tcp::socket socket;

    void on_accept(error_code ec);

    const Router& router; // The Router determines the semantics of the HTTP endpoint
public:
    BaseServer(std::string_view ipAddress, unsigned short port, const Router& router);
    ~BaseServer();

    // This function listens to connections and runs indefinitely.
    // To stop it, you need to call stop() (presumably from another thread)
    void start();
    void stop();

    template<typename Function>
    void async_do(Function&& fun){
        boost::asio::post(ioc, std::forward<Function>(fun));
    }

    boost::asio::io_context& getContext() { return ioc; }
};

#endif //GAMEAWESOME_BASESERVER_HPP
