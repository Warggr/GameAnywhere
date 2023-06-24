// Adapted from https://github.com/vinniefalco/CppCon2018
// Copyright (c) 2018 Vinnie Falco (vinnie dot falco at gmail dot com)
// Distributed under the Boost Software License, Version 1.0. (See copy at http://www.boost.org/LICENSE_1_0.txt)

#include "http_session.hpp"
#include "spectator.hpp"
#include "server_impl.hpp"
#include "visitor.hpp"
#include "nlohmann/json.hpp"
#include <iostream>
#include <utility>

#ifdef HTTP_CONTROLLED_SERVER
#include "setup/agent_setup.hpp"
#include "control/agent.hpp"
#include "setup/team.hpp"
#include "setup/www_visitor.hpp"
#endif

using json = nlohmann::json;

namespace { // local-only functions
    [[maybe_unused]] std::string_view mime_type(std::string_view path);

    //Writes the read values to @param roomId and @param agentId and returns a bool to indicate errors, C-style.
    bool read_request_path(std::string_view& str, unsigned short& retVal){
        unsigned int iter = 0;
        if(str[iter++] != '/') return false;
        retVal = 0;
        do{
            char digit = str[iter++] - '0';
            if(0 > digit or digit > 9) return false;
            retVal = 10*retVal + digit;
        } while(iter < str.size() and str[iter] != '/');
        str = str.substr(iter);
        return true;
    }
}

HttpSession::HttpSession(tcp::socket&& socket, Server_impl& server)
    : socket_(std::move(socket))
    , server(server)
{
    std::cout << "(async listener) Creating HttpSession\n";
}

void HttpSession::run(){
    // Read a request
    http::async_read(socket_, buffer_, req_,
        [&](error_code ec, std::size_t bytes){
            on_read(ec, bytes);
        });
}

// Report a failure
void HttpSession::fail(error_code ec, char const* what){
    // Don't report on canceled operations
    if(ec == net::error::operation_aborted) return;
    std::cerr << what << ": " << ec.message() << "\n";
}

using Request = http::request<http::string_body>;
using Response = http::response<http::string_body>;

template<typename HttpBodyType>
void HttpSession::sendResponse(http::response<HttpBodyType>&& res){
    std::cout << "(http) " << res.result_int() << ' ' << req_.method_string() << ' '
        << req_.target() << ' ' << res.payload_size().get() << "B\n";
    res.set(http::field::server, BOOST_BEAST_VERSION_STRING);
    res.set(http::field::access_control_allow_origin, "*");
    res.keep_alive(req_.keep_alive());

    res.prepare_payload();
    // The lifetime of the message has to extend
    // for the duration of the async operation so
    // we use a shared_ptr to manage it.
    using response_type = typename std::decay<decltype(res)>::type;
    auto sp = std::make_shared<response_type>(std::forward<decltype(res)>(res));

    // Write the response
    http::async_write(this->socket_, *sp,
                      [&, sp](error_code ec, std::size_t bytes){ on_write(ec, bytes, sp->need_eof()); });
}

[[maybe_unused]] static Response bad_request(const Request& req_, std::string_view why){
    http::response<http::string_body> res{http::status::bad_request, req_.version()};
    res.set(http::field::content_type, "text/plain");
    res.body() = why;
    return res;
}

[[maybe_unused]] static Response not_found(const Request& req_, std::string_view target){
    http::response<http::string_body> res{http::status::not_found, req_.version()};
    res.set(http::field::content_type, "text/plain");
    res.body() = "The resource '" + std::string(target) + "' was not found.";
    return res;
}

[[maybe_unused]] static Response redirect(const Request& req_, std::string_view location){
    http::response<http::string_body> res{http::status::moved_permanently, req_.version()};
    res.set(http::field::location, location);
    return res;
}

[[maybe_unused]] static Response jsonResponse(const Request& req_, std::string_view j){
    http::response<http::string_body> res{ http::status::ok, req_.version() };
    res.set(http::field::content_type, "application/json");
    res.body() = j;
    return res;
}

[[maybe_unused]] static Response server_error(const Request& req_, std::string_view what){
    http::response<http::string_body> res{http::status::internal_server_error, req_.version()};
    res.set(http::field::content_type, "text/html");
    res.body() = "An error occurred: '" + std::string(what) + "'";
    return res;
}

void HttpSession::on_read(error_code ec, std::size_t){
    // This means they closed the connection
    if(ec == http::error::end_of_stream){
        socket_.shutdown(tcp::socket::shutdown_send, ec);
        server.askForHttpSessionDeletion(this);
        return;
    }

    // Handle the error, if any
    if(ec){
        server.askForHttpSessionDeletion(this);
        return fail(ec, "read");
    }

#define RESPOND(function, ...) return sendResponse(function(req_, __VA_ARGS__ ))

    // See if it is a WebSocket Upgrade
    if(websocket::is_upgrade(req_)){
        std::cout << "(async http) websocket upgrade heard! " << req_.target() << '\n';
        // The websocket connection is established! Transfer the socket and the request to the server
        std::string_view request_path = req_.target();

        ServerRoom* room = nullptr;
        RoomId roomId; AgentId agentId;
#ifdef HTTP_CONTROLLED_SERVER
        if(request_path == "/control"){
            room = &server.controlRoom;
            agentId = 0;
        } else
#endif
        if(read_request_path(request_path, roomId)
        and read_request_path(request_path, agentId)) {
            if (server.getRooms().find(roomId) == server.getRooms().end())
                RESPOND(not_found, "Room not found");
            room = &server.getRooms().find(roomId)->second;
        }
        else RESPOND(bad_request, "Wrong path");

        auto spec = room->addSpectator(socket_, agentId);
        if (!spec)
            RESPOND(bad_request, "Room did not accept you");

        spec->connect(std::move(req_));
        server.askForHttpSessionDeletion(this); //don't schedule any further network operations, delete this, and die.
        return;
    }
    else if(req_.method() == boost::beast::http::verb::options) {
        //see https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS
        http::response<http::string_body> res{http::status::no_content, req_.version()};
        res.set(http::field::access_control_allow_methods, "POST, GET, OPTIONS");
        res.set(http::field::access_control_allow_headers, "Content-Type");
        res.set(http::field::access_control_max_age, "86400");
        return sendResponse(std::move(res));
    }
#define ADD_ENDPOINT(endpoint, thismethod) else if(req_.target() == endpoint and req_.method() == boost::beast::http::verb::thismethod)
    ADD_ENDPOINT("/heartbeat", get){
        return sendResponse( http::response<http::string_body>( http::status::ok, req_.version() ) );
    }
#ifdef HTTP_CONTROLLED_SERVER
    ADD_ENDPOINT("/room/grammar", get){
        RESPOND(jsonResponse, grammar_as_json_string);
    }
    ADD_ENDPOINT("/room", post){
        GameDescription gameDescr;
        if(req_.body().empty()){
            gameDescr.agents = { AgentDescriptor::NETWORK, AgentDescriptor::NETWORK };
        } else {
            auto encoding = req_[http::field::content_type];
            if(encoding != "application/json")
                RESPOND(bad_request, "Need JSON description of agents");
            try{
                json agentDescrJson = json::parse(req_.body());
                gameDescr = parseGame(agentDescrJson);
            } catch(json::parse_error& err) {
                RESPOND(bad_request, err.what());
            } catch(AgentCreationException& err){
                RESPOND(bad_request, err.what());
            }
        }
        auto [roomId, room] = server.addRoom();
        room.launchGame(roomId, std::move(gameDescr));

        http::response<http::string_body> res{ http::status::created, req_.version() };
        res.set(http::field::content_type, "text/plain");
        res.body() = std::to_string(roomId);
        return sendResponse(std::move(res));
    }
    ADD_ENDPOINT("/unit", post){
        auto encoding = req_[http::field::content_type];
        if(encoding != "application/x-www-form-urlencoded")
            RESPOND(bad_request, "Form should be urlencoded");
        try{
            WwwDataVisitor visitor(req_.body());
            ImmutableCharacter chr(visitor);
            if(not visitor.empty())
                throw std::invalid_argument(std::string("Extra value: ").append(visitor.anyKey()));
            if(server.repo.addCharacter(std::move(chr)))
                return sendResponse( http::response<http::string_body>( http::status::ok, req_.version() ) );
            else
                return sendResponse( http::response<http::string_body>( http::status::conflict, req_.version() ) );
        } catch(const std::invalid_argument& err) {
            RESPOND(bad_request, err.what());
        }
    }
    ADD_ENDPOINT("/team", post){
        auto encoding = req_[http::field::content_type];
        if(encoding != "application/x-www-form-urlencoded")
            RESPOND(bad_request, "Form should be urlencoded");
        WwwDataVisitor visitor(req_.body());
        try {
            server.repo.createTeam(visitor);
            if(not visitor.empty())
                throw std::invalid_argument(std::string("Extra value: ").append(visitor.anyKey()));
            return sendResponse( http::response<http::string_body>( http::status::ok, req_.version() ) );
        } catch(std::invalid_argument& err){
            RESPOND(bad_request, err.what());
        }
    }
    ADD_ENDPOINT("/team/random", post){
        Generator seed(getRandom());
        server.repo.mkRandom(seed, server.repo, ARMY_SIZE);
        return sendResponse( http::response<http::string_body>( http::status::ok, req_.version() ) );;
    }
    ADD_ENDPOINT("/team/", get){
        json characters = json::array();
        for(const auto& [ name, character ] : server.repo.getCharacters()){
            characters.push_back(character);
        }
        json teams = json::array();
        for(const auto& [ name, team ] : server.repo.getTeams() ){
            teams.push_back(team);
        }
        json j = { {"teams", teams}, {"characters", characters} };
        RESPOND(jsonResponse, j.dump());
    }
#endif
    ADD_ENDPOINT("/room/", get){
        json j = json::array();
        for(const auto& [ roomId, room ] : server.getRooms()){
            json agents = json::array({ "Unavailable", "Unavailable" });
            unsigned nbSpectators = 0;
            for(const auto& [ agentId, agent ] : room.getSessions()){
                agents[agentId-1] = (
                        agent->isConnected() ? std::string("Connected") :
                        agent->isClaimed() ? std::string("claimed") :
                        std::string("free"));
            }
            for(const auto& spectator: room.getSpectators()){
                if(spectator->id != 0)
                    agents[spectator->id-1] = (spectator->isConnected() ? std::string("connected") : std::string("disconnected"));
                else nbSpectators++;
            }
            j.push_back(json({
                {"id", roomId},
                {"agents", agents},
                {"spectators", nbSpectators}
            }));
        }
        RESPOND(jsonResponse, j.dump());
    }
#ifdef HTTP_SERVE_FILES
    const char doc_api_path[] = "/files";
    constexpr unsigned int doc_api_path_len = sizeof(doc_api_path) / sizeof(char) - 1;
    if(req_.method() == http::verb::get or req_.method() == http::verb::head){
        if(boost::beast::iequals(req_.target(), "/"))
            RESPOND(redirect, "/files/");

        std::string_view req_path;

        if(boost::beast::iequals(doc_api_path, req_.target().substr(0, doc_api_path_len))){
            req_path = req_.target().substr(doc_api_path_len);
            auto const posParams = req_path.rfind("?");
            if(posParams != std::string_view::npos) req_path = req_path.substr(0, posParams);

            // Request path must be absolute and not contain ".."
            if(req_path.empty() or req_path[0] != '/' or req_path.find("..") != std::string_view::npos)
                RESPOND(bad_request, "Illegal request-target");
        }
        else if(boost::beast::iequals(req_.target(), "/favicon.ico")) req_path = "/favicon.ico";
        else RESPOND(bad_request, "File not found");

        auto path = path_cat(server.doc_root, req_path);
        if(req_path.back() == '/') path.append("index.html");
        // Attempt to open the file
        boost::beast::error_code error;
        http::file_body::value_type body;
        body.open(path.c_str(), boost::beast::file_mode::scan, error);

        // File doesn't exist
        if(error == boost::system::errc::no_such_file_or_directory) RESPOND(not_found, req_.target());
        // Unknown error
        if(error) RESPOND(server_error, error.message());

        // Cache the size since we need it after the move
        auto const size = body.size();

        // Respond to HEAD request
        if(req_.method() == http::verb::head){
            http::response<http::empty_body> res{http::status::ok, req_.version()};
            res.set(http::field::content_type, mime_type(path));
            res.content_length(size);
            return sendResponse(std::move(res));
        } else { // Respond to GET request
            http::response<http::file_body> res{
                    std::piecewise_construct,
                    std::make_tuple(std::move(body)),
                    std::make_tuple(http::status::ok, req_.version())};
            res.set(http::field::content_type, mime_type(path));
            res.content_length(size);
            return sendResponse(std::move(res));
        }
    }
#endif
    RESPOND(bad_request, "Not found");
}

void HttpSession::on_write(error_code ec, std::size_t, bool close){
    // Handle the error, if any
    if(ec) return fail(ec, "write");

    if(close){
        // This means we should close the connection, usually because
        // the response indicated the "Connection: close" semantic.
        socket_.shutdown(tcp::socket::shutdown_send, ec);
        server.askForHttpSessionDeletion(this);
        return;
    }

    // Clear contents of the request message, otherwise the read behavior is undefined.
    req_ = {};

    // Read another request
    http::async_read(socket_, buffer_, req_,
        [&](error_code ec, std::size_t bytes){ on_read(ec, bytes); });
}

namespace {

// Return a reasonable mime type based on the extension of a file.
std::string_view mime_type(std::string_view path){
    using boost::beast::iequals;
    auto const pos = path.rfind('.');
    if(pos == std::string_view::npos) return "application/text";
    const std::string_view ext = path.substr(pos+1);
    if(iequals(ext, "htm"))  return "text/html";
    if(iequals(ext, "html")) return "text/html";
    if(iequals(ext, "php"))  return "text/html";
    if(iequals(ext, "css"))  return "text/css";
    if(iequals(ext, "txt"))  return "text/plain";
    if(iequals(ext, "js"))   return "application/javascript";
    if(iequals(ext, "json")) return "application/json";
    if(iequals(ext, "xml"))  return "application/xml";
    if(iequals(ext, "swf"))  return "application/x-shockwave-flash";
    if(iequals(ext, "flv"))  return "video/x-flv";
    if(iequals(ext, "png"))  return "image/png";
    if(iequals(ext, "jpe"))  return "image/jpeg";
    if(iequals(ext, "jpeg")) return "image/jpeg";
    if(iequals(ext, "jpg"))  return "image/jpeg";
    if(iequals(ext, "gif"))  return "image/gif";
    if(iequals(ext, "bmp"))  return "image/bmp";
    if(iequals(ext, "ico"))  return "image/vnd.microsoft.icon";
    if(iequals(ext, "tiff")) return "image/tiff";
    if(iequals(ext, "tif"))  return "image/tiff";
    if(iequals(ext, "svg"))  return "image/svg+xml";
    if(iequals(ext, "svgz")) return "image/svg+xml";
    return "application/text";
}

}

// Append an HTTP rel-path to a local filesystem path.
// The returned path is normalized for the platform.
std::string path_cat(std::string_view base, std::string_view path){
    if(base.empty()) return std::string( path );
    auto result = std::string( base );
#if BOOST_MSVC
    constexpr char path_separator = '\\';
    if(result.back() == path_separator) result.resize(result.size() - 1);
    result.append(path.data(), path.size());
    for(auto& c : result)
        if(c == '/')
            c = path_separator;
#else
    constexpr char path_separator = '/';
    if(result.back() == path_separator) result.resize(result.size() - 1);
    result.append(path.data(), path.size());
#endif
    return result;
}
