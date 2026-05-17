import random
from importlib.metadata import entry_points
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from game_anywhere.core import Game

examples = pytest.importorskip("game_anywhere_examples")

games = [
    ep.load()
    for ep in entry_points(group="game_anywhere.games")
    if ep.module.startswith("game_anywhere_examples")
]


def random_object(schema: dict, generator: random.Random):
    if "const" in schema:
        return schema["const"]
    elif "enum" in schema:
        return generator.choice(schema["enum"])
    if "anyOf" in schema:
        subschema = generator.choice(schema["anyOf"])
        return random_object(subschema, generator)
    if schema["type"] == "object":
        return {
            key: random_object(value, generator)
            for key, value in schema["properties"].items()
        }
    elif schema["type"] == "array":
        mini = schema.get("minItems", 0)
        maxi = schema.get("maxItems", mini + 10)
        items = schema.get("items", {"const": None})
        num = generator.randint(mini, maxi)
        return [random_object(items, generator) for _ in range(num)]
    elif schema["type"] == "integer":
        mini = schema.get("minimum", 0)
        maxi = schema.get("maximum", mini + 10)
        return generator.randint(mini, maxi)
    elif schema["type"] == "boolean":
        return generator.choice([True, False])
    raise ValueError("Don't know how to handle", schema)


@pytest.mark.parametrize("game_class", games)
def test_instantiate_game(game_class: type[Game]):
    generator = random.Random(0)
    schema = game_class.CONFIG_SCHEMA.copy()
    schema["type"] = "object"
    kwargs = random_object(schema, generator)
    num_agents, kwargs = game_class.parse_config(**kwargs)
    _ = game_class([None for _ in range(num_agents)], **kwargs)
