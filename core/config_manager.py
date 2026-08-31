import json
import logging
import os

from .app_paths import get_config_file, get_legacy_config_files
from .atomic_json import atomic_write_json


logger = logging.getLogger(__name__)

class ConfigManager:
    def __init__(self, config_file=None):
        self.using_default_path = config_file is None
        self.config_file = (
            get_config_file()
            if self.using_default_path
            else os.fspath(config_file)
        )
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
                return self._read_config_file(self.config_file)
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
                    self.config = config
                    self.save_config()
                    return config
                except Exception:
                    logger.exception("旧版配置文件迁移失败: %s", legacy_file)

        return self.default_config()

    def default_config(self):
        return {
            "window_size": [900, 600],
            "pinned_plugins": ["quick_copy"],
            "theme": "light",
            "worklog_lunch_break": {
                "start_time": "12:00",
                "end_time": "13:30"
            }
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
