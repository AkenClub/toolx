"""Services that expose plugin-contributed settings pages to core UI."""

import logging

from core.config_manager import AppSettingsService
from core.plugin_admin import PluginAdminService
from core.plugin_interface import SettingsPage


logger = logging.getLogger(__name__)


class PluginSettingsService:
    """Discover settings pages without exposing plugin manager to plugins."""

    def __init__(self, plugin_manager=None):
        self.plugin_manager = plugin_manager

    def list_pages(self):
        if self.plugin_manager is None:
            return []
        pages = []
        for plugin_id, plugin in self.plugin_manager.get_plugins().items():
            try:
                contributed = plugin.get_settings_pages() or []
            except Exception:
                logger.exception("读取插件 %s 的设置页失败", plugin_id)
                continue
            for page in contributed:
                if not isinstance(page, SettingsPage):
                    logger.warning("插件 %s 返回了无效设置页，已跳过", plugin_id)
                    continue
                if not page.plugin_id:
                    page.plugin_id = plugin_id
                if not page.path:
                    page.path = ("插件", plugin.get_name())
                pages.append(page)
        return pages

    def get_page(self, plugin_id, page_id):
        for page in self.list_pages():
            if page.plugin_id == plugin_id and page.page_id == page_id:
                return page
        return None

    def create_widget(self, plugin_id, page_id, parent=None):
        page = self.get_page(plugin_id, page_id)
        if page is None:
            raise KeyError("设置页不存在: %s/%s" % (plugin_id, page_id))
        return page.create_widget(parent)

    open_page = create_widget

    def apply(self, plugin_id, page_id, widget):
        page = self.get_page(plugin_id, page_id)
        if page is None:
            raise KeyError("设置页不存在: %s/%s" % (plugin_id, page_id))
        apply_method = getattr(widget, "apply", None)
        return True if not callable(apply_method) else apply_method()

    def reset(self, plugin_id, page_id, widget):
        page = self.get_page(plugin_id, page_id)
        if page is None:
            raise KeyError("设置页不存在: %s/%s" % (plugin_id, page_id))
        reset_method = getattr(widget, "reset", None)
        return True if not callable(reset_method) else reset_method()


__all__ = ["AppSettingsService", "PluginAdminService", "PluginSettingsService"]
