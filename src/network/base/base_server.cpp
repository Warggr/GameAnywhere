// Adapted from https://github.com/vinniefalco/CppCon2018
// Copyright (c) 2018 Vinnie Falco (vinnie dot falco at gmail dot com)
// Distributed under the Boost Software License, Version 1.0. (See copy at http://www.boost.org/LICENSE_1_0.txt)
#include "base_server.hpp"
#include "http_session.hpp"
#include <iostream>

// Report a failure
void fail(error_code ec, const std::string_view& what){
    // Don't report on canceled operations
    if(ec == boost::asio::error::operation_aborted) return;
    std::cerr << what << ": " << ec.message() << "\n";
}

BaseServer::BaseServer(std::string_view ipAddress, unsigned short port, const Router& router)
    : acceptor(ioc), socket(ioc), router(router)
{
    const auto endpoint = tcp::endpoint{boost::asio::ip::make_address(ipAddress), port};
    std::cout << "(main) Starting server\n";

    error_code ec;

    // Open the acceptor
    acceptor.open(endpoint.protocol(), ec);
    if(ec){ fail(ec, "open"); return; }

    // Allow address reuse
    acceptor.set_option(boost::asio::socket_base::reuse_address(true));
    if(ec){ fail(ec, "set_option"); return; }

    // Bind to the server address
    acceptor.bind(endpoint, ec);
    if(ec){ fail(ec, "bind"); return; }

    // Start listening for connections
    acceptor.listen(boost::asio::socket_base::max_listen_connections, ec);
    if(ec){ fail(ec, "listen"); return; }
}

BaseServer::~BaseServer() = default;

// Handle a connection
void BaseServer::on_accept(error_code ec){
    std::cout << "(async listener) accept connection\n";

    if(ec) return fail(ec, "accept");

    // Launch a new session for this connection
    auto session = HttpSession::factory(std::move(socket), router);
    session->run(std::move(session));

    // Accept another connection
    acceptor.async_accept(socket,[&](error_code ec){
        on_accept(ec);
    });
}

void BaseServer::start(){
    std::cout << "(network) start accepting connections...\n";
    // Start accepting a connection
    acceptor.async_accept(socket, [&](error_code ec){ on_accept(ec); });

    //! this function runs indefinitely.
    //! To stop it, you need to call stop() (presumably from another thread)
    ioc.run();
}

void BaseServer::stop(){
    std::cout << "(network) ...stopping server and interrupting rooms\n";

    ioc.stop(); //Stop io_context. Now the only things that can block are in the game threads.
}
