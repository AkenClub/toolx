import json
import logging
import os

from .app_paths import PluginPaths, get_config_file, get_legacy_config_files
from .atomic_json import atomic_write_json


logger = logging.getLogger(__name__)
CURRENT_SCHEMA_VERSION = 2

class ConfigManager:
    """Manage ToolX application settings only.

    Plugin settings are migrated out of this file and are thereafter owned by
    ``ScopedPluginConfig``.  ``ConfigManager`` remains as the compatibility
    name used by the existing host code.
    """

    def __init__(self, config_file=None, paths=None, data_dir=None):
        explicit_data_root = paths is not None or data_dir is not None
        self.using_default_path = config_file is None and not explicit_data_root
        if data_dir is not None and paths is None:
            paths = PluginPaths(data_dir)
        if paths is not None:
            self.paths = paths if isinstance(paths, PluginPaths) else PluginPaths(paths)
            self.config_file = self.paths.app_config_file
        elif self.using_default_path:
            # Resolve through get_config_file() so callers can redirect the
            # default location in tests and alternate application hosts.
            self.config_file = os.path.abspath(get_config_file())
            self.paths = PluginPaths(
                os.path.dirname(self.config_file),
                app_config_file=self.config_file,
            )
        else:
            self.config_file = os.path.abspath(os.fspath(config_file))
            self.paths = PluginPaths.from_config_file(self.config_file)
        self.legacy_config_files = get_legacy_config_files() if self.using_default_path else []
        self.config = self.load_config()

    def _read_config_file(self, file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            config = json.load(file)
        if not isinstance(config, dict):
            raise ValueError("配置根节点必须是 JSON 对象")
        return config

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                config = self._read_config_file(self.config_file)
                return self._migrate_config(config, save=True)
            except Exception:
                logger.exception("配置文件读取失败: %s", self.config_file)
                return self.default_config()

        if self.using_default_path:
            for legacy_file in self.legacy_config_files:
                if os.path.abspath(legacy_file) == os.path.abspath(self.config_file):
                    continue
                if not os.path.exists(legacy_file):
                    continue
                try:
                    config = self._read_config_file(legacy_file)
                    logger.info(
                        "发现旧版配置文件，将迁移到用户数据目录: %s -> %s",
                        legacy_file,
                        self.config_file,
                    )
                    self.config = self._migrate_config(config, save=False)
                    self.save_config()
                    return self.config
                except Exception:
                    logger.exception("旧版配置文件迁移失败: %s", legacy_file)

        return self.default_config()

    def _migrate_config(self, config, save=False):
        """Normalize app settings and move legacy plugin settings safely."""
        if not isinstance(config, dict):
            raise ValueError("配置根节点必须是 JSON 对象")

        migrated = dict(config)
        changed = False
        raw_schema_version = migrated.get("schema_version", 1)
        try:
            schema_version = int(raw_schema_version)
        except (TypeError, ValueError):
            schema_version = 1

        legacy_lunch = migrated.pop("worklog_lunch_break", None)
        if isinstance(legacy_lunch, dict):
            try:
                self._migrate_plugin_settings(
                    "worklog",
                    {"worklog_lunch_break": legacy_lunch},
                )
                changed = True
                logger.info("已将旧版工时设置迁移到插件专属配置")
            except Exception:
                # Do not remove the only copy when the destination cannot be
                # written.  The original app file is kept intact as well.
                migrated["worklog_lunch_break"] = legacy_lunch
                logger.exception("旧版工时设置迁移失败，保留原配置")

        defaults = self.default_config()
        for key, default_value in defaults.items():
            if key not in migrated:
                migrated[key] = default_value
                changed = True

        if schema_version < CURRENT_SCHEMA_VERSION or migrated.get("schema_version") != CURRENT_SCHEMA_VERSION:
            migrated["schema_version"] = CURRENT_SCHEMA_VERSION
            changed = True

        self.config = migrated
        if save and changed:
            self.save_config()
        return migrated

    def _migrate_plugin_settings(self, plugin_id, values):
        target_file = self.paths.plugin_config_file(plugin_id)
        existing = {}
        if os.path.exists(target_file):
            with open(target_file, "r", encoding="utf-8") as file:
                loaded = json.load(file)
            if not isinstance(loaded, dict):
                raise ValueError("插件配置根节点必须是 JSON 对象")
            existing = loaded

        for key, value in values.items():
            existing.setdefault(key, value)
        atomic_write_json(target_file, existing, indent=2)

    def default_config(self):
        return {
            "schema_version": CURRENT_SCHEMA_VERSION,
            "window_size": [900, 600],
            "pinned_plugins": ["quick_copy"],
            "theme": "light",
        }

    def save_config(self):
        try:
            atomic_write_json(self.config_file, self.config, indent=4)
        except Exception:
            logger.exception("配置文件保存失败: %s", self.config_file)

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save_config()

    def update(self, values):
        if not isinstance(values, dict):
            raise TypeError("应用配置更新值必须是 JSON 对象")
        self.config.update(values)
        self.save_config()

    def reset(self):
        self.config = self.default_config()
        self.save_config()

    def add_pinned(self, plugin_id):
        pinned = self.get("pinned_plugins", [])
        if not isinstance(pinned, list):
            pinned = []
        if plugin_id not in pinned:
            pinned.append(plugin_id)
            self.set("pinned_plugins", pinned)

    def remove_pinned(self, plugin_id):
        pinned = self.get("pinned_plugins", [])
        if not isinstance(pinned, list):
            return
        if plugin_id in pinned:
            pinned.remove(plugin_id)
            self.set("pinned_plugins", pinned)


class AppSettingsService(ConfigManager):
    """Preferred descriptive name for the host application settings service."""

    pass
