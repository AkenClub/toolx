import logging

from PyQt6.QtCore import QTime
from PyQt6.QtWidgets import QFormLayout, QLabel, QTimeEdit, QVBoxLayout, QWidget

from core.plugin_interface import PluginInterface, SettingsPage

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
    def __init__(self, context=None):
        super().__init__(context)
        self.widget = None

    def get_id(self) -> str:
        return "worklog"

    def get_name(self) -> str:
        return "任务工时"

    def get_icon(self):
        return "🕒"

    def get_widget(self, parent: QWidget) -> QWidget:
        if self.widget is None:
            self.widget = WorklogWidget(self.context, parent)
        return self.widget

    def get_settings_pages(self):
        return [
            SettingsPage(
                page_id="general",
                title="常规",
                path=("插件", self.get_name()),
                factory=lambda parent: WorklogSettingsWidget(self.context, parent),
                plugin_id=self.get_id(),
            )
        ]

    def on_unload(self):
        if self.widget is not None:
            try:
                self.widget.persist_current_day()
            except Exception:
                logger.exception("退出时保存任务工时失败")


class WorklogSettingsWidget(QWidget):
    def __init__(self, context, parent=None):
        super().__init__(parent)
        self.context = context
        self.config = getattr(context, "config", None)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("任务工时设置"))
        form = QFormLayout()
        self.start_edit = QTimeEdit()
        self.end_edit = QTimeEdit()
        for editor in (self.start_edit, self.end_edit):
            editor.setDisplayFormat("HH:mm")
        form.addRow("午休开始", self.start_edit)
        form.addRow("午休结束", self.end_edit)
        layout.addLayout(form)
        layout.addWidget(QLabel("午休设置只影响工时自动计算，不会修改已登记的原始记录。"))
        layout.addStretch(1)
        self.load()

    def load(self):
        settings = get_lunch_break_settings(self.config)
        self.start_edit.setTime(QTime.fromString(settings["start_time"], "HH:mm"))
        self.end_edit.setTime(QTime.fromString(settings["end_time"], "HH:mm"))

    def apply(self):
        start_text = self.start_edit.time().toString("HH:mm")
        end_text = self.end_edit.time().toString("HH:mm")
        if not is_valid_lunch_break(start_text, end_text):
            return False
        if self.config is not None:
            self.config.set(
                LUNCH_BREAK_CONFIG_KEY,
                {"start_time": start_text, "end_time": end_text},
            )
        return True

    def reset(self):
        self.start_edit.setTime(QTime.fromString(DEFAULT_LUNCH_BREAK_START_TIME, "HH:mm"))
        self.end_edit.setTime(QTime.fromString(DEFAULT_LUNCH_BREAK_END_TIME, "HH:mm"))


def get_plugin(context):
    return WorklogPlugin(context)


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
    "WorklogSettingsWidget",
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
