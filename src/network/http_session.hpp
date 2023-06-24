// Adapted from https://github.com/vinniefalco/CppCon2018
// Copyright (c) 2018 Vinnie Falco (vinnie dot falco at gmail dot com)
// Distributed under the Boost Software License, Version 1.0. (See copy at http://www.boost.org/LICENSE_1_0.txt)
#ifndef CPPCON2018_HTTP_SESSION_HPP
#define CPPCON2018_HTTP_SESSION_HPP

#include "net.hpp"
#include <boost/beast.hpp>

class Server_impl;

namespace beast = boost::beast;
namespace http = boost::beast::http;

/** Represents an established HTTP connection. */
class HttpSession {
    tcp::socket socket_;
    beast::flat_buffer buffer_;
    http::request<http::string_body> req_;
    Server_impl& server;

    void fail(error_code ec, char const* what);
    template<typename HttpBodyType>
    void sendResponse(http::response<HttpBodyType>&& res);
    void on_read(error_code ec, std::size_t);
    void on_write(error_code ec, std::size_t, bool close);
public:
    explicit HttpSession(tcp::socket&& socket, Server_impl& server);
    void run();
};

#endif
