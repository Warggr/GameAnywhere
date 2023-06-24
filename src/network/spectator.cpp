// Adapted from https://github.com/vinniefalco/CppCon2018
// Copyright (c) 2018 Vinnie Falco (vinnie dot falco at gmail dot com)
// Distributed under the Boost Software License, Version 1.0. (See copy at http://www.boost.org/LICENSE_1_0.txt)

#include "spectator.hpp"
#include "room.hpp"
#include "control/agent.hpp"
#include <iostream>
#include <utility>

constexpr int NB_OUTSIDE_THREADS = 1;

Spectator::Spectator(ServerRoom& room, AgentId id)
: room(room), id(id){}

Spectator& Spectator::claim(tcp::socket &&socket) {
    ws = std::make_unique<websocket::stream<tcp::socket>>(std::move(socket));
    assert(state == FREE);
    state = CLAIMED;
    return *this;
}

Spectator::~Spectator(){
    assert(state == FREE or state == INTERRUPTED_BY_SERVER);
}

void Spectator::fail(error_code ec, char const* what){
    // Don't report these
    if( ec == net::error::operation_aborted ) return;
    std::cerr << what << ": " << ec.message() << "\n";
}

void Spectator::on_connect(error_code ec){
    std::cout << "(async spectator" << id << ") Accept WS handshake\n";
    if(ec){ // Handle the error, if any
        room.reportAfk(*this);
        return fail(ec, "accept");
    }
    assert(state == CLAIMED);
    protectReadingQueue.lock();
    state = CONNECTED;
    protectReadingQueue.unlock();
    signalReadingQueue.notify_one();

    room.onConnect(*this);

    //Starting the message reading loop
    ws->async_read(
        buffer,
        [sp=shared_from_this()](error_code ec, std::size_t bytes) {
            sp->on_read(ec, bytes);
        }
    );
}

void Spectator::send(std::shared_ptr<const std::string> message){
    std::cout << "(main) Sending message\n";
    bool queue_empty = writing_queue.empty();

    // Always add to queue
    writing_queue.push(message);

    if(state != CONNECTED) return;
    if(queue_empty) {
        // We are not currently writing, so send this immediately
        ws->async_write(
                net::buffer(*writing_queue.front()),
                [sp=shared_from_this()](error_code ec, std::size_t bytes) {
                    sp->on_write(ec, bytes);
                }
        );
    }
}

void Spectator::send_sync(std::shared_ptr<const std::string> message){
    net::post(ws->get_executor(),
        [&,message=std::move(message)]{ send(message); }
    );
}

void Spectator::on_write(error_code ec, std::size_t){
    std::cout << "(async spectator" << id << ") Message written\n";
    // Handle the error, if any
    if(ec) return fail(ec, "write");

    // Remove the string from the queue
    writing_queue.pop();

    // Send the next message if any
    if(! writing_queue.empty())
        ws->async_write(
            net::buffer(*writing_queue.front()),
            [sp=shared_from_this()](error_code ec, std::size_t bytes){
                sp->on_write(ec, bytes);
            });
}

// This is executed on the network thread, so the only possible race condition is with send() or get()
void Spectator::interrupt(){
    std::cout << "(async spectator" << id << ") connection interrupted\n";
    protectReadingQueue.lock();
    state = INTERRUPTED_BY_SERVER;
    protectReadingQueue.unlock();
    signalReadingQueue.notify_one(); //in case anyone was waiting for it
    if(ws and ws->is_open())
        ws->close(beast::websocket::close_reason());
}

void Spectator::on_read(error_code ec, std::size_t size) {
    if(not isConnected()) return;
    // Handle the error, if any
    if(ec == websocket::error::closed or size == 0){
        std::cout << "(async spectator" << id << ") received close, ask for disconnect\n";
        protectReadingQueue.lock();
        state = FREE;
        protectReadingQueue.unlock();
        signalReadingQueue.notify_one();
        room.reportAfk(*this);
        return;
    }
    if (ec) return fail(ec, "read");

    std::cout << "(async spectator" << id << ") Read message of size " << size << '\n';

    // Add to queue
    protectReadingQueue.lock();
    reading_queue.push(beast::buffers_to_string(buffer.data()));
    protectReadingQueue.unlock();
    signalReadingQueue.notify_one();

    // Clear the buffer
    buffer.consume(buffer.size());

    if(not listening) send("\"Not listening\"");

    // Read another message
    ws->async_read(
        buffer,
        [sp=shared_from_this()](error_code ec, std::size_t bytes) {
            sp->on_read(ec, bytes);
        }
    );
}

std::string Session::get_sync(){
    // There are two waiting states: connected (waiting for string...) and disconnected (waiting for connection...)
    // Each can transform into the other. For memory performance reasons, both use the same mutex / cv / semaphore.
    // Both will return quickly if their precondition isn't met.
    // Arbitrarily starting with the connected (wait for string...) state.
    std::cout << "(main) Getting string, waiting for mutex...\n";
    listening = true;
    {
connected:
        std::unique_lock<std::mutex> lock(protectReadingQueue);
        if(reading_queue.empty()){
            if(state != CONNECTED) goto disconnected; //"fail rapidly if the precondition isn't met"
            signalReadingQueue.wait(lock, [&] { return not reading_queue.empty() or state != CONNECTED; });
            if(state != CONNECTED) goto disconnected;
            assert(not reading_queue.empty());
        }

        listening = false; //okay, maybe a semaphore would've been cleaner
        std::string retVal = std::move(reading_queue.front());
        reading_queue.pop();
        return retVal;
    }
disconnected:
    awaitReconnect();
    goto connected;
}

void Session::awaitReconnect() {
    std::unique_lock<std::mutex> lock(protectReadingQueue);
    if(state == INTERRUPTED_BY_SERVER) throw DisconnectedException();
    if(state == CONNECTED) return; //exit rapidly if the precondition isn't met

    std::cout << "(sync session) Awaiting reconnect...\n";
    using namespace std::chrono_literals;
    if(signalReadingQueue.wait_for(lock, 3min) == std::cv_status::timeout) throw TimeoutException();
    std::cout << "(sync session) ...reconnect signal heard\n";

    if(state == INTERRUPTED_BY_SERVER) throw DisconnectedException();

    assert(state == CONNECTED);
    std::cout << "(sync session) reconnected!\n";
}
