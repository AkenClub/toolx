"""Compatibility exports for centralized plugin paths."""

from .app_paths import (
    PluginPaths,
    get_installed_plugins_dir,
    get_logs_dir,
    get_plugin_config_file,
    get_plugin_data_dir,
    get_plugin_registry_file,
    validate_plugin_id,
)

__all__ = [
    "PluginPaths",
    "get_installed_plugins_dir",
    "get_logs_dir",
    "get_plugin_config_file",
    "get_plugin_data_dir",
    "get_plugin_registry_file",
    "validate_plugin_id",
]
