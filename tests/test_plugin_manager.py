import importlib
import logging
import textwrap
import uuid

from core.plugin_manager import PluginManager


def _create_package(tmp_path):
    package_name = "plugin_pkg_" + uuid.uuid4().hex
    package_dir = tmp_path / package_name
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    return package_name, package_dir


def _write_plugin(package_dir, folder_name, source):
    plugin_dir = package_dir / folder_name
    plugin_dir.mkdir()
    (plugin_dir / "__init__.py").write_text("", encoding="utf-8")
    (plugin_dir / "plugin.py").write_text(textwrap.dedent(source), encoding="utf-8")


def _valid_plugin_source(plugin_id, on_load="pass"):
    return f"""
        from core.plugin_interface import PluginInterface

        class ExamplePlugin(PluginInterface):
            def get_id(self):
                return {plugin_id!r}

            def get_name(self):
                return {plugin_id!r}

            def get_widget(self, parent):
                return None

            def on_load(self):
                {on_load}

        def get_plugin(config_manager):
            return ExamplePlugin(config_manager)
    """


def test_plugin_manager_isolates_errors_and_rejects_duplicate_ids(tmp_path, monkeypatch, caplog):
    package_name, package_dir = _create_package(tmp_path)
    _write_plugin(package_dir, "a_duplicate", _valid_plugin_source("duplicate"))
    _write_plugin(package_dir, "b_duplicate", _valid_plugin_source("duplicate"))
    _write_plugin(package_dir, "good", _valid_plugin_source("good"))
    _write_plugin(
        package_dir,
        "broken_factory",
        """
        def get_plugin(config_manager):
            raise RuntimeError("factory failed")
        """,
    )
    _write_plugin(
        package_dir,
        "missing_factory",
        "value = 1",
    )
    _write_plugin(
        package_dir,
        "broken_lifecycle",
        _valid_plugin_source("broken_lifecycle", "raise RuntimeError('load failed')"),
    )

    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()
    manager = PluginManager(
        config_manager=None,
        plugin_package=package_name,
        plugin_dir=str(package_dir),
    )

    with caplog.at_level(logging.INFO):
        plugins = manager.load_all_plugins()

    assert set(plugins) == {"duplicate", "good"}
    assert "重复插件 ID" in caplog.text
    assert "broken_factory" in caplog.text
    assert "on_load() 执行失败" in caplog.text
    manager.unload_all()
