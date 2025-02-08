from typing import Union

# Adapted from https://stackoverflow.com/a/76646986
Json = Union[None, int, str, bool, list["Json"], dict[str, "Json"]]
JsonSchema = Json
