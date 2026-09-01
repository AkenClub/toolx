import json
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from core.config_manager import ConfigManager
from core.plugin_admin import PluginAdminError, PluginAdminService
from core.plugin_manager import PluginManager


PLUGIN_SOURCE = """
from core.plugin_interface import PluginInterface

class ImportedPlugin(PluginInterface):
    def get_id(self):
        return "imported_example"

    def get_name(self):
        return "Imported Example"

    def get_widget(self, parent):
        return None

def get_plugin(context):
    return ImportedPlugin(context)
"""


def _write_package(path, source=PLUGIN_SOURCE):
    manifest = {
        "id": "imported_example",
        "name": "Imported Example",
        "version": "1.0.0",
        "entry": "plugin.py:get_plugin",
        "api_version": 1,
    }
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("plugin.json", json.dumps(manifest))
        archive.writestr("plugin.py", source)


def test_install_disable_enable_and_load_imported_plugin(tmp_path):
    app_settings = ConfigManager(str(tmp_path / "config.json"))
    admin = PluginAdminService(app_settings=app_settings)
    package_path = tmp_path / "example.toolx-plugin"
    _write_package(package_path)

    manifest = admin.install_package(package_path)
    assert manifest.id == "imported_example"
    assert (tmp_path / "installed_plugins" / "imported_example" / "1.0.0" / "plugin.py").exists()

    manager = PluginManager(app_settings, plugin_dir=str(tmp_path / "builtin"))
    assert "imported_example" in manager.load_all_plugins()
    context = manager.get_plugin_context("imported_example")
    assert context.plugin_id == "imported_example"

    admin.disable("imported_example")
    manager.load_all_plugins()
    assert "imported_example" not in manager.get_plugins()

    admin.enable("imported_example")
    manager.load_all_plugins()
    assert "imported_example" in manager.get_plugins()

    context.storage.write_json("data.json", {"keep": True})
    admin.uninstall("imported_example")
    assert not (tmp_path / "installed_plugins" / "imported_example").exists()
    assert (tmp_path / "plugin_data" / "imported_example" / "data.json").exists()


def test_invalid_zip_path_is_rejected_before_extraction(tmp_path):
    app_settings = ConfigManager(str(tmp_path / "config.json"))
    admin = PluginAdminService(app_settings=app_settings)
    package_path = tmp_path / "malicious.toolx-plugin"
    with ZipFile(package_path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("../escaped.txt", "must not be written")
        archive.writestr("plugin.json", json.dumps({}))

    with pytest.raises(PluginAdminError):
        admin.install_package(package_path)

    assert not (tmp_path.parent / "escaped.txt").exists()
    assert not (tmp_path / "installed_plugins").exists()

