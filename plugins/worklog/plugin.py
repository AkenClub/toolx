import json
import os
import sys
import uuid

from PyQt6.QtCore import QDate, Qt, QTime
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDateEdit,
    QDoubleSpinBox,
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from core.plugin_interface import PluginInterface


DEFAULT_DAY_TOTAL_HOURS = 7.5
DEFAULT_START_TIME = "08:30"
DEFAULT_END_TIME = "09:00"
DEFAULT_TASK_DURATION_MINUTES = 30
COMPLETE_TOLERANCE_HOURS = 0.01


def get_worklog_data_file():
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
        plugin_dir = os.path.join(base_dir, "plugins", "worklog")
    else:
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(plugin_dir, "data.json")


def ensure_data_shape(data):
    if not isinstance(data, dict):
        return {"days": {}}

    days = data.get("days")
    if not isinstance(days, dict):
        days = {}

    return {"days": days}


def parse_time_text(time_text, fallback_text):
    parsed_time = QTime.fromString(str(time_text), "HH:mm")
    if parsed_time.isValid():
        return parsed_time.toString("HH:mm")
    return fallback_text


def create_task_item(date_key, start_time=DEFAULT_START_TIME, end_time=DEFAULT_END_TIME, task_text=""):
    start_text = parse_time_text(start_time, DEFAULT_START_TIME)
    end_text = parse_time_text(end_time, DEFAULT_END_TIME)
    return {
        "id": str(uuid.uuid4()),
        "date": date_key,
        "start_time": start_text,
        "end_time": end_text,
        "task_text": task_text or "",
        "duration_hours": calculate_duration_hours(start_text, end_text),
    }


def get_next_task_time_range(items):
    if not items:
        return DEFAULT_START_TIME, DEFAULT_END_TIME

    last_item = items[-1] if isinstance(items[-1], dict) else {}
    start_time = QTime.fromString(str(last_item.get("end_time", "")), "HH:mm")
    if not start_time.isValid():
        return DEFAULT_START_TIME, DEFAULT_END_TIME

    end_time = start_time.addSecs(DEFAULT_TASK_DURATION_MINUTES * 60)
    return start_time.toString("HH:mm"), end_time.toString("HH:mm")


def normalize_task_item(item, date_key):
    if not isinstance(item, dict):
        item = {}

    start_text = parse_time_text(item.get("start_time"), DEFAULT_START_TIME)
    end_text = parse_time_text(item.get("end_time"), DEFAULT_END_TIME)

    return {
        "id": str(item.get("id") or uuid.uuid4()),
        "date": date_key,
        "start_time": start_text,
        "end_time": end_text,
        "task_text": str(item.get("task_text") or ""),
        "duration_hours": calculate_duration_hours(start_text, end_text),
    }


def ensure_day(data, date_key):
    normalized = ensure_data_shape(data)
    data.clear()
    data.update(normalized)

    day = data["days"].get(date_key)
    if not isinstance(day, dict):
        day = {}

    raw_day_total_hours = day.get("day_total_hours", DEFAULT_DAY_TOTAL_HOURS)
    try:
        day_total_hours = round(float(raw_day_total_hours), 2)
    except (TypeError, ValueError):
        day_total_hours = DEFAULT_DAY_TOTAL_HOURS

    raw_items = day.get("items", [])
    if not isinstance(raw_items, list):
        raw_items = []

    items = [normalize_task_item(item, date_key) for item in raw_items]

    normalized_day = {
        "day_total_hours": day_total_hours,
        "items": items,
    }
    data["days"][date_key] = normalized_day
    return normalized_day


def calculate_duration_hours(start_text, end_text):
    start_time = QTime.fromString(str(start_text), "HH:mm")
    end_time = QTime.fromString(str(end_text), "HH:mm")
    if not start_time.isValid() or not end_time.isValid() or end_time <= start_time:
        return 0.0
    return round(start_time.secsTo(end_time) / 3600.0, 2)


def calculate_percentage(duration_hours, day_total_hours):
    try:
        total_hours = float(day_total_hours)
    except (TypeError, ValueError):
        total_hours = 0.0

    if total_hours <= 0:
        return 0.0
    return round((float(duration_hours) / total_hours) * 100, 2)


def summarize_day(items, day_total_hours):
    total_hours = round(sum(float(item.get("duration_hours", 0.0)) for item in items), 2)
    invalid_count = sum(
        1
        for item in items
        if calculate_duration_hours(item.get("start_time", ""), item.get("end_time", "")) <= 0
    )

    try:
        target_hours = round(float(day_total_hours), 2)
    except (TypeError, ValueError):
        target_hours = 0.0

    if target_hours <= 0:
        return {
            "total_hours": total_hours,
            "percentage": 0.0,
            "difference_hours": round(total_hours - target_hours, 2),
            "status": "标准工时无效",
            "color": "#e6a23c",
            "invalid_count": invalid_count,
        }

    difference_hours = round(total_hours - target_hours, 2)
    percentage = round((total_hours / target_hours) * 100, 2)

    if abs(difference_hours) <= COMPLETE_TOLERANCE_HOURS:
        status = "刚好 100%"
        color = "#67c23a"
    elif difference_hours < 0:
        status = "未满 100%"
        color = "#e6a23c"
    else:
        status = "超过 100%"
        color = "#f56c6c"

    return {
        "total_hours": total_hours,
        "percentage": percentage,
        "difference_hours": difference_hours,
        "status": status,
        "color": color,
        "invalid_count": invalid_count,
    }


def load_worklog_data(data_file):
    if not os.path.exists(data_file):
        return {"days": {}}, False

    try:
        with open(data_file, "r", encoding="utf-8") as file:
            raw_data = json.load(file)
    except Exception:
        return {"days": {}}, True

    normalized_data = ensure_data_shape(raw_data)
    for date_key in list(normalized_data["days"].keys()):
        ensure_day(normalized_data, date_key)
    return normalized_data, False


def save_worklog_data(data_file, data):
    directory = os.path.dirname(data_file)
    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(data_file, "w", encoding="utf-8") as file:
        json.dump(ensure_data_shape(data), file, indent=2, ensure_ascii=False)


class WorklogWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data_file = get_worklog_data_file()
        self.data, self.had_corrupted_data = load_worklog_data(self.data_file)
        self.is_loading = False

        self.init_ui()
        self.load_current_date()

        if self.had_corrupted_data:
            QMessageBox.warning(
                self,
                "数据恢复",
                "检测到任务工时数据文件损坏，已恢复为空数据结构。后续修改会覆盖损坏文件。",
            )

    def init_ui(self):
        self.setStyleSheet(
            """
            QWidget {
                background-color: #ffffff;
                font-family: 'Segoe UI', 'Microsoft YaHei';
                font-size: 14px;
                color: #303133;
            }
            QLabel#Title {
                font-size: 22px;
                font-weight: bold;
                color: #303133;
            }
            QLabel#Caption {
                color: #909399;
            }
            QFrame#Toolbar, QFrame#SummaryCard {
                background-color: #f7f9fc;
                border: 1px solid #e4e7ed;
                border-radius: 10px;
            }
            QPushButton {
                background-color: #409eff;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #66b1ff;
            }
            QPushButton#Danger {
                background-color: #f56c6c;
            }
            QPushButton#Danger:hover {
                background-color: #f78989;
            }
            QDateEdit, QDoubleSpinBox, QTimeEdit, QLineEdit {
                background-color: #ffffff;
                border: 1px solid #dcdfe6;
                border-radius: 6px;
                padding: 6px 8px;
            }
            QTableWidget {
                border: 1px solid #ebeef5;
                border-radius: 8px;
                gridline-color: #ebeef5;
                background-color: #ffffff;
            }
            QHeaderView::section {
                background-color: #f5f7fa;
                color: #606266;
                padding: 10px;
                border: none;
                border-bottom: 1px solid #ebeef5;
                font-weight: bold;
            }
            QLabel#SummaryText {
                font-size: 14px;
                line-height: 1.6;
            }
            """
        )

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        title_label = QLabel("🕒 每日任务工时")
        title_label.setObjectName("Title")
        caption_label = QLabel("按天记录任务、精确时间范围，并实时保存到本地。")
        caption_label.setObjectName("Caption")

        toolbar = QFrame()
        toolbar.setObjectName("Toolbar")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(16, 14, 16, 14)
        toolbar_layout.setSpacing(12)

        date_label = QLabel("日期")
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.dateChanged.connect(self.on_date_changed)

        total_label = QLabel("当天标准工时")
        self.day_total_spin = QDoubleSpinBox()
        self.day_total_spin.setRange(-24.0, 24.0)
        self.day_total_spin.setDecimals(2)
        self.day_total_spin.setSingleStep(0.5)
        self.day_total_spin.setSuffix(" 小时")
        self.day_total_spin.setValue(DEFAULT_DAY_TOTAL_HOURS)
        self.day_total_spin.valueChanged.connect(self.on_day_total_changed)

        self.add_row_button = QPushButton("新增任务")
        self.add_row_button.clicked.connect(self.add_task_row)

        toolbar_layout.addWidget(date_label)
        toolbar_layout.addWidget(self.date_edit)
        toolbar_layout.addSpacing(8)
        toolbar_layout.addWidget(total_label)
        toolbar_layout.addWidget(self.day_total_spin)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.add_row_button)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["开始时间", "结束时间", "工时", "占比", "任务内容", "操作"])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setShowGrid(True)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setColumnWidth(4, 320)

        self.summary_card = QFrame()
        self.summary_card.setObjectName("SummaryCard")
        summary_layout = QVBoxLayout(self.summary_card)
        summary_layout.setContentsMargins(16, 14, 16, 14)
        summary_layout.setSpacing(8)

        summary_title = QLabel("当天汇总")
        summary_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #303133;")
        self.summary_label = QLabel()
        self.summary_label.setObjectName("SummaryText")
        self.summary_label.setWordWrap(True)

        summary_layout.addWidget(summary_title)
        summary_layout.addWidget(self.summary_label)

        main_layout.addWidget(title_label)
        main_layout.addWidget(caption_label)
        main_layout.addWidget(toolbar)
        main_layout.addWidget(self.table, 1)
        main_layout.addWidget(self.summary_card)

    def current_date_key(self):
        return self.date_edit.date().toString("yyyy-MM-dd")

    def load_current_date(self):
        self.is_loading = True
        date_key = self.current_date_key()
        day = ensure_day(self.data, date_key)

        self.day_total_spin.blockSignals(True)
        self.day_total_spin.setValue(day["day_total_hours"])
        self.day_total_spin.blockSignals(False)

        self.table.setRowCount(0)
        for item in day["items"]:
            self.insert_table_row(item, day["day_total_hours"])

        self.refresh_summary()
        self.is_loading = False

    def insert_table_row(self, item, day_total_hours):
        row = self.table.rowCount()
        self.table.insertRow(row)

        start_edit = self.create_time_edit(item["start_time"])
        end_edit = self.create_time_edit(item["end_time"])
        task_edit = QLineEdit(item["task_text"])
        delete_button = QPushButton("删除")
        delete_button.setObjectName("Danger")

        task_edit.setProperty("item_id", item["id"])
        delete_button.setProperty("item_id", item["id"])

        start_edit.timeChanged.connect(self.on_table_input_changed)
        end_edit.timeChanged.connect(self.on_table_input_changed)
        task_edit.textChanged.connect(self.on_table_input_changed)
        delete_button.clicked.connect(lambda _, item_id=item["id"]: self.delete_task_row(item_id))

        duration_item = QTableWidgetItem()
        percentage_item = QTableWidgetItem()
        duration_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        percentage_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        duration_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        percentage_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        self.table.setCellWidget(row, 0, start_edit)
        self.table.setCellWidget(row, 1, end_edit)
        self.table.setItem(row, 2, duration_item)
        self.table.setItem(row, 3, percentage_item)
        self.table.setCellWidget(row, 4, task_edit)
        self.table.setCellWidget(row, 5, delete_button)

        self.update_display_row(row, item, day_total_hours)

    def create_time_edit(self, time_text):
        time_edit = QTimeEdit()
        time_edit.setDisplayFormat("HH:mm")
        time_edit.setTime(QTime.fromString(parse_time_text(time_text, DEFAULT_START_TIME), "HH:mm"))
        time_edit.setKeyboardTracking(False)
        return time_edit

    def update_display_row(self, row, item, day_total_hours):
        start_text = item["start_time"]
        end_text = item["end_time"]
        duration_hours = calculate_duration_hours(start_text, end_text)
        percentage = calculate_percentage(duration_hours, day_total_hours)
        is_valid_range = duration_hours > 0

        duration_item = self.table.item(row, 2)
        percentage_item = self.table.item(row, 3)
        start_edit = self.table.cellWidget(row, 0)
        end_edit = self.table.cellWidget(row, 1)

        if is_valid_range:
            duration_item.setText(f"{duration_hours:.2f} h")
            percentage_item.setText(f"{percentage:.2f}%")
            duration_item.setForeground(Qt.GlobalColor.black)
            percentage_item.setForeground(Qt.GlobalColor.black)
            start_edit.setStyleSheet("")
            end_edit.setStyleSheet("")
            duration_item.setToolTip("")
            percentage_item.setToolTip("")
        else:
            duration_item.setText("无效")
            percentage_item.setText("0.00%")
            duration_item.setForeground(Qt.GlobalColor.red)
            percentage_item.setForeground(Qt.GlobalColor.red)
            invalid_style = "QTimeEdit { border: 1px solid #f56c6c; border-radius: 6px; padding: 6px 8px; }"
            start_edit.setStyleSheet(invalid_style)
            end_edit.setStyleSheet(invalid_style)
            tooltip = "结束时间必须晚于开始时间，该行暂按 0 小时处理。"
            duration_item.setToolTip(tooltip)
            percentage_item.setToolTip(tooltip)

    def build_items_from_table(self):
        date_key = self.current_date_key()
        items = []
        day_total_hours = round(float(self.day_total_spin.value()), 2)

        for row in range(self.table.rowCount()):
            start_edit = self.table.cellWidget(row, 0)
            end_edit = self.table.cellWidget(row, 1)
            task_edit = self.table.cellWidget(row, 4)

            item = {
                "id": str(task_edit.property("item_id") or uuid.uuid4()),
                "date": date_key,
                "start_time": start_edit.time().toString("HH:mm"),
                "end_time": end_edit.time().toString("HH:mm"),
                "task_text": task_edit.text(),
            }
            item["duration_hours"] = calculate_duration_hours(item["start_time"], item["end_time"])
            items.append(item)
            self.update_display_row(row, item, day_total_hours)

        return items

    def persist_current_day(self):
        if self.is_loading:
            return

        date_key = self.current_date_key()
        day = ensure_day(self.data, date_key)
        day["day_total_hours"] = round(float(self.day_total_spin.value()), 2)
        day["items"] = self.build_items_from_table()
        self.refresh_summary()
        self.save_data()

    def save_data(self):
        try:
            save_worklog_data(self.data_file, self.data)
        except Exception as error:
            QMessageBox.critical(self, "保存失败", f"任务工时数据保存失败：\n{error}")

    def refresh_summary(self):
        date_key = self.current_date_key()
        day = ensure_day(self.data, date_key)
        summary = summarize_day(day["items"], day["day_total_hours"])

        summary_lines = [
            f"标准工时：<b>{day['day_total_hours']:.2f}</b> 小时",
            f"已记录：<b>{summary['total_hours']:.2f}</b> 小时",
            f"占用比例：<b>{summary['percentage']:.2f}%</b>",
            f"差值：<b>{summary['difference_hours']:.2f}</b> 小时",
            f"状态：<b style='color:{summary['color']};'>{summary['status']}</b>",
        ]

        if summary["invalid_count"] > 0:
            summary_lines.append(
                f"<span style='color:#f56c6c;'>当前有 {summary['invalid_count']} 条记录的结束时间不晚于开始时间，暂按 0 小时计算。</span>"
            )
        elif day["items"]:
            summary_lines.append("<span style='color:#67c23a;'>当前所有任务时间范围有效，已实时保存。</span>")
        else:
            summary_lines.append("<span style='color:#909399;'>当前日期还没有任务记录。</span>")

        self.summary_card.setStyleSheet(
            f"QFrame#SummaryCard {{ background-color: #f7f9fc; border: 1px solid {summary['color']}; border-radius: 10px; }}"
        )
        self.summary_label.setText("<br>".join(summary_lines))

    def add_task_row(self):
        date_key = self.current_date_key()
        day = ensure_day(self.data, date_key)
        start_time, end_time = get_next_task_time_range(day["items"])
        item = create_task_item(date_key, start_time, end_time)
        self.insert_table_row(item, self.day_total_spin.value())
        self.persist_current_day()

    def delete_task_row(self, item_id):
        date_key = self.current_date_key()
        self.persist_current_day()

        day = ensure_day(self.data, date_key)
        day["items"] = [item for item in day["items"] if item.get("id") != item_id]
        self.save_data()
        self.load_current_date()

    def on_table_input_changed(self):
        self.persist_current_day()

    def on_day_total_changed(self, _value):
        self.persist_current_day()

    def on_date_changed(self, _date):
        if self.is_loading:
            return
        self.load_current_date()


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
            self.widget = WorklogWidget(parent)
        return self.widget


def get_plugin(config_manager):
    return WorklogPlugin(config_manager)
