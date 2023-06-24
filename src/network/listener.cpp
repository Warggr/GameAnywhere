// Adapted from https://github.com/vinniefalco/CppCon2018
// Copyright (c) 2018 Vinnie Falco (vinnie dot falco at gmail dot com)
// Distributed under the Boost Software License, Version 1.0. (See copy at http://www.boost.org/LICENSE_1_0.txt)
#include "listener.hpp"
#include "server.hpp"
#include <iostream>

Listener::Listener(Server& server, net::io_context& ioc, const tcp::endpoint& endpoint)
    : acceptor(ioc)
    , socket(ioc)
    , server(server)
{
    error_code ec;

    // Open the acceptor
    acceptor.open(endpoint.protocol(), ec);
    if(ec){ fail(ec, "open"); return; }

    // Allow address reuse
    acceptor.set_option(net::socket_base::reuse_address(true));
    if(ec){ fail(ec, "set_option"); return; }

    // Bind to the server address
    acceptor.bind(endpoint, ec);
    if(ec){ fail(ec, "bind"); return; }

    // Start listening for connections
    acceptor.listen(net::socket_base::max_listen_connections, ec);
    if(ec){ fail(ec, "listen"); return; }
}

void Listener::listen(){
    std::cout << "(network) start accepting connections\n";
    // Start accepting a connection
    acceptor.async_accept(
        socket,
        [&](error_code ec){
            on_accept(ec);
        });
}

// Report a failure
void Listener::fail(error_code ec, char const* what){
    // Don't report on canceled operations
    if(ec == net::error::operation_aborted) return;
    std::cerr << what << ": " << ec.message() << "\n";
}

// Handle a connection
void Listener::on_accept(error_code ec){
    std::cout << "(async listener) accept connection\n";

    if(ec) return fail(ec, "accept");

    // Launch a new session for this connection
    server.addSession(std::move(socket));

    // Accept another connection
    acceptor.async_accept(
        socket,
        [&](error_code ec){
            on_accept(ec);
        });
}
