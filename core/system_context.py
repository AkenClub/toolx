"""System-only context used by the core settings center."""

from dataclasses import dataclass

from .plugin_admin import PluginAdminService
from .plugin_context import HostServices
from .settings.settings_services import PluginSettingsService


@dataclass
class SystemContext:
    app_settings: object
    plugin_admin: PluginAdminService
    plugin_settings: PluginSettingsService
    services: HostServices

    @classmethod
    def create(cls, app_settings=None, plugin_manager=None, plugin_admin=None):
        if plugin_admin is None:
            plugin_admin = PluginAdminService(app_settings=app_settings)
        return cls(
            app_settings=app_settings,
            plugin_admin=plugin_admin,
            plugin_settings=PluginSettingsService(plugin_manager),
            services=HostServices("toolx", app_settings=app_settings),
        )
