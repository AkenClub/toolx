import os
import re
import sys


APP_NAME = "ToolX"
PLUGIN_ID_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9_-]*[a-z0-9])?$")


def validate_plugin_id(plugin_id):
    """Validate and return a plugin id that is safe to use as a directory name."""
    if not isinstance(plugin_id, str) or not PLUGIN_ID_PATTERN.fullmatch(plugin_id):
        raise ValueError(
            "插件 ID 必须只包含小写字母、数字、下划线或短横线，且不能以分隔符开头或结尾"
        )
    return plugin_id


def get_resource_path(relative_path):
    """Return the absolute path of a bundled read-only resource."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, relative_path)


def get_app_data_dir(app_name=APP_NAME):
    """Return the per-user directory used by ToolX for writable data."""
    override = os.environ.get("TOOLX_DATA_DIR")
    if override:
        return os.path.abspath(os.path.expanduser(override))

    if os.name == "nt":
        root = os.environ.get("APPDATA")
        if not root:
            root = os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
    elif sys.platform == "darwin":
        root = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
    else:
        root = os.environ.get("XDG_DATA_HOME")
        if not root:
            root = os.path.join(os.path.expanduser("~"), ".local", "share")

    return os.path.join(root, app_name)


def get_config_file(app_name=APP_NAME):
    return os.path.join(get_app_data_dir(app_name), "toolx_config.json")


def get_plugin_data_dir(plugin_id, app_name=APP_NAME, data_root=None):
    """Return the isolated writable data directory for one plugin."""
    validate_plugin_id(plugin_id)
    root = os.fspath(data_root) if data_root is not None else get_app_data_dir(app_name)
    return os.path.join(os.path.abspath(root), "plugin_data", plugin_id)


def get_plugin_config_file(plugin_id, app_name=APP_NAME, data_root=None):
    """Return the settings file belonging to one plugin."""
    return os.path.join(get_plugin_data_dir(plugin_id, app_name, data_root), "settings.json")


def get_plugin_registry_file(app_name=APP_NAME, data_root=None):
    root = os.fspath(data_root) if data_root is not None else get_app_data_dir(app_name)
    return os.path.join(os.path.abspath(root), "plugin_registry.json")


def get_installed_plugins_dir(app_name=APP_NAME, data_root=None):
    root = os.fspath(data_root) if data_root is not None else get_app_data_dir(app_name)
    return os.path.join(os.path.abspath(root), "installed_plugins")


def get_logs_dir(app_name=APP_NAME, data_root=None):
    root = os.fspath(data_root) if data_root is not None else get_app_data_dir(app_name)
    return os.path.join(os.path.abspath(root), "logs")


class PluginPaths:
    """Centralize all writable ToolX and per-plugin paths.

    ``root`` is normally ``%APPDATA%/ToolX``.  Tests and alternate hosts can
    provide another root without changing any plugin code.
    """

    def __init__(self, root=None, app_name=APP_NAME, app_config_file=None):
        self.root = os.path.abspath(
            os.fspath(root) if root is not None else get_app_data_dir(app_name)
        )
        self.app_config_file = os.path.abspath(
            os.fspath(app_config_file)
            if app_config_file is not None
            else os.path.join(self.root, "toolx_config.json")
        )
        self.config_file = self.app_config_file
        self.plugin_registry_file = os.path.join(self.root, "plugin_registry.json")
        self.registry_file = self.plugin_registry_file
        self.plugin_data_root = os.path.join(self.root, "plugin_data")
        self.installed_plugins_root = os.path.join(self.root, "installed_plugins")
        self.logs_root = os.path.join(self.root, "logs")
        self.temp_root = os.path.join(self.root, ".tmp")

    @classmethod
    def from_config_file(cls, config_file=None):
        if config_file is None:
            return cls()
        config_path = os.path.abspath(os.fspath(config_file))
        return cls(os.path.dirname(config_path), app_config_file=config_path)

    def plugin_data_dir(self, plugin_id):
        validate_plugin_id(plugin_id)
        return os.path.join(self.plugin_data_root, plugin_id)

    def plugin_config_file(self, plugin_id):
        return os.path.join(self.plugin_data_dir(plugin_id), "settings.json")

    def plugin_cache_dir(self, plugin_id):
        return os.path.join(self.plugin_data_dir(plugin_id), "cache")

    def installed_plugin_dir(self, plugin_id, version):
        validate_plugin_id(plugin_id)
        if not isinstance(version, str) or not version.strip() or os.path.sep in version:
            raise ValueError("插件版本不能包含路径分隔符")
        return os.path.join(self.installed_plugins_root, plugin_id, version)


def get_legacy_config_files():
    """Return old config locations that may be migrated on first launch."""
    paths = [os.path.abspath("toolx_config.json")]
    if getattr(sys, "frozen", False):
        paths.append(os.path.join(os.path.dirname(sys.executable), "toolx_config.json"))

    unique_paths = []
    for path in paths:
        normalized = os.path.abspath(path)
        if normalized not in unique_paths:
            unique_paths.append(normalized)
    return unique_paths
