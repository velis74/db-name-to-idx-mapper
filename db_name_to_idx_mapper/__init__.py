__title__ = "DB name to idx mapper"
__version__ = "1.0.3-alpha"
__author__ = "Velis d.o.o."
__email__ = "support@velis.si"
__license__ = "MIT"
__copyright__ = "Copyright 2025-present Velis d.o.o."

VERSION = __version__

from .config_path import resolve_config_path, get_help_text, get_default_config_path, get_system_paths
from .db_name_to_idx_mapper import DbNameToIdxMapper
from .cli import main
