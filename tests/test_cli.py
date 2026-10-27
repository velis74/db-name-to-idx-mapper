import pytest

from db_name_to_idx_mapper import main
from db_name_to_idx_mapper.cli import build_exec_commands


@pytest.fixture
def mapped(mapper):
    mapper.ensure_mapping("app.cache")
    mapper.ensure_mapping("app.sessions")
    mapper.ensure_mapping("other")
    return mapper


def test_exec_maps_exact_name(mapped):
    assert build_exec_commands(mapped, "redis-cli", ["-n", "app.cache", "GET", "k"]) == [
        ["redis-cli", "-n", "0", "GET", "k"]
    ]


def test_exec_runs_once_per_prefix_match(mapped):
    assert build_exec_commands(mapped, "redis-cli", ["-h", "host", "-n", "app", "KEYS", "*"]) == [
        ["redis-cli", "-h", "host", "-n", "0", "KEYS", "*"],
        ["redis-cli", "-h", "host", "-n", "1", "KEYS", "*"],
    ]


def test_exec_passes_unknown_value_and_missing_param_through(mapped):
    assert build_exec_commands(mapped, "redis-cli", ["-n", "5", "PING"]) == [["redis-cli", "-n", "5", "PING"]]
    assert build_exec_commands(mapped, "redis-cli", ["PING"]) == [["redis-cli", "PING"]]
    assert build_exec_commands(mapped, "redis-cli", ["-n"]) == [["redis-cli", "-n"]]


def test_exec_uses_utility_param(mapped):
    mapped.add_utility_db_param_map("tool", "--db")
    assert build_exec_commands(mapped, "tool", ["-n", "x", "--db", "other"]) == [["tool", "-n", "x", "--db", "2"]]


def run_cli(monkeypatch, config_file, *args):
    monkeypatch.setattr("sys.argv", ["db-name-to-idx-mapper", "--config-path", config_file, *args])
    with pytest.raises(SystemExit) as exc:
        main()
        raise SystemExit(0)
    return exc.value.code


def test_cli_commands(monkeypatch, capsys, config_file):
    assert run_cli(monkeypatch, config_file, "ensure-mapping", "app.cache") == 0
    assert run_cli(monkeypatch, config_file, "add-mapping", "app.sessions") == 0
    assert run_cli(monkeypatch, config_file, "map", "app.sessions") == 0
    assert run_cli(monkeypatch, config_file, "list-mappings", "app") == 0
    assert run_cli(monkeypatch, config_file, "get-max-index") == 0
    assert capsys.readouterr().out.split() == ["0", "1", "1", "app.cache:0", "app.sessions:1", "1"]

    assert run_cli(monkeypatch, config_file, "map", "missing") == 1
    assert "not found" in capsys.readouterr().err


def test_cli_exec_returns_utility_exit_code(monkeypatch, config_file):
    import sys

    assert run_cli(monkeypatch, config_file, "exec", sys.executable, "-c", "raise SystemExit(3)") == 3
    assert run_cli(monkeypatch, config_file, "exec", sys.executable, "-c", "pass") == 0
