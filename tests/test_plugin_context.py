import json

import pytest

from core.app_paths import PluginPaths
from core.config_manager import ConfigManager
from core.plugin_context import PluginContext, ScopedPluginConfig


def test_plugin_context_config_and_storage_are_isolated(tmp_path):
    paths = PluginPaths(tmp_path)
    context_a = PluginContext.create("plugin_a", paths)
    context_b = PluginContext.create("plugin_b", paths)

    context_a.config.set("private", {"value": 1})
    context_a.storage.write_json("data.json", {"owner": "a"})

    assert context_a.config.get("private") == {"value": 1}
    assert context_b.config.get("private") is None
    assert context_b.storage.read_json("data.json") is None
    assert context_a.config.file_path != context_b.config.file_path
    assert context_a.storage.data_dir() != context_b.storage.data_dir()
    assert not hasattr(context_a.services, "app_settings")

    with pytest.raises(ValueError):
        context_a.storage.write_json("../other.json", {})


def test_legacy_worklog_setting_moves_to_plugin_config(tmp_path):
    config_path = tmp_path / "toolx_config.json"
    config_path.write_text(
        json.dumps(
            {
                "window_size": [800, 500],
                "worklog_lunch_break": {"start_time": "12:15", "end_time": "13:45"},
            }
        ),
        encoding="utf-8",
    )

    app_settings = ConfigManager(str(config_path))
    plugin_config = ScopedPluginConfig("worklog", app_settings.paths)

    assert "worklog_lunch_break" not in app_settings.config
    assert plugin_config.get("worklog_lunch_break") == {
        "start_time": "12:15",
        "end_time": "13:45",
    }

