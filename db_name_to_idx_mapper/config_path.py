#!/usr/bin/env python3
"""
Config path resolver with cross-platform aliases
"""
import os
import tempfile
import platform


def get_system_paths():
    """Get system-specific paths for temp and config directories"""
    system = platform.system()

    if system == "Windows":
        temp_dir = os.environ.get("TEMP", tempfile.gettempdir())
        config_dir = os.environ.get(
            "APPDATA", os.path.expanduser("~\\AppData\\Roaming")
        )
    elif system == "Darwin":  # macOS
        temp_dir = tempfile.gettempdir()
        config_dir = os.path.expanduser("~/Library/Application Support")
    else:  # Linux and other Unix-like
        temp_dir = tempfile.gettempdir()
        config_dir = "/etc"

    return temp_dir, config_dir


def get_default_config_path():
    """Get default config path for the application"""
    _, config_dir = get_system_paths()
    return os.path.join(config_dir, "db-name-to-idx-mapper", "config.json")


def resolve_config_path(path_with_aliases):
    """
    Resolve config path with system aliases

    Supported aliases:
    - {TEMP}: system temporary directory
    - {CONFIG}: system configuration directory

    Examples:
        {TEMP}/my-config.json -> /tmp/my-config.json (Linux)
        {CONFIG}/db-name-to-idx-mapper/config.json -> /etc/db-name-to-idx-mapper/config.json (Linux)
    """
    temp_dir, config_dir = get_system_paths()

    resolved_path = path_with_aliases
    resolved_path = resolved_path.replace("{TEMP}", temp_dir)
    resolved_path = resolved_path.replace("{CONFIG}", config_dir)

    return resolved_path


def get_help_text():
    """Generate help text with resolved examples for current platform"""
    temp_dir, config_dir = get_system_paths()

    temp_example = os.path.join(temp_dir, "db-name-to-idx-mapper", "config.json")
    config_example = os.path.join(config_dir, "db-name-to-idx-mapper", "config.json")

    help_text = f"""Path to config file (default: {config_example})
    
    Use aliases to get system paths:
    * {{TEMP}}: temporary directory, e.g. {temp_example}
    * {{CONFIG}}: app configuration directory, e.g. {config_example}
    """.replace("\n    ", "\n")

    return help_text

