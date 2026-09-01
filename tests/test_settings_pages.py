from PyQt6.QtCore import QTime

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


def test_plugin_config_changes_refresh_runtime_and_settings_widgets(qapp, tmp_path):
    config = ConfigManager(str(tmp_path / "config.json"))
    manager = PluginManager(config, plugin_dir="plugins")
    manager.load_all_plugins()

    worklog_plugin = manager.get_plugin("worklog")
    worklog_widget = worklog_plugin.get_widget(None)
    settings = SettingsWidget(manager.get_system_context())
    worklog_settings = settings.get_page_widget("worklog", "general")

    worklog_settings.start_edit.setTime(QTime(12, 15))
    worklog_settings.end_edit.setTime(QTime(13, 45))
    assert settings.apply_changes() is True
    assert worklog_widget.lunch_start_edit.time().toString("HH:mm") == "12:15"
    assert worklog_widget.lunch_end_edit.time().toString("HH:mm") == "13:45"

    worklog_widget.lunch_start_edit.setTime(QTime(11, 45))
    assert worklog_settings.start_edit.time().toString("HH:mm") == "11:45"

    quick_copy_plugin = manager.get_plugin("quick_copy")
    quick_copy_widget = quick_copy_plugin.get_widget(None)
    quick_copy_settings = settings.get_page_widget("quick_copy", "general")

    quick_copy_settings.template_edit.setText("new_{{yyyy}}")
    assert settings.apply_changes() is True
    assert quick_copy_widget.filename_template_edit.text() == "new_{{yyyy}}"

    quick_copy_widget.filename_template_edit.setText("main_{{HH}}")
    quick_copy_widget.save_settings()
    assert quick_copy_settings.template_edit.text() == "main_{{HH}}"

    settings.close()
    manager.unload_all()
