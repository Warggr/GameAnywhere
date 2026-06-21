# Source - https://stackoverflow.com/a/78056725
# Posted by Dev-iL, modified by community. See post 'Timeline' for change history
# Retrieved 2026-04-12, License - CC BY-SA 4.0
import subprocess
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py


class BuildFrontend(build_py):
    def run(self):
        frontend = Path("game_anywhere/client")

        subprocess.check_call(["npm", "ci"], cwd=frontend)
        subprocess.check_call(["npm", "run", "build-only"], cwd=frontend)

        super().run()


local_path: str = (Path(__file__).parent / "examples").as_uri()

setup(
    cmdclass={"build_py": BuildFrontend},
    extras_require={
        "examples": f"game-anywhere-examples @ {local_path}",
        "testing": ["pytest", "pytest-asyncio", "pytest-aiohttp"],
    },
)
