from PyQt6.QtCore import Qt

from core.config_manager import ConfigManager
from core.main_window import MainWindow


class EmptyPluginManager:
    def get_plugins(self):
        return {}

    def get_plugin(self, _plugin_id):
        return None

    def unload_all(self):
        pass


def test_core_system_pages_are_available_without_feature_plugins(qapp, tmp_path):
    config = ConfigManager(str(tmp_path / "config.json"))
    window = MainWindow(config, EmptyPluginManager())

    assert window.nav_list.count() == 0
    assert [
        window.system_nav_list.item(index).data(Qt.ItemDataRole.UserRole)
        for index in range(window.system_nav_list.count())
    ] == ["sys_settings"]
    assert window.system_nav_list.item(0).text().endswith("设置")
    assert window.system_context.plugin_settings.list_pages() == []

    window.close()
