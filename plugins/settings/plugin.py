"""Compatibility shim for the pre-1.0 settings plugin.

The plugin manager intentionally skips this directory. The real settings
page lives under ``core.settings`` and is always available as a system page.
"""

from PyQt6.QtWidgets import QWidget

from core.plugin_interface import PluginInterface
from core.settings.settings_widget import SettingsWidget


class SettingsPlugin(PluginInterface):
    def get_id(self) -> str:
        return "sys_settings"

    def get_name(self) -> str:
        return "设置"

    def get_icon(self):
        return "⚙️"

    def get_widget(self, parent: QWidget) -> QWidget:
        return SettingsWidget(self.context, parent)


def get_plugin(context):
    return SettingsPlugin(context)
