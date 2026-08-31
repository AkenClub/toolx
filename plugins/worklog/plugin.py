import logging

from PyQt6.QtWidgets import QWidget

from core.plugin_interface import PluginInterface

from .calculations import (
    COMPLETE_TOLERANCE_HOURS,
    DEFAULT_DAY_TOTAL_HOURS,
    DEFAULT_END_TIME,
    DEFAULT_LUNCH_BREAK_END_TIME,
    DEFAULT_LUNCH_BREAK_START_TIME,
    DEFAULT_START_TIME,
    DEFAULT_TASK_DURATION_MINUTES,
    LUNCH_BREAK_CONFIG_KEY,
    calculate_duration_details,
    calculate_duration_hours,
    calculate_lunch_break_overlap_seconds,
    calculate_percentage,
    create_task_item,
    ensure_data_shape,
    ensure_day,
    get_lunch_break_settings,
    get_next_task_time_range,
    is_valid_lunch_break,
    normalize_task_item,
    parse_time_text,
    parse_time_value,
    summarize_day,
    time_to_seconds,
)
from .storage import (
    get_legacy_worklog_data_files,
    get_worklog_data_file,
    load_worklog_data,
    save_worklog_data,
)
from .ui import (
    WorklogWidget,
    get_left_arrow_icon,
    get_refresh_icon,
    get_right_arrow_icon,
)


logger = logging.getLogger(__name__)


class WorklogPlugin(PluginInterface):
    def __init__(self, config_manager=None):
        super().__init__(config_manager)
        self.widget = None

    def get_id(self) -> str:
        return "worklog"

    def get_name(self) -> str:
        return "任务工时"

    def get_icon(self):
        return "🕒"

    def get_widget(self, parent: QWidget) -> QWidget:
        if self.widget is None:
            self.widget = WorklogWidget(self.config_manager, parent)
        return self.widget

    def on_unload(self):
        if self.widget is not None:
            try:
                self.widget.persist_current_day()
            except Exception:
                logger.exception("退出时保存任务工时失败")


def get_plugin(config_manager):
    return WorklogPlugin(config_manager)


__all__ = [
    "COMPLETE_TOLERANCE_HOURS",
    "DEFAULT_DAY_TOTAL_HOURS",
    "DEFAULT_END_TIME",
    "DEFAULT_LUNCH_BREAK_END_TIME",
    "DEFAULT_LUNCH_BREAK_START_TIME",
    "DEFAULT_START_TIME",
    "DEFAULT_TASK_DURATION_MINUTES",
    "LUNCH_BREAK_CONFIG_KEY",
    "WorklogPlugin",
    "WorklogWidget",
    "calculate_duration_details",
    "calculate_duration_hours",
    "calculate_lunch_break_overlap_seconds",
    "calculate_percentage",
    "create_task_item",
    "ensure_data_shape",
    "ensure_day",
    "get_legacy_worklog_data_files",
    "get_left_arrow_icon",
    "get_lunch_break_settings",
    "get_next_task_time_range",
    "get_refresh_icon",
    "get_right_arrow_icon",
    "get_worklog_data_file",
    "is_valid_lunch_break",
    "load_worklog_data",
    "normalize_task_item",
    "parse_time_text",
    "parse_time_value",
    "save_worklog_data",
    "summarize_day",
    "time_to_seconds",
]
