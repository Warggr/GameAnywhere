from game_anywhere.include.core import Agent
from .descriptors import AgentDescriptor, Context
from ..network import Server, ServerRoom
from typing import List, Any

class NetworkAgent(Agent):
    class Descriptor(AgentDescriptor):
        def start_initialization(self, agent_id : 'AgentId', context : Context):
            if 'server_room' not in context:
                if Server._instance is None:
                    server = Server.create_instance()
                    context['exit_stack'].enter_context(server)
                else:
                    server = Server._instance
                _room_id, room = server.new_room()
                context['server_room'] = room
                # context['exit_stack'].enter_context(room)
            else:
                room = context['server_room']
            print('Creating session on room')
            session = room.create_session(agent_id)
            return session

        def await_initialization(self, session):
            session.reconnect_sync()
            return NetworkAgent(session)

    def __init__(self, session: 'Session'):
        self.session = session

    # override
    def message(self, message) -> None:
        self.session.send_sync(message)

    # override
    def update(self, diffs : List[Any]):
        def serialize_diff(diff):
            if True: # TODO multiple types of diffs
                component_to_replace : 'Component' = diff['replace']
                return { 'id': component_to_replace.id, 'newHTML': component_to_replace.html() }
            else:
                return diff
        self.session.send_sync( list(map(serialize_diff, diffs)) )

    # override
    def get_2D_choice(self, dimensions):
        return tuple( self.get_integer(min=0, max=dim-1) for dim in dimensions )

    # override
    def choose_one_component(self, components : List['Component']):
        self.session.send_sync({ 'type': 'choice', 'components': [ component.id for component in components ] })
        ids = { c.id : c for c in components }
        while True:
            chosen_id = self.session.get_sync()
            if chosen_id in ids:
                return ids[chosen_id]
            else:
                self.session.send_sync({ 'type': 'error', 'message': 'Invalid choice, please try again!' })

    def get_integer(self, min=None, max=None) -> int:
        while True:
            integer = self.session.get_sync()
            print("(game) parsing", repr(integer))
            try:
                assert integer.isdigit()
                integer = int(integer)
                if min is not None:
                    assert integer >= min, f"Please choose a number higher than {min}"
                if max is not None:
                    assert integer <= max, f"Please choose a number higher than {max}"
                return integer
            except (ValueError, AssertionError) as err:
                self.session.send_sync(repr(err))
                continue
