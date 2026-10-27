#!/usr/bin/env python3
"""
Database name to index mapper - core library

Writers serialise on an exclusive lock on ``<config>.lock`` and replace the config file atomically,
so concurrent processes never assign one index twice and readers never see a partly written file.
"""

import json
import os
import time

from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, NamedTuple, Optional

from db_name_to_idx_mapper.config_path import get_default_config_path


class MappingResult(NamedTuple):
    created: bool
    index: int


@contextmanager
def _exclusive_lock(lock_path: str) -> Iterator[None]:
    """Hold an exclusive inter-process lock on lock_path for the duration of the block"""
    with open(lock_path, "a+b") as f:
        if os.name == "nt":
            import msvcrt

            f.seek(0)
            while True:
                try:
                    msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
                    break
                except OSError:  # LK_LOCK gives up after ~10 s
                    pass
            try:
                yield
            finally:
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def _replace(src: str, dst: str):
    """os.replace, retried on Windows while a reader has dst open"""
    for _ in range(100):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if os.name != "nt":
                raise
            time.sleep(0.01)
    os.replace(src, dst)


class DbNameToIdxMapper:
    def __init__(self, config_file: Optional[str] = None):
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
        """Write configuration atomically, keeping the existing file's permissions"""
        tmp_file = f"{self.config_file}.{os.getpid()}.tmp"
        try:
            with open(tmp_file, "w") as f:
                json.dump(config, f, indent=2, sort_keys=True)
                f.flush()
                os.fsync(f.fileno())
            if os.path.exists(self.config_file):
                os.chmod(tmp_file, os.stat(self.config_file).st_mode)
            _replace(tmp_file, self.config_file)
        finally:
            if os.path.exists(tmp_file):
                os.remove(tmp_file)

    @contextmanager
    def _modify_config(self) -> Iterator[Dict]:
        """Load the config under the write lock and save it when the block exits without an exception"""
        with _exclusive_lock(f"{self.config_file}.lock"):
            config = self._load_config()
            yield config
            self._save_config(config)

    def add_mapping(self, name: str) -> int:
        """Add new mapping, raise ValueError if it exists"""
        with self._modify_config() as config:
            if name in config["mappings"]:
                raise ValueError(f"Mapping '{name}' already exists")

            next_index = max(config["mappings"].values(), default=-1) + 1
            config["mappings"][name] = next_index

        return next_index

    def ensure_mapping(self, name: str) -> MappingResult:
        """Ensure mapping exists, return existing or create new"""
        mappings = self._load_config()["mappings"]
        if name in mappings:
            return MappingResult(False, mappings[name])

        with self._modify_config() as config:
            if name in config["mappings"]:  # created by another process since the unlocked read
                return MappingResult(False, config["mappings"][name])

            next_index = max(config["mappings"].values(), default=-1) + 1
            config["mappings"][name] = next_index

        return MappingResult(True, next_index)

    def map(self, name: str) -> int:
        """Map name to index, raise KeyError if not found"""
        config = self._load_config()

        if name not in config["mappings"]:
            raise KeyError(f"Mapping '{name}' not found")

        return config["mappings"][name]

    def list_mappings(self, prefix: Optional[str] = None) -> List[Dict[str, Any]]:
        """List mappings sorted by name, optionally only those whose name starts with ``prefix + "."``"""
        config = self._load_config()
        mappings = config["mappings"]

        if prefix is not None:
            prefix_filter = f"{prefix}."
            mappings = {name: idx for name, idx in mappings.items() if name.startswith(prefix_filter)}

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
        with self._modify_config() as config:
            config["utilities"][utility_name] = param_name

    def get_utility_db_param(self, utility_name: str) -> str:
        """Get utility parameter name, "-n" if the utility has no mapping"""
        config = self._load_config()
        return config["utilities"].get(utility_name, "-n")
