import logging

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel

from core.config_manager import ConfigManager
from core.main_window import MainWindow
from core.plugin_interface import PluginInterface


class GoodPlugin(PluginInterface):
    def get_id(self):
        return "good"

    def get_name(self):
        return "正常插件"

    def get_icon(self):
        return "✅"

    def get_widget(self, parent):
        return QLabel("正常页面", parent)


class BrokenWidgetPlugin(PluginInterface):
    def get_id(self):
        return "broken"

    def get_name(self):
        return "故障插件"

    def get_icon(self):
        return "❌"

    def get_widget(self, parent):
        raise RuntimeError("widget failed")


class FakePluginManager:
    def __init__(self, plugins):
        self.plugins = plugins

    def get_plugins(self):
        return self.plugins

    def get_plugin(self, plugin_id):
        return self.plugins.get(plugin_id)

    def unload_all(self):
        pass


def test_main_window_skips_plugin_when_widget_creation_fails(qapp, tmp_path, caplog):
    config = ConfigManager(str(tmp_path / "config.json"))
    manager = FakePluginManager({"good": GoodPlugin(), "broken": BrokenWidgetPlugin()})

    with caplog.at_level(logging.ERROR):
        window = MainWindow(config_manager=config, plugin_manager=manager)

    assert window.nav_list.count() == 1
    assert window.nav_list.item(0).data(Qt.ItemDataRole.UserRole) == "good"
    assert window.logo_label.text() == "ToolX"
    assert not window.logo_icon.pixmap().isNull()
    assert not window.windowIcon().isNull()
    assert "插件页面创建失败" in caplog.text
    window.close()
