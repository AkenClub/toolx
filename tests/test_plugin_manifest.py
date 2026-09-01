import json

import pytest

from core.plugin_manifest import PluginManifest, PluginManifestError


def test_manifest_validates_required_metadata_and_entry(tmp_path):
    plugin_dir = tmp_path / "example"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.py").write_text("def get_plugin(context):\n    return None\n", encoding="utf-8")
    (plugin_dir / "plugin.json").write_text(
        json.dumps(
            {
                "id": "example",
                "name": "Example",
                "version": "1.2.3",
                "entry": "plugin.py:get_plugin",
                "api_version": 1,
                "settings": {"has_pages": True},
            }
        ),
        encoding="utf-8",
    )

    manifest = PluginManifest.from_directory(plugin_dir)

    assert manifest.id == "example"
    assert manifest.entry_module == "plugin"
    assert manifest.entry_function == "get_plugin"
    assert manifest.entry_file == str(plugin_dir / "plugin.py")
    assert manifest.is_compatible()


@pytest.mark.parametrize(
    "overrides",
    [
        {"id": "Bad ID"},
        {"version": "1.0"},
        {"entry": "../plugin.py:get_plugin"},
        {"api_version": 0},
    ],
)
def test_manifest_rejects_invalid_values(tmp_path, overrides):
    plugin_dir = tmp_path / "example"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.py").write_text("", encoding="utf-8")
    raw = {
        "id": "example",
        "name": "Example",
        "version": "1.0.0",
        "entry": "plugin.py:get_plugin",
        "api_version": 1,
    }
    raw.update(overrides)
    (plugin_dir / "plugin.json").write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(PluginManifestError):
        PluginManifest.from_directory(plugin_dir)
