"""The restricted runtime objects exposed to ordinary plugins."""

from copy import deepcopy
import json
import logging
import os
from dataclasses import dataclass

from PyQt6.QtCore import QObject, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QApplication

from .app_paths import PluginPaths, validate_plugin_id
from .atomic_json import atomic_write_json


logger = logging.getLogger(__name__)
TOOLX_VERSION = "1.0.0"


def _safe_child_path(root, name):
    """Resolve a plugin-owned relative path without allowing path traversal."""
    if not isinstance(name, str) or not name or "\x00" in name:
        raise ValueError("插件存储名称必须是非空字符串")
    if os.path.isabs(name):
        raise ValueError("插件存储路径必须是相对路径")

    root_path = os.path.abspath(os.fspath(root))
    target_path = os.path.abspath(os.path.join(root_path, name))
    try:
        is_inside = os.path.commonpath([root_path, target_path]) == root_path
    except ValueError:
        is_inside = False
    if not is_inside or target_path == root_path:
        raise ValueError("插件存储路径不能跳出插件数据目录")
    return target_path


class ScopedPluginConfig(QObject):
    """Persistent settings limited to one plugin id."""

    changed = pyqtSignal(str, object)

    def __init__(self, plugin_id, paths=None, defaults=None, parent=None):
        super().__init__(parent)
        self.plugin_id = validate_plugin_id(plugin_id)
        if paths is not None and hasattr(paths, "paths"):
            paths = paths.paths
        self.paths = paths if isinstance(paths, PluginPaths) else PluginPaths(paths)
        self.file_path = self.paths.plugin_config_file(self.plugin_id)
        self._defaults = deepcopy(defaults) if isinstance(defaults, dict) else {}
        self._config = self._load()

    def _load(self):
        if not os.path.exists(self.file_path):
            return deepcopy(self._defaults)
        try:
            with open(self.file_path, "r", encoding="utf-8") as file:
                value = json.load(file)
            if not isinstance(value, dict):
                raise ValueError("插件配置根节点必须是 JSON 对象")
        except Exception:
            logger.exception("插件 %s 配置读取失败: %s", self.plugin_id, self.file_path)
            value = {}

        config = deepcopy(self._defaults)
        config.update(value)
        return config

    def get(self, key, default=None):
        return deepcopy(self._config.get(key, default))

    def has(self, key):
        return key in self._config

    def as_dict(self):
        return deepcopy(self._config)

    def set(self, key, value):
        self._config[key] = deepcopy(value)
        self._save()
        self.changed.emit(key, deepcopy(value))

    def update(self, values):
        if not isinstance(values, dict):
            raise TypeError("插件配置更新值必须是 JSON 对象")
        self._config.update(deepcopy(values))
        self._save()
        self.changed.emit("*", deepcopy(values))

    def reset(self, key=None):
        if key is None:
            self._config = deepcopy(self._defaults)
            changed_value = self.as_dict()
        elif key in self._defaults:
            self._config[key] = deepcopy(self._defaults[key])
            changed_value = deepcopy(self._config[key])
        else:
            self._config.pop(key, None)
            changed_value = None
        self._save()
        self.changed.emit("*" if key is None else key, changed_value)

    def _save(self):
        atomic_write_json(self.file_path, self._config, indent=2)


class ScopedPluginStorage:
    """File storage whose root is fixed to the current plugin."""

    def __init__(self, plugin_id, paths=None):
        self.plugin_id = validate_plugin_id(plugin_id)
        if paths is not None and hasattr(paths, "paths"):
            paths = paths.paths
        self.paths = paths if isinstance(paths, PluginPaths) else PluginPaths(paths)
        self.root_dir = self.paths.plugin_data_dir(self.plugin_id)

    def data_dir(self):
        os.makedirs(self.root_dir, exist_ok=True)
        return self.root_dir

    def cache_dir(self):
        path = self.paths.plugin_cache_dir(self.plugin_id)
        os.makedirs(path, exist_ok=True)
        return path

    def path(self, name):
        return _safe_child_path(self.root_dir, name)

    def exists(self, name):
        return os.path.exists(self.path(name))

    def read_json(self, name, default=None):
        file_path = self.path(name)
        if not os.path.exists(file_path):
            return deepcopy(default)
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)

    def write_json(self, name, value):
        atomic_write_json(self.path(name), value, indent=2)

    def read_text(self, name, default=None, encoding="utf-8"):
        file_path = self.path(name)
        if not os.path.exists(file_path):
            return default
        with open(file_path, "r", encoding=encoding) as file:
            return file.read()

    def write_text(self, name, value, encoding="utf-8"):
        file_path = self.path(name)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding=encoding, newline="\n") as file:
            file.write(value)

    def delete(self, name):
        file_path = self.path(name)
        if os.path.isfile(file_path):
            os.remove(file_path)
        elif os.path.isdir(file_path):
            import shutil

            shutil.rmtree(file_path)


class _ClipboardService:
    def read(self):
        app = QApplication.instance()
        return app.clipboard().text() if app is not None else ""

    def write(self, value):
        app = QApplication.instance()
        if app is not None:
            app.clipboard().setText(str(value))

    get_text = read
    set_text = write


class HostServices(QObject):
    """Small host capability facade; it deliberately contains no main window."""

    theme_changed = pyqtSignal(str)
    restart_requested = pyqtSignal()

    def __init__(
        self,
        plugin_id,
        app_settings=None,
        notify_callback=None,
        restart_callback=None,
        app_version=TOOLX_VERSION,
        parent=None,
    ):
        super().__init__(parent)
        self.plugin_id = validate_plugin_id(plugin_id)
        self.logger = logging.getLogger("toolx.plugin.%s" % self.plugin_id)
        # Keep the application settings object private.  Ordinary plugins
        # should only observe/change the explicitly supported theme service.
        self._app_settings = app_settings
        self._notify_callback = notify_callback
        self._restart_callback = restart_callback
        self._app_version = app_version
        self.clipboard = _ClipboardService()
        self._app_settings_change_connected = False
        app_settings_changed = getattr(app_settings, "changed", None)
        connect = getattr(app_settings_changed, "connect", None)
        if callable(connect):
            connect(self._on_app_settings_changed)
            self._app_settings_change_connected = True

    def _on_app_settings_changed(self, key, _value):
        if key in ("theme", "*"):
            self.theme_changed.emit(str(self.theme))

    @property
    def theme(self):
        if self._app_settings is None:
            return "light"
        return self._app_settings.get("theme", "light")

    def set_theme(self, theme):
        if self._app_settings is not None:
            self._app_settings.set("theme", theme)
            if not self._app_settings_change_connected:
                self.theme_changed.emit(str(theme))
            return
        self.theme_changed.emit(str(theme))

    @property
    def app_info(self):
        return {"name": "ToolX", "version": self._app_version}

    def notify(self, message, title="ToolX"):
        if self._notify_callback is not None:
            self._notify_callback(title, message)
        else:
            self.logger.info("%s: %s", title, message)

    def open_url(self, url):
        return QDesktopServices.openUrl(QUrl(str(url)))

    def open_path(self, path):
        return QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(os.fspath(path))))

    def request_restart(self):
        if self._restart_callback is not None:
            self._restart_callback()
        self.restart_requested.emit()


@dataclass
class PluginContext:
    """Context passed to an ordinary plugin factory."""

    plugin_id: str
    config: ScopedPluginConfig
    storage: ScopedPluginStorage
    services: HostServices

    @classmethod
    def create(cls, plugin_id, paths, app_settings=None, defaults=None):
        plugin_id = validate_plugin_id(plugin_id)
        if not isinstance(paths, PluginPaths):
            paths = PluginPaths(paths)
        return cls(
            plugin_id=plugin_id,
            config=ScopedPluginConfig(plugin_id, paths, defaults=defaults),
            storage=ScopedPluginStorage(plugin_id, paths),
            services=HostServices(plugin_id, app_settings=app_settings),
        )

    # Transitional helpers for old factories that treated their argument as a
    # config object. They delegate only to the current plugin's scope.
    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        return self.config.set(key, value)

    def update(self, values):
        return self.config.update(values)

    def reset(self):
        return self.config.reset()
