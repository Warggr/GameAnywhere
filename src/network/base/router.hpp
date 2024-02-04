#ifndef GAMEAWESOME_ROUTER_HPP
#define GAMEAWESOME_ROUTER_HPP

#include "routing.hpp"
#include "http_session.hpp"
#include <boost/beast.hpp>
#include <vector>
#include <string_view>
#include <functional>
#include <cassert>

namespace http = boost::beast::http;

using RoutingRule = std::function<bool(const Request&, std::unique_ptr<HttpSession>&)>;

http::response<http::string_body> bad_request(const Request& req, std::string_view why);
http::response<http::string_body> not_found(const Request& req);
http::response<http::string_body> redirect(const Request& req, std::string_view location);
http::response<http::string_body> jsonResponse(const Request& req, std::string_view j);
http::response<http::string_body> server_error(const Request& req, std::string_view what);
http::response<http::string_body> textResponse(const Request& req, std::string_view text);

#define RESPOND(response) { HttpSession::sendResponse(std::move(session), response); return true; }

class Router {
    std::vector<RoutingRule> routingRules;
public:
    void handle(const Request& request, std::unique_ptr<HttpSession>&& session) const {
        for(const auto& rule: routingRules) {
            bool handled = rule(request, session);
            if(handled){
                assert(not session);
                return;
            }
        }
        return HttpSession::sendResponse(std::move(session), bad_request(request, "not found") );
    }
    void addRule(RoutingRule&& rule) {
        routingRules.emplace_back(rule);
    }
};

class SimpleRouter {
    const std::string_view path;
    const http::verb method;
public:
    SimpleRouter(std::string_view path, http::verb method): path(path), method(method) {}
    virtual ~SimpleRouter() = default;
    virtual void handle(const Request& request, std::unique_ptr<HttpSession>&& session) const = 0;

    bool operator() (const Request& request, std::unique_ptr<HttpSession>& session) const;
};

class Heartbeat final : public SimpleRouter {
public:
    Heartbeat(): SimpleRouter("/heartbeat", http::verb::get) {};
    void handle(const Request &request, std::unique_ptr<HttpSession>&& session) const override;
};

class StaticFileServer {
    const std::string doc_root, web_path_root;
public:
    explicit StaticFileServer(std::string_view doc_root, std::string_view web_path_root)
    : doc_root(doc_root), web_path_root(web_path_root) {}
    bool operator()(const Request& request, std::unique_ptr<HttpSession>& session) const;
};

#endif //GAMEAWESOME_ROUTER_HPP
