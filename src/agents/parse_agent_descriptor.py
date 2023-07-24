from typing import List
from .agent_descriptor import AgentDescriptor

from .local_agent import HumanAgent

def parse_agent_descriptions(args: List[str]) -> List[AgentDescriptor]:
    return [ HumanAgent.Descriptor(), HumanAgent.Descriptor() ]
