import pytest

from db_name_to_idx_mapper import DbNameToIdxMapper


@pytest.fixture
def config_file(tmp_path):
    return str(tmp_path / "mapper" / "config.json")


@pytest.fixture
def mapper(config_file):
    return DbNameToIdxMapper(config_file=config_file)
