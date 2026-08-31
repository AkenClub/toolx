import json
import logging
import os
import shutil
import sys
import tempfile

from core.app_paths import get_app_data_dir
from core.atomic_json import atomic_write_json

from .calculations import (
    DEFAULT_LUNCH_BREAK_END_TIME,
    DEFAULT_LUNCH_BREAK_START_TIME,
    ensure_data_shape,
    ensure_day,
)


logger = logging.getLogger(__name__)


def get_worklog_data_file():
    """Return the writable per-user worklog file path."""
    return os.path.join(get_app_data_dir(), "worklog", "data.json")


def get_legacy_worklog_data_files():
    """Return old worklog locations used before the user-data migration."""
    module_data_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")
    paths = [module_data_file]
    if getattr(sys, "frozen", False):
        executable_data_file = os.path.join(
            os.path.dirname(sys.executable),
            "plugins",
            "worklog",
            "data.json",
        )
        paths.insert(0, executable_data_file)

    unique_paths = []
    for path in paths:
        normalized = os.path.abspath(path)
        if normalized not in unique_paths:
            unique_paths.append(normalized)
    return unique_paths


def _migrate_legacy_data(target_file):
    if os.path.exists(target_file):
        return None

    target_file = os.path.abspath(target_file)
    for legacy_file in get_legacy_worklog_data_files():
        if os.path.abspath(legacy_file) == target_file or not os.path.isfile(legacy_file):
            continue
        temp_file = None
        try:
            os.makedirs(os.path.dirname(target_file), exist_ok=True)
            fd, temp_file = tempfile.mkstemp(
                prefix="." + os.path.basename(target_file) + ".",
                suffix=".migration.tmp",
                dir=os.path.dirname(target_file),
            )
            os.close(fd)
            shutil.copyfile(legacy_file, temp_file)
            os.replace(temp_file, target_file)
            temp_file = None
            logger.info("发现旧版工时数据，已迁移: %s -> %s", legacy_file, target_file)
            return legacy_file
        except Exception:
            logger.exception("工时数据迁移失败: %s -> %s", legacy_file, target_file)
        finally:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except OSError:
                    pass
    return None


def load_worklog_data(
    data_file=None,
    lunch_start_text=DEFAULT_LUNCH_BREAK_START_TIME,
    lunch_end_text=DEFAULT_LUNCH_BREAK_END_TIME,
):
    """Load and normalize worklog data, migrating the old default location once."""
    if data_file is None:
        data_file = get_worklog_data_file()
        _migrate_legacy_data(data_file)
    else:
        data_file = os.fspath(data_file)

    if not os.path.exists(data_file):
        return {"days": {}}, False

    try:
        with open(data_file, "r", encoding="utf-8") as file:
            raw_data = json.load(file)
        normalized_data = ensure_data_shape(raw_data)
        for date_key in list(normalized_data["days"].keys()):
            ensure_day(normalized_data, date_key, lunch_start_text, lunch_end_text)
        return normalized_data, False
    except Exception:
        logger.exception("工时数据读取或规范化失败: %s", data_file)
        return {"days": {}}, True


def save_worklog_data(data_file, data):
    """Persist the complete worklog structure using an atomic JSON replacement."""
    atomic_write_json(data_file, ensure_data_shape(data), indent=2)
