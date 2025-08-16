#!/usr/bin/env python3
"""
Database name to index mapper - core library
"""

import json
import os
from typing import Dict, List, Optional, NamedTuple
from db_name_to_idx_mapper.config_path import get_default_config_path


class MappingResult(NamedTuple):
    created: bool
    index: int

class DbNameToIdxMapper:
    def __init__(self, config_file: str = None):
        if config_file is None:
            config_file = get_default_config_path()

        self.config_file = config_file
        self._ensure_config_dir()

    def _ensure_config_dir(self):
        """Ensure config directory exists"""
        config_dir = os.path.dirname(self.config_file)
        os.makedirs(config_dir, exist_ok=True)

    def _load_config(self) -> Dict:
        """Load configuration from file"""
        if not os.path.exists(self.config_file):
            return {"mappings": {}, "utilities": {}}

        with open(self.config_file, "r") as f:
            return json.load(f)

    def _save_config(self, config: Dict):
        """Save configuration to file"""
        with open(self.config_file, "w") as f:
            json.dump(config, f, indent=2, sort_keys=True)

    def add_mapping(self, name: str) -> int:
        """Add new mapping, raise exception if exists"""
        config = self._load_config()

        if name in config["mappings"]:
            raise ValueError(f"Mapping '{name}' already exists")

        # Find next available index
        existing_indices = list(config["mappings"].values())
        next_index = max(existing_indices, default=-1) + 1

        config["mappings"][name] = next_index
        self._save_config(config)

        return next_index

    def ensure_mapping(self, name: str) -> MappingResult:
        """Ensure mapping exists, return existing or create new"""
        config = self._load_config()

        if name in config["mappings"]:
            return MappingResult(False, config["mappings"][name])

        # Create new mapping
        existing_indices = list(config["mappings"].values())
        next_index = max(existing_indices, default=-1) + 1

        config["mappings"][name] = next_index
        self._save_config(config)

        return MappingResult(True, next_index)

    def map(self, name: str) -> int:
        """Map name to index, raise exception if not found"""
        config = self._load_config()

        if name not in config["mappings"]:
            raise KeyError(f"Mapping '{name}' not found")

        return config["mappings"][name]

    def list_mappings(self, prefix: Optional[str] = None) -> List[Dict[str, any]]:
        """List mappings, optionally filtered by prefix"""
        config = self._load_config()
        mappings = config["mappings"]

        if prefix is not None:
            # Filter by prefix + "."
            prefix_filter = f"{prefix}."
            mappings = {
                name: idx
                for name, idx in mappings.items()
                if name.startswith(prefix_filter)
            }

        # Return sorted list of dicts
        return [{"name": name, "index": idx} for name, idx in sorted(mappings.items())]

    def get_max_mapping_index(self) -> int:
        """Get highest mapping index, return -1 if no mappings exist"""
        config = self._load_config()
        mappings = config["mappings"]

        if not mappings:
            return -1

        return max(mappings.values())

    def add_utility_db_param_map(self, utility_name: str, param_name: str):
        """Add utility parameter mapping"""
        config = self._load_config()
        config["utilities"][utility_name] = param_name
        self._save_config(config)

    def get_utility_db_param(self, utility_name: str) -> str:
        """Get utility parameter name, raise exception if not found"""
        config = self._load_config()

        if utility_name not in config["utilities"]:
            return "-n"

        return config["utilities"][utility_name]
