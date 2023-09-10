#ifndef GAMEAWESOME_SERVER_H
#define GAMEAWESOME_SERVER_H

#ifdef __cplusplus
extern "C" {
#endif

struct GameAwesome_Server;

GameAwesome_Server* GameAwesome_Server_construct(const char* ipAddress, unsigned short port);
void GameAwesome_Server_destruct(GameAwesome_Server* server);
void GameAwesome_Server_start(GameAwesome_Server* server);
void GameAwesome_Server_stop(GameAwesome_Server* server);

#ifdef __cplusplus
}
#endif

#endif //GAMEAWESOME_SERVER_H
