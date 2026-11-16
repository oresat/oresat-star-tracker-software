"""Minimal wrapper to LOST for generating databases"""

from .utils import find_cli

if not find_cli().exists():
    raise FileNotFoundError("LOST executable is missing. Did you compile it?")

from .types import PyDbConfig, TetraDbConfig
from .wrapper import generate_db, prepare_db_args

__all__ = ["PyDbConfig", "TetraDbConfig", "generate_db", "prepare_db_args"]
