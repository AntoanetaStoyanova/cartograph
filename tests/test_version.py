import tomllib

from cartograph import __version__
from cartograph.config import PROJECT_ROOT


def test_version_matches_pyproject() -> None:
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as f:
        expected = tomllib.load(f)["project"]["version"]
    assert __version__ == expected
