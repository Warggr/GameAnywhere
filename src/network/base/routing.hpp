#ifndef GAMEAWESOME_ROUTING_HPP
#define GAMEAWESOME_ROUTING_HPP

#include <boost/beast.hpp>
#include <variant>

namespace http = boost::beast::http;

using Request = http::request<http::string_body>;

#endif //GAMEAWESOME_ROUTING_HPP
