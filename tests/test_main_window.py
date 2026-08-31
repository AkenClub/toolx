import logging

from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QLabel

from core.config_manager import ConfigManager
from core.main_window import MainWindow
from core.plugin_interface import PluginInterface
from plugins.about.plugin import AboutPlugin


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


class NamedPlugin(PluginInterface):
    def __init__(self, plugin_id, name):
        super().__init__()
        self.plugin_id = plugin_id
        self.name = name

    def get_id(self):
        return self.plugin_id

    def get_name(self):
        return self.name

    def get_icon(self):
        return "•"

    def get_widget(self, parent):
        return QLabel(self.name, parent)


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
    assert not window.windowIcon().isNull()
    assert window.btn_toggle.height() == 44
    assert "插件页面创建失败" in caplog.text
    window.close()


def test_sidebar_separates_system_navigation_and_keeps_footer(qapp, tmp_path):
    config = ConfigManager(str(tmp_path / "config.json"))
    manager = FakePluginManager({
        "regular_b": NamedPlugin("regular_b", "普通插件 B"),
        "sys_about": NamedPlugin("sys_about", "关于"),
        "sys_settings": NamedPlugin("sys_settings", "系统设置"),
        "regular_a": NamedPlugin("regular_a", "普通插件 A"),
    })

    window = MainWindow(config_manager=config, plugin_manager=manager)

    assert [
        window.nav_list.item(index).data(Qt.ItemDataRole.UserRole)
        for index in range(window.nav_list.count())
    ] == ["regular_b", "regular_a"]
    assert [
        window.system_nav_list.item(index).data(Qt.ItemDataRole.UserRole)
        for index in range(window.system_nav_list.count())
    ] == ["sys_settings", "sys_about"]
    assert window.nav_list.sizePolicy().verticalPolicy().name == "Expanding"
    assert window.system_nav_list.sizePolicy().verticalPolicy().name == "Fixed"
    assert not hasattr(window, "logo_container")
    assert not hasattr(window, "logo_icon")
    assert not hasattr(window, "logo_label")

    window.show()
    qapp.processEvents()
    assert window.btn_toggle.height() == 44
    assert window.btn_toggle.width() >= 44
    window.nav_list.setCurrentRow(0)
    assert window.system_nav_list.currentRow() == -1
    window.system_nav_list.setCurrentRow(0)
    assert window.nav_list.currentRow() == -1

    window.toggle_sidebar()
    qapp.processEvents()
    assert window.sidebar.width() == MainWindow.SIDEBAR_COLLAPSED_WIDTH
    assert window.btn_toggle.text() == "›"
    assert window.btn_toggle.height() == 44
    assert window.btn_toggle.width() >= 36

    QTest.mouseClick(window.btn_toggle, Qt.MouseButton.LeftButton)
    assert window.sidebar.width() == MainWindow.SIDEBAR_EXPANDED_WIDTH

    QTest.mouseClick(window.btn_toggle, Qt.MouseButton.LeftButton)
    assert window.sidebar.width() == MainWindow.SIDEBAR_COLLAPSED_WIDTH

    window.toggle_sidebar()
    assert window.sidebar.width() == MainWindow.SIDEBAR_EXPANDED_WIDTH
    assert window.btn_toggle.text() == "‹"
    window.close()


def test_about_plugin_uses_short_navigation_name():
    assert AboutPlugin().get_name() == "关于"


def test_about_plugin_displays_application_logo(qapp):
    widget = AboutPlugin().get_widget(None)

    logo = widget.findChild(QLabel, "Logo")
    title = widget.findChild(QLabel, "Title")

    assert logo is not None
    assert logo.pixmap() is not None
    assert not logo.pixmap().isNull()
    assert title is not None
    assert title.text() == "ToolX"
