// Adapted from https://github.com/vinniefalco/CppCon2018
// Copyright (c) 2018 Vinnie Falco (vinnie dot falco at gmail dot com)
// Distributed under the Boost Software License, Version 1.0. (See copy at http://www.boost.org/LICENSE_1_0.txt)
#ifndef CPPCON2018_HTTP_SESSION_HPP
#define CPPCON2018_HTTP_SESSION_HPP

#include "routing.hpp"
#include <boost/beast.hpp>
#include <boost/asio/ip/tcp.hpp>
#include <boost/asio.hpp>
#include <memory>

class Router;

namespace beast = boost::beast;
namespace http = beast::http;
using boost::asio::ip::tcp;
using boost::system::error_code;

/** Represents an established HTTP connection. */
class HttpSession {
    tcp::socket _socket;
    beast::flat_buffer _buffer;
    http::request<http::string_body> _req;
    const Router& router;

    static void fail(error_code ec, std::string_view what);
    static void on_read(std::unique_ptr<HttpSession>&& self, error_code ec, std::size_t);
    static void on_write(std::unique_ptr<HttpSession>&& self, error_code ec, std::size_t, bool close);

    explicit HttpSession(tcp::socket&& socket, const Router& router);
public:
    static std::unique_ptr<HttpSession> factory(tcp::socket&& socket, const Router& router){
        return std::unique_ptr<HttpSession>( new HttpSession(std::move(socket), router) );
    }
    static void run(std::unique_ptr<HttpSession>&& self);
    template<typename HttpBodyType>
    static void sendResponse(std::unique_ptr<HttpSession>&& self, http::response<HttpBodyType>&& res);
    static tcp::socket decay(std::unique_ptr<HttpSession>&& self) {
        return std::move(self->_socket);
    }
};

#endif
