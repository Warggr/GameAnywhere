import asyncio
from game_anywhere.include.core.agent import Agent

class AgentDescriptor:
    async def initialize(self) -> Agent:
        raise NotImplementedError()
