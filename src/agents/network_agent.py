from game_anywhere.include.core import Agent
from .descriptors import AgentDescriptor
from ..network import Server, ServerRoom

class NetworkAgent(Agent):
    class Descriptor(AgentDescriptor):
        def start_initialization(self, id : 'AgentId', context):
            if 'server_room' not in context:
                if Server._instance is None:
                    server = Server.create_instance()
                    context['exit_stack'].enter_context(server)
                else:
                    server = Server._instance
                room = server.new_room()
                context['server_room'] = room
                # context['exit_stack'].enter_context(room)
            else:
                room = context['server_room']
            session = room.create_session(id)
            return session

        def await_initialization(self, session):
            session.reconnect_sync()

    def __init__(self, session: 'Session'):
        self.session = session

    def message(self, message):
        self.session.send(message)

    def get_2D_choice(self, dimensions):
        return tuple( self.get_integer(min=0, max=dim-1) for dim in dimensions )
