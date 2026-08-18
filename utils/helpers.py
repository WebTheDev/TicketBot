import tomllib
from pathlib import Path


def get_project_version() -> str:
    pyproject_path = Path(__file__).resolve().parent.parent / "pyproject.toml"
    with pyproject_path.open("rb") as pyproject_file:
        pyproject = tomllib.load(pyproject_file)
    return pyproject["project"]["version"]
