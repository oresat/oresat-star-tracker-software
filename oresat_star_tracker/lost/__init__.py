"""Minimal wrapper to LOST for generating databases"""

from .utils import find_cli

if not find_cli().exists():
    raise FileNotFoundError("LOST executable is missing. Did you compile it?")

from .wrapper import prepare_db_args, generate_db
from .types import TetraDbConfig, PyDbConfig

__all__ = ["prepare_db_args", "generate_db", "TetraDbConfig", "PyDbConfig"]
