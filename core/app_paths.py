import os
import sys


APP_NAME = "ToolX"


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
