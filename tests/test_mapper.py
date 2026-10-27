import json
import os
import subprocess
import sys

import pytest

from db_name_to_idx_mapper import DbNameToIdxMapper, MappingResult


def test_indices_are_sequential_from_zero(mapper):
    assert mapper.ensure_mapping("app.cache") == MappingResult(True, 0)
    assert mapper.ensure_mapping("app.sessions") == MappingResult(True, 1)
    assert mapper.ensure_mapping("app.cache") == MappingResult(False, 0)
    assert mapper.add_mapping("other") == 2


def test_add_mapping_rejects_existing(mapper):
    mapper.add_mapping("app.cache")
    with pytest.raises(ValueError):
        mapper.add_mapping("app.cache")


def test_map(mapper):
    mapper.ensure_mapping("app.cache")
    assert mapper.map("app.cache") == 0
    with pytest.raises(KeyError):
        mapper.map("missing")


def test_list_mappings_prefix_matches_dotted_children_only(mapper):
    for name in ("app.sessions", "app.cache", "app", "application.cache"):
        mapper.ensure_mapping(name)
    assert mapper.list_mappings("app") == [
        {"name": "app.cache", "index": 1},
        {"name": "app.sessions", "index": 0},
    ]
    assert [m["name"] for m in mapper.list_mappings()] == ["app", "app.cache", "app.sessions", "application.cache"]


def test_max_index(mapper):
    assert mapper.get_max_mapping_index() == -1
    mapper.ensure_mapping("a")
    mapper.ensure_mapping("b")
    assert mapper.get_max_mapping_index() == 1


def test_utility_db_param(mapper):
    assert mapper.get_utility_db_param("redis-cli") == "-n"
    mapper.add_utility_db_param_map("redis-benchmark", "--dbnum")
    assert mapper.get_utility_db_param("redis-benchmark") == "--dbnum"


def test_mappings_persist_across_instances(mapper, config_file):
    mapper.ensure_mapping("app.cache")
    assert DbNameToIdxMapper(config_file=config_file).map("app.cache") == 0
    with open(config_file) as f:
        assert json.load(f) == {"mappings": {"app.cache": 0}, "utilities": {}}


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits")
def test_save_keeps_file_permissions(mapper, config_file):
    mapper.ensure_mapping("a")
    os.chmod(config_file, 0o644)
    mapper.ensure_mapping("b")
    assert os.stat(config_file).st_mode & 0o777 == 0o644
    assert sorted(os.listdir(os.path.dirname(config_file))) == ["config.json", "config.json.lock"]


def test_concurrent_processes_get_distinct_indices(config_file):
    os.makedirs(os.path.dirname(config_file))
    script = (
        "import sys\n"
        "from db_name_to_idx_mapper import DbNameToIdxMapper\n"
        "m = DbNameToIdxMapper(config_file=sys.argv[1])\n"
        "for i in range(20):\n"
        "    m.ensure_mapping(f'{sys.argv[2]}.{i}')\n"
    )
    workers = [subprocess.Popen([sys.executable, "-c", script, config_file, f"w{n}"]) for n in range(6)]
    assert [w.wait() for w in workers] == [0] * 6

    indices = [m["index"] for m in DbNameToIdxMapper(config_file=config_file).list_mappings()]
    assert sorted(indices) == list(range(120))
