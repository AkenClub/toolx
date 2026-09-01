"""Compatibility shim for the old about plugin.

About is now a core settings page and is not scanned as an ordinary plugin.
"""

from PyQt6.QtWidgets import QWidget

from core.plugin_interface import PluginInterface
from core.settings.pages.about import AboutPage


AboutWidget = AboutPage


class AboutPlugin(PluginInterface):
    def get_id(self) -> str:
        return "sys_about"

    def get_name(self) -> str:
        return "关于"

    def get_icon(self):
        return "ℹ️"

    def get_widget(self, parent: QWidget) -> QWidget:
        return AboutPage(None, parent)


def get_plugin(context):
    return AboutPlugin(context)
