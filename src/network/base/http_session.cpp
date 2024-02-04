// Adapted from https://github.com/vinniefalco/CppCon2018
// Copyright (c) 2018 Vinnie Falco (vinnie dot falco at gmail dot com)
// Distributed under the Boost Software License, Version 1.0. (See copy at http://www.boost.org/LICENSE_1_0.txt)

#include "http_session.hpp"
#include "nlohmann/json.hpp"
#include <iostream>
#include <utility>

#include "router.hpp"

namespace websocket = boost::beast::websocket;

HttpSession::HttpSession(tcp::socket&& socket, const Router& router)
    : _socket(std::move(socket))
    , router(router)
{
    std::cout << "(async listener) Creating HttpSession\n";
}

void HttpSession::run(std::unique_ptr<HttpSession>&& self){
    auto* self_ptr = self.get();
    // Read a request
    http::async_read(self_ptr->_socket, self_ptr->_buffer, self_ptr->_req,
        [&,self=std::move(self)](error_code ec, std::size_t bytes) mutable {
            on_read(std::move(self), ec, bytes);
        });
}

// Report a failure
void HttpSession::fail(error_code ec, std::string_view what){
    // Don't report on canceled operations
    if(ec == boost::asio::error::operation_aborted) return;
    std::cerr << what << ": " << ec.message() << "\n";
}

template<typename HttpBodyType>
void HttpSession::sendResponse(std::unique_ptr<HttpSession>&& self, http::response<HttpBodyType>&& res) {
    std::cout << "(http) " << res.result_int() << ' ' << self->_req.method_string() << ' '
              << self->_req.target() << ' ' << res.payload_size().get() << "B\n";
    res.set(http::field::server, BOOST_BEAST_VERSION_STRING);
    // TODO CORS policy (probably some kind of env variable?)
    res.set(http::field::access_control_allow_origin, "*");
    res.keep_alive(self->_req.keep_alive());
    res.prepare_payload();

    auto* self_ptr = self.get();
    // Write the response
    http::async_write(self_ptr->_socket, res,
        [&,self=std::move(self),close=res.need_eof()](error_code ec, std::size_t bytes) mutable {
            on_write(std::move(self), ec, bytes, close);
    });
}

// tell the compiler that we will need those templates
template void HttpSession::sendResponse<http::string_body>(std::unique_ptr<HttpSession>&& self, http::response<http::string_body>&& res);
template void HttpSession::sendResponse<http::empty_body>(std::unique_ptr<HttpSession>&& self, http::response<http::empty_body>&& res);
template void HttpSession::sendResponse<http::file_body>(std::unique_ptr<HttpSession>&& self, http::response<http::file_body>&& res);

void HttpSession::on_read(std::unique_ptr<HttpSession>&& self, error_code ec, std::size_t){
    // This means they closed the connection
    if(ec == http::error::end_of_stream){
        self->_socket.shutdown(tcp::socket::shutdown_send, ec);
        return;
    }

    // Handle the error, if any
    if(ec){
        return fail(ec, "read");
    }

    if(self->_req.method() == boost::beast::http::verb::options) {
        //see https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS
        http::response<http::string_body> res{http::status::no_content, self->_req.version()};
        res.set(http::field::access_control_allow_methods, "POST, GET, OPTIONS");
        res.set(http::field::access_control_allow_headers, "Content-Type");
        res.set(http::field::access_control_max_age, "86400");

        return sendResponse(std::move(self), std::move(res));
    }

    self->router.handle(self->_req, std::move(self));
}

void HttpSession::on_write(std::unique_ptr<HttpSession>&& self, error_code ec, std::size_t, bool close){
    // Handle the error, if any
    if(ec){
        return fail(ec, "write");
    }

    if(close){
        // This means we should close the connection, usually because
        // the response indicated the "Connection: close" semantic.
        self->_socket.shutdown(tcp::socket::shutdown_send, ec);
        return;
    }

    // Clear contents of the request message, otherwise the read behavior is undefined.
    self->_req = {};
    auto* self_ptr = self.get();

    // Read another request
    http::async_read(self_ptr->_socket, self_ptr->_buffer, self_ptr->_req,
        [&,self=std::move(self)](error_code ec, std::size_t bytes) mutable{
            on_read(std::move(self), ec, bytes);
    });
}
