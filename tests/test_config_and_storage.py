import json

import core.config_manager as config_module
import plugins.worklog.storage as storage_module
from core.config_manager import ConfigManager
from plugins.worklog.storage import load_worklog_data


def test_config_save_is_atomic_and_roundtrips(tmp_path):
    config_path = tmp_path / "toolx_config.json"
    config = ConfigManager(str(config_path))

    config.set("example", {"enabled": True})

    with config_path.open("r", encoding="utf-8") as file:
        loaded = json.load(file)
    assert loaded["example"] == {"enabled": True}
    assert list(tmp_path.glob(".*.tmp")) == []


def test_config_changes_emit_key_and_wildcard_events(qapp, tmp_path):
    config = ConfigManager(str(tmp_path / "toolx_config.json"))
    changes = []
    config.changed.connect(lambda key, value: changes.append((key, value)))

    config.set("example", {"enabled": True})
    config.update({"theme": "dark"})
    config.reset()

    assert changes[0] == ("example", {"enabled": True})
    assert changes[1] == ("*", {"theme": "dark"})
    assert changes[2][0] == "*"
    assert changes[2][1]["theme"] == "light"


def test_default_config_migrates_legacy_file(monkeypatch, tmp_path):
    legacy_path = tmp_path / "legacy" / "toolx_config.json"
    target_path = tmp_path / "user-data" / "toolx_config.json"
    legacy_path.parent.mkdir()
    legacy_path.write_text(
        json.dumps({"window_size": [111, 222]}, ensure_ascii=False),
        encoding="utf-8",
    )

    monkeypatch.setattr(config_module, "get_config_file", lambda: str(target_path))
    monkeypatch.setattr(config_module, "get_legacy_config_files", lambda: [str(legacy_path)])

    config = ConfigManager()

    assert config.get("window_size") == [111, 222]
    assert target_path.exists()


def test_worklog_storage_migrates_legacy_file(monkeypatch, tmp_path):
    legacy_path = tmp_path / "legacy" / "data.json"
    target_path = tmp_path / "user-data" / "worklog" / "data.json"
    legacy_path.parent.mkdir()
    legacy_path.write_text(
        json.dumps({"days": {"2026-04-15": {"day_total_hours": 7.5, "items": []}}}),
        encoding="utf-8",
    )

    monkeypatch.setattr(storage_module, "get_worklog_data_file", lambda: str(target_path))
    monkeypatch.setattr(storage_module, "get_legacy_worklog_data_files", lambda: [str(legacy_path)])

    data, corrupted = load_worklog_data()

    assert corrupted is False
    assert data["days"]["2026-04-15"]["day_total_hours"] == 7.5
    assert target_path.exists()
