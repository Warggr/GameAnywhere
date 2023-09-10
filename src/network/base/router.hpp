#ifndef GAMEAWESOME_ROUTER_HPP
#define GAMEAWESOME_ROUTER_HPP

#include "routing.hpp"
#include "http_session.hpp"
#include <boost/beast.hpp>
#include <vector>
#include <string_view>
#include <functional>
#include <optional>
#include <cassert>

namespace http = boost::beast::http;

class RoutingRule {
public:
    virtual ~RoutingRule() = default;
    virtual bool operator()(const Request&, std::unique_ptr<HttpSession>&) const = 0;
};

http::response<http::string_body> bad_request(const Request& req, std::string_view why);
http::response<http::string_body> not_found(const Request& req);
http::response<http::string_body> redirect(const Request& req, std::string_view location);
http::response<http::string_body> jsonResponse(const Request& req, std::string_view j);
http::response<http::string_body> server_error(const Request& req, std::string_view what);
http::response<http::string_body> textResponse(const Request& req, std::string_view text);

#define RESPOND(response) { HttpSession::sendResponse(std::move(session), response); return true; }

class Router {
    std::vector<std::unique_ptr<RoutingRule>> routingRules;
public:
    void handle(const Request& request, std::unique_ptr<HttpSession>&& session) const {
        for(const auto& rule: routingRules) {
            bool handled = (*rule)(request, session);
            if(handled){
                assert(not session);
                return;
            }
        }
        return HttpSession::sendResponse(std::move(session), bad_request(request, "not found") );
    }
    template<typename Rule, typename... Args>
    void addRule(Args&&... args) {
        routingRules.push_back(std::make_unique<Rule>(args...));
    }
};

#endif //GAMEAWESOME_ROUTER_HPP
