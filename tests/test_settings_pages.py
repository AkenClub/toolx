from core.config_manager import ConfigManager
from core.plugin_manager import PluginManager
from core.settings.settings_widget import SettingsWidget


def test_plugin_settings_are_contributed_to_core_settings_center(qapp, tmp_path):
    config = ConfigManager(str(tmp_path / "config.json"))
    manager = PluginManager(config, plugin_dir="plugins")
    manager.load_all_plugins()

    pages = manager.get_system_context().plugin_settings.list_pages()
    assert {(page.plugin_id, page.page_id) for page in pages} == {
        ("quick_copy", "general"),
        ("worklog", "general"),
    }

    settings = SettingsWidget(manager.get_system_context())
    assert settings.get_page_widget("quick_copy", "general") is not None
    assert settings.get_page_widget("worklog", "general") is not None
    assert settings.settings_tree.topLevelItemCount() == 3
    settings.close()
    manager.unload_all()
