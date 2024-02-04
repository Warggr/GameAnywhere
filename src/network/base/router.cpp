#include "router.hpp"

std::string path_cat(std::string_view base, std::string_view path);
std::string_view mime_type(std::string_view path);

bool SimpleRouter::operator() (const Request& request, std::unique_ptr<HttpSession>& session) const {
    if(request.target() != path or request.method() != method) return false;
    handle(request, std::move(session));
    return true;
}

void Heartbeat::handle(const Request &request, std::unique_ptr<HttpSession>&& session) const {
    return HttpSession::sendResponse(std::move(session),
         http::response<http::empty_body>(http::status::ok, request.version())
    );
}

bool StaticFileServer::operator() (const Request& request, std::unique_ptr<HttpSession>& session) const {
    if (request.method() != http::verb::get and request.method() != http::verb::head)
        return false;

    if (not beast::iequals(web_path_root, request.target().substr(0, web_path_root.length())))
        RESPOND(bad_request(request, "File not found"));
    std::string_view req_path = request.target().substr(web_path_root.length());

    auto const posParams = req_path.rfind('?');
    if (posParams != std::string_view::npos) req_path = req_path.substr(0, posParams);

    // Request path must be absolute and not contain ".."
    if (req_path.empty() or req_path[0] != '/' or req_path.find("..") != std::string_view::npos)
        RESPOND(bad_request(request, "Illegal request-target"));

    auto path = path_cat(doc_root, req_path);
    if (req_path.back() == '/') path.append("index.html");
    // Attempt to open the file
    boost::beast::error_code error;
    http::file_body::value_type body;
    body.open(path.c_str(), boost::beast::file_mode::scan, error);

    // File doesn't exist
    if (error == boost::system::errc::no_such_file_or_directory) RESPOND(not_found(request));
    // Unknown error
    if (error) RESPOND(server_error(request, error.message()));

    // Cache the size since we need it after the move
    auto const size = body.size();

    // Respond to HEAD request
    if (request.method() == http::verb::head) {
        http::response<http::empty_body> res{http::status::ok, request.version()};
        res.set(http::field::content_type, mime_type(path));
        res.content_length(size);
        RESPOND(std::move(res));
    } else { // Respond to GET request
        http::response<http::file_body> res{
                std::piecewise_construct,
                std::make_tuple(std::move(body)),
                std::make_tuple(http::status::ok, request.version())};
        const std::string_view mimeType = mime_type(path);
        res.set(http::field::content_type, mimeType);
        res.content_length(size);
        RESPOND(std::move(res));
    }
    return false;
}

http::response<http::string_body> bad_request(const Request& req, std::string_view why){
    http::response<http::string_body> res{http::status::bad_request, req.version()};
    res.set(http::field::content_type, "text/plain");
    res.body() = why;
    return res;
}

http::response<http::string_body> not_found(const Request& req){
    http::response<http::string_body> res{http::status::not_found, req.version()};
    res.set(http::field::content_type, "text/plain");
    res.body() = "The resource '" + std::string(req.target()) + "' was not found.";
    return res;
}

http::response<http::string_body> redirect(const Request& req, std::string_view location){
    http::response<http::string_body> res{http::status::moved_permanently, req.version()};
    res.set(http::field::location, location);
    return res;
}

http::response<http::string_body> jsonResponse(const Request& req, std::string_view j){
    http::response<http::string_body> res{ http::status::ok, req.version() };
    res.set(http::field::content_type, "application/json");
    res.body() = j;
    return res;
}

http::response<http::string_body> textResponse(const Request& req, std::string_view text){
    http::response<http::string_body> res{ http::status::ok, req.version() };
    res.set(http::field::content_type, "text/plain");
    res.body() = text;
    return res;
}

http::response<http::string_body> server_error(const Request& req, std::string_view what){
    http::response<http::string_body> res{http::status::internal_server_error, req.version()};
    res.set(http::field::content_type, "text/plain");
    res.body() = "An error occurred: '" + std::string(what) + "'";
    return res;
}

// Return a reasonable mime type based on the extension of a file.
std::string_view mime_type(std::string_view path) {
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
