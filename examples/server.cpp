#include "network/server.hpp"

int main(int, char**) {
    GameAwesome::Server server("127.0.0.1", 3000);
    server.start();
}
