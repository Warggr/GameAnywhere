import asyncio
import inspect
from typing import List
from game_anywhere.src.agents import parse_agent_descriptions
from .core.game import Game, GameSummary

def force_async(function):
    if inspect.isawaitable(function):
        return function
    else:
        async def _wrapper(*args, **kwargs):
            return function(*args, **kwargs)
        return _wrapper

def run_game(GameType : type[Game], args: List[str]) -> GameSummary:
    agent_descriptions = parse_agent_descriptions(args)

    agents = asyncio.get_event_loop().run_until_complete(
        asyncio.gather( *(force_async(description.initialize)() for description in agent_descriptions) )
    )

    game = GameType(agents)

    return game.play_game()
