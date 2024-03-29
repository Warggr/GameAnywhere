from game_anywhere.include.core import Agent
from .descriptors import AgentDescriptor, Context
from ..network import Server, ServerRoom
from ..network.spectator import Session
from typing import List, Any, TypeVar, Callable

T = TypeVar('T')

class NetworkAgent(Agent):
    class Descriptor(AgentDescriptor):
        def start_initialization(self, agent_id : 'AgentId', context : Context):
            if 'server_room' not in context:
                if Server._instance is None:
                    server = Server()
                    context['server'] = server
                    context['exit_stack'].enter_context(server)
                else:
                    server = context['server']
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

    def __init__(self, session: Session):
        self.session = session

    # override
    def message(self, message) -> None:
        self.session.send_sync(message)

    # override
    def update(self, diffs : List[Any]):
        def serialize_diff(diff):
            if True: # TODO multiple types of diffs
                return {
                    'id': diff['id'],
                    'newHTML': str(diff['new_value'].html()) if diff['new_value'] is not None else ''
                }
            else:
                return diff
        self.session.send_sync( list(map(serialize_diff, diffs)) )

    # override
    def get_2D_choice(self, dimensions):
        return tuple( self.int_choice(min=0, max=dim-1) for dim in dimensions )

    def choose_one_component_slot(self, components : List['Component'], indices : List[T]) -> T:
        return self.choose_one(components, indices)

    class InvalidAnswer(Exception):
        def __init__(self, message):
            super().__init__()
            self.message = message

    # override
    def choose_one(self, components : List['Component'], indices : List[T], special_options=[]) -> T:
        question = { 'type': 'choice', 'components': [ component.id for component in components ], 'special_options': special_options }
        ids = { components[i].id : indices[i] for i in range(len(components)) }
        def _validation(answer : str):
            if answer in ids:
                return ids[answer]
            elif answer in special_options:
                return answer
            else:
                raise NetworkAgent.InvalidAnswer('Invalid choice, please try again!')
        return self.question_with_validation(question, _validation)

    # override
    def int_choice(self, min: int|None = 0, max: int|None = None) -> int:
        jsonSchema = { 'type': 'integer' }
        if min is not None:
            jsonSchema['minimum'] = min
        if max is not None:
            jsonSchema['maximum'] = max

        def _validation(answer : str):
            try:
                assert answer.isdigit()
                integer = int(answer)
                if min is not None:
                    assert integer >= min, f"Please choose a number higher than {min}"
                if max is not None:
                    assert integer <= max, f"Please choose a number higher than {max}"
                return integer
            except (ValueError, AssertionError) as err:
                raise NetworkAgent.InvalidAnswer(repr(err))
        return self.question_with_validation({ 'type': 'choice', 'schema': jsonSchema }, _validation)

    # override
    def text_choice(self, options: List[str]) -> str:
        jsonSchema = { 'type': 'string', 'enum': options }
        def _validation(answer : str):
            if answer not in options:
                raise NetworkAgent.InvalidAnswer(f'value {answer} not allowed')
            return answer
        return self.question_with_validation({ 'type': 'choice', 'schema': jsonSchema }, _validation)

    def question_with_validation(self, question : Any, validation : Callable[str, T]) -> T:
        while True:
            print('(network agent) sending question')
            self.session.send_sync(question)
            answer = self.session.get_sync()
            if answer == Session.CLIENT_LOST_TRACK_MESSAGE:
                continue # goto beginning_of_while_loop # resend question
            try:
                answer = validation(answer)
            except NetworkAgent.InvalidAnswer as err:
                self.session.send_sync({ 'type': 'error', 'message': err.message })
                continue # goto beginning_of_while_loop
            return answer
