from importlib.metadata import version

__title__ = "DB name to idx mapper"
__version__ = version("db-name-to-idx-mapper")
__author__ = "Jure Erznožnik"
__email__ = "jure.erznoznik@gmail.com"
__license__ = "MIT"
__copyright__ = "Copyright 2025-present Jure Erznožnik"

VERSION = __version__

from .cli import main  # noqa: E402
from .config_path import get_default_config_path, get_help_text, get_system_paths, resolve_config_path  # noqa: E402
from .db_name_to_idx_mapper import DbNameToIdxMapper, MappingResult  # noqa: E402

__all__ = [
    "DbNameToIdxMapper",
    "MappingResult",
    "get_default_config_path",
    "get_help_text",
    "get_system_paths",
    "main",
    "resolve_config_path",
]
