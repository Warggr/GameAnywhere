# Source - https://stackoverflow.com/a/78056725
# Posted by Dev-iL, modified by community. See post 'Timeline' for change history
# Retrieved 2026-04-12, License - CC BY-SA 4.0
from pathlib import Path

from setuptools import setup

local_path: str = (Path(__file__).parent / "examples").as_uri()

setup(extras_require={"examples": f"game-anywhere-examples @ {local_path}"})
