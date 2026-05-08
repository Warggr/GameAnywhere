import asyncio
from http import HTTPStatus
from typing import TYPE_CHECKING

import aiohttp
import pytest
import pytest_asyncio

from game_anywhere.network.server import Server

if TYPE_CHECKING:
    from aiohttp.test_utils import TestClient

    from game_anywhere.network.room import ServerRoom


# This needs the asyncio current event loop,
# therefore both the fixture and the function have to be async.
@pytest_asyncio.fixture
async def server():
    server = Server()
    server.loop = asyncio.get_event_loop()
    return server


@pytest_asyncio.fixture
async def client(server, aiohttp_client) -> TestClient:
    client = await aiohttp_client(server.app)
    return client


@pytest_asyncio.fixture
async def room_with_id(server) -> tuple[int, ServerRoom]:
    return server.new_room()


async def connect_to_room(
    client, room_id, seat_id, username: str | None = None, *, logged_in: bool = False
):
    params = {}
    client.session.cookie_jar.clear()
    if logged_in:
        client.session.cookie_jar.update_cookies({"username": username})
    elif username is not None:
        params["username"] = username

    connection = client.ws_connect(f"/r/{room_id}/ws/{seat_id}", params=params)
    async with connection:
        # This is necessary so the __aexit__ gets called and the connection is closed properly
        pass


@pytest.mark.asyncio
async def test_can_connect_to_session(client, room_with_id):
    seat_id = 0
    room_id, room = room_with_id
    room.create_session(seat_id=seat_id)
    await connect_to_room(client, room_id=room_id, seat_id=seat_id)


@pytest.mark.asyncio
async def test_can_reconnect_to_session(client, room_with_id):
    seat_id = 0
    room_id, room = room_with_id
    room.create_session(seat_id=seat_id)
    for _ in range(3):
        await connect_to_room(client, room_id=room_id, seat_id=seat_id)


@pytest.mark.asyncio
async def test_connecting_with_username_reserves_session(client, room_with_id):
    room_id, room = room_with_id
    seat_id = 0
    room.create_session(seat_id=seat_id)
    await connect_to_room(
        client, room_id=room_id, seat_id=seat_id, username="User 1", logged_in=True
    )

    with pytest.raises(aiohttp.WSServerHandshakeError) as e_info:
        await connect_to_room(
            client, room_id=room_id, seat_id=seat_id, username="User 2"
        )
    assert e_info.value.status in (HTTPStatus.FORBIDDEN, HTTPStatus.UNAUTHORIZED)

    with pytest.raises(aiohttp.WSServerHandshakeError) as e_info:
        await connect_to_room(
            client, room_id=room_id, seat_id=seat_id, username="User 2", logged_in=True
        )
    assert e_info.value.status in (HTTPStatus.FORBIDDEN, HTTPStatus.UNAUTHORIZED)


@pytest.mark.asyncio
async def test_connecting_as_guest_does_not_reserve_session(client, room_with_id):
    room_id, room = room_with_id
    seat_id = 0
    room.create_session(seat_id=seat_id)
    await connect_to_room(client, room_id=room_id, seat_id=seat_id, username="Guest 1")

    await connect_to_room(client, room_id=room_id, seat_id=seat_id, username="Guest 2")
    await connect_to_room(client, room_id=room_id, seat_id=seat_id, username="Guest 1")

    await connect_to_room(
        client, room_id=room_id, seat_id=seat_id, username="User 3", logged_in=True
    )
