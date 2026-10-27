from db_name_to_idx_mapper import get_system_paths, resolve_config_path


def test_aliases_resolve_to_system_paths():
    temp_dir, config_dir = get_system_paths()
    assert resolve_config_path("{TEMP}/a.json") == f"{temp_dir}/a.json"
    assert resolve_config_path("{CONFIG}/m/config.json") == f"{config_dir}/m/config.json"
    assert resolve_config_path("/plain/path.json") == "/plain/path.json"
