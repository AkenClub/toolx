import logging
import uuid

from PyQt6.QtCore import QDate, QSize, Qt, QTime
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
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

from .calculations import (
    DEFAULT_DAY_TOTAL_HOURS,
    DEFAULT_END_TIME,
    DEFAULT_LUNCH_BREAK_END_TIME,
    DEFAULT_LUNCH_BREAK_START_TIME,
    DEFAULT_START_TIME,
    LUNCH_BREAK_CONFIG_KEY,
    calculate_duration_details,
    calculate_duration_hours,
    calculate_percentage,
    create_task_item,
    ensure_day,
    get_lunch_break_settings,
    get_next_task_time_range,
    is_valid_lunch_break,
    normalize_custom_duration,
    parse_time_text,
    parse_time_value,
    summarize_day,
)
from .storage import (
    get_worklog_data_file,
    load_worklog_data,
    save_worklog_data,
)


logger = logging.getLogger(__name__)


REFRESH_SVG = b"""<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M12 4V1L8 5L12 9V6C15.31 6 18 8.69 18 12C18 15.31 15.31 18 12 18C8.69 18 6 15.31 6 12H4C4 16.42 7.58 20 12 20C16.42 20 20 16.42 20 12C20 7.58 16.42 4 12 4Z" fill="#606266"/>
</svg>"""

LEFT_ARROW_SVG = b"""<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M15.41 7.41L14 6L8 12L14 18L15.41 16.59L10.83 12L15.41 7.41Z" fill="#606266"/>
</svg>"""

RIGHT_ARROW_SVG = b"""<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M10 6L8.59 7.41L13.17 12L8.59 16.59L10 18L16 12L10 6Z" fill="#606266"/>
</svg>"""


def _icon_from_svg(svg_data):
    pixmap = QPixmap()
    pixmap.loadFromData(svg_data, "SVG")
    return QIcon(pixmap)


def get_refresh_icon():
    return _icon_from_svg(REFRESH_SVG)


def get_left_arrow_icon():
    return _icon_from_svg(LEFT_ARROW_SVG)


def get_right_arrow_icon():
    return _icon_from_svg(RIGHT_ARROW_SVG)


class WorklogWidget(QWidget):
    def __init__(self, config_manager=None, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.data_file = get_worklog_data_file()
        initial_lunch = get_lunch_break_settings(self.config_manager)
        self.data, self.had_corrupted_data = load_worklog_data(
            lunch_start_text=initial_lunch["start_time"],
            lunch_end_text=initial_lunch["end_time"],
        )
        self.is_loading = False
        self._loaded_date_key = None

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
        caption_label = QLabel("按天记录任务、精确时间范围，午休时间会自动跳过并实时保存到本地。")
        caption_label.setObjectName("Caption")

        toolbar = QFrame()
        toolbar.setObjectName("Toolbar")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(16, 14, 16, 14)
        toolbar_layout.setSpacing(12)

        date_label = QLabel("日期")
        date_layout = QHBoxLayout()
        date_layout.setSpacing(4)
        date_layout.setContentsMargins(0, 0, 0, 0)

        self.prev_date_btn = QPushButton()
        self.prev_date_btn.setIcon(get_left_arrow_icon())
        self.prev_date_btn.setIconSize(QSize(16, 16))
        self.prev_date_btn.setFixedSize(30, 30)
        self.prev_date_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.prev_date_btn.setToolTip("前一天")
        self.prev_date_btn.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                border: 1px solid #dcdfe6;
                border-radius: 6px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #f5f7fa;
                border-color: #c0c4cc;
            }
            QPushButton:pressed {
                background-color: #e4e7ed;
            }
            """
        )
        self.prev_date_btn.clicked.connect(self.on_prev_date_clicked)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.dateChanged.connect(self.on_date_changed)

        self.next_date_btn = QPushButton()
        self.next_date_btn.setIcon(get_right_arrow_icon())
        self.next_date_btn.setIconSize(QSize(16, 16))
        self.next_date_btn.setFixedSize(30, 30)
        self.next_date_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_date_btn.setToolTip("后一天")
        self.next_date_btn.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                border: 1px solid #dcdfe6;
                border-radius: 6px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #f5f7fa;
                border-color: #c0c4cc;
            }
            QPushButton:pressed {
                background-color: #e4e7ed;
            }
            """
        )
        self.next_date_btn.clicked.connect(self.on_next_date_clicked)

        date_layout.addWidget(self.prev_date_btn)
        date_layout.addWidget(self.date_edit)
        date_layout.addWidget(self.next_date_btn)

        total_label = QLabel("当天标准工时")
        self.day_total_spin = QDoubleSpinBox()
        self.day_total_spin.setRange(-24.0, 24.0)
        self.day_total_spin.setDecimals(2)
        self.day_total_spin.setSingleStep(0.5)
        self.day_total_spin.setSuffix(" 小时")
        self.day_total_spin.setValue(DEFAULT_DAY_TOTAL_HOURS)
        self.day_total_spin.valueChanged.connect(self.on_day_total_changed)

        lunch_settings = get_lunch_break_settings(self.config_manager)
        lunch_label = QLabel("全局午休")
        self.lunch_start_edit = self.create_time_edit(
            lunch_settings["start_time"],
            DEFAULT_LUNCH_BREAK_START_TIME,
        )
        self.lunch_end_edit = self.create_time_edit(
            lunch_settings["end_time"],
            DEFAULT_LUNCH_BREAK_END_TIME,
        )
        self.lunch_start_edit.timeChanged.connect(self.on_lunch_break_changed)
        self.lunch_end_edit.timeChanged.connect(self.on_lunch_break_changed)

        self.add_row_button = QPushButton("新增任务")
        self.add_row_button.clicked.connect(self.add_task_row)

        toolbar_layout.addWidget(date_label)
        toolbar_layout.addLayout(date_layout)
        toolbar_layout.addSpacing(8)
        toolbar_layout.addWidget(total_label)
        toolbar_layout.addWidget(self.day_total_spin)
        toolbar_layout.addSpacing(8)
        toolbar_layout.addWidget(lunch_label)
        toolbar_layout.addWidget(self.lunch_start_edit)
        toolbar_layout.addWidget(QLabel("至"))
        toolbar_layout.addWidget(self.lunch_end_edit)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.add_row_button)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["开始时间", "结束时间", "工时（扣午休）", "占比", "已登记", "任务内容", "操作"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setShowGrid(True)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setColumnWidth(5, 320)

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

    def get_active_lunch_break_settings(self):
        if hasattr(self, "lunch_start_edit") and hasattr(self, "lunch_end_edit"):
            start_text = self.lunch_start_edit.time().toString("HH:mm")
            end_text = self.lunch_end_edit.time().toString("HH:mm")
            return {
                "start_time": start_text,
                "end_time": end_text,
                "is_valid": is_valid_lunch_break(start_text, end_text),
            }

        return get_lunch_break_settings(self.config_manager)

    def save_lunch_break_settings(self):
        if self.config_manager is None:
            return

        lunch_settings = self.get_active_lunch_break_settings()
        self.config_manager.set(
            LUNCH_BREAK_CONFIG_KEY,
            {
                "start_time": lunch_settings["start_time"],
                "end_time": lunch_settings["end_time"],
            },
        )

    def recalculate_all_days(self):
        lunch_settings = self.get_active_lunch_break_settings()
        for date_key in list(self.data.get("days", {}).keys()):
            ensure_day(
                self.data,
                date_key,
                lunch_settings["start_time"],
                lunch_settings["end_time"],
            )
        self.save_data()

    def load_current_date(self):
        self.is_loading = True
        date_key = self.current_date_key()
        lunch_settings = self.get_active_lunch_break_settings()
        try:
            day = ensure_day(
                self.data,
                date_key,
                lunch_settings["start_time"],
                lunch_settings["end_time"],
            )

            self.day_total_spin.blockSignals(True)
            self.day_total_spin.setValue(day["day_total_hours"])
            self.day_total_spin.blockSignals(False)

            self.table.setRowCount(0)
            for item in day["items"]:
                self.insert_table_row(item, day["day_total_hours"])

            self._loaded_date_key = date_key
            self.refresh_summary()
        finally:
            self.is_loading = False

    def insert_table_row(self, item, day_total_hours):
        row = self.table.rowCount()
        self.table.insertRow(row)

        start_edit = self.create_time_edit(item["start_time"])
        end_edit = self.create_time_edit(item["end_time"])
        task_edit = QLineEdit(item["task_text"])
        delete_button = QPushButton("删除")
        delete_button.setObjectName("Danger")

        item_id = item["id"]
        task_edit.setProperty("item_id", item_id)
        delete_button.setProperty("item_id", item_id)

        # 时间和文本变更即时进入持久化流程；加载期间由 is_loading 屏蔽。
        start_edit.timeChanged.connect(self.on_table_input_changed)
        end_edit.timeChanged.connect(self.on_table_input_changed)
        task_edit.textChanged.connect(self.on_table_input_changed)
        delete_button.clicked.connect(lambda _, value=item_id: self.delete_task_row(value))

        duration_widget = QWidget()
        duration_layout = QHBoxLayout(duration_widget)
        duration_layout.setContentsMargins(4, 2, 4, 2)
        duration_layout.setSpacing(4)

        duration_spin = QDoubleSpinBox()
        duration_spin.setRange(0.0, 24.0)
        duration_spin.setDecimals(2)
        duration_spin.setSuffix(" h")
        duration_spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        duration_spin.setKeyboardTracking(False)
        duration_spin.setProperty("item_id", item_id)
        duration_spin.setProperty("is_custom", item.get("custom_duration_hours") is not None)

        edit_button = QPushButton()
        edit_button.setIcon(get_refresh_icon())
        edit_button.setIconSize(QSize(14, 14))
        edit_button.setFixedWidth(28)
        edit_button.setToolTip("恢复按开始/结束时间自动计算")
        edit_button.setStyleSheet(
            "QPushButton { padding: 4px; background-color: transparent; border: 1px solid #dcdfe6; border-radius: 4px; } QPushButton:hover { background-color: #f5f7fa; }"
        )

        duration_layout.addWidget(duration_spin)
        duration_layout.addWidget(edit_button)

        percentage_item = QTableWidgetItem()
        percentage_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        percentage_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        registered_checkbox = QCheckBox()
        registered_checkbox.setStyleSheet("margin-left: 5px; margin-right: 5px;")
        checkbox_widget = QWidget()
        checkbox_layout = QHBoxLayout(checkbox_widget)
        checkbox_layout.setContentsMargins(0, 0, 0, 0)
        checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        checkbox_layout.addWidget(registered_checkbox)

        self.table.setCellWidget(row, 0, start_edit)
        self.table.setCellWidget(row, 1, end_edit)
        self.table.setCellWidget(row, 2, duration_widget)
        self.table.setItem(row, 3, percentage_item)
        self.table.setCellWidget(row, 4, checkbox_widget)
        self.table.setCellWidget(row, 5, task_edit)
        self.table.setCellWidget(row, 6, delete_button)

        registered_checkbox.stateChanged.connect(self.on_table_input_changed)
        duration_spin.editingFinished.connect(
            lambda value=item_id: self.mark_duration_custom_and_persist(value)
        )
        edit_button.clicked.connect(lambda *args, value=item_id: self.reset_duration(value))

        self.update_display_row(row, item, day_total_hours)

    def create_time_edit(self, time_text, fallback_text=DEFAULT_START_TIME):
        time_edit = QTimeEdit()
        time_edit.setDisplayFormat("HH:mm")
        time_edit.setTime(QTime.fromString(parse_time_text(time_text, fallback_text), "HH:mm"))
        time_edit.setKeyboardTracking(False)
        return time_edit

    def update_display_row(self, row, item, day_total_hours):
        start_text = item["start_time"]
        end_text = item["end_time"]
        lunch_settings = self.get_active_lunch_break_settings()
        duration_details = calculate_duration_details(
            start_text,
            end_text,
            lunch_settings["start_time"],
            lunch_settings["end_time"],
        )

        custom_duration = normalize_custom_duration(item.get("custom_duration_hours"))
        if custom_duration is not None:
            duration_hours = custom_duration
            is_valid_range = True
        else:
            duration_hours = duration_details["duration_hours"]
            is_valid_range = duration_details["is_valid_range"]

        percentage = calculate_percentage(duration_hours, day_total_hours)

        duration_widget = self.table.cellWidget(row, 2)
        duration_spin = duration_widget.findChild(QDoubleSpinBox)

        duration_spin.blockSignals(True)
        if custom_duration is not None:
            if duration_spin.value() != custom_duration:
                duration_spin.setValue(custom_duration)
            duration_spin.setProperty("is_custom", True)
        else:
            if duration_spin.value() != duration_hours:
                duration_spin.setValue(duration_hours)
            duration_spin.setProperty("is_custom", False)
        duration_spin.setEnabled(True)
        duration_spin.setStyleSheet(
            "QDoubleSpinBox { border: 1px solid #dcdfe6; border-radius: 4px; padding: 2px; }"
        )
        duration_spin.blockSignals(False)

        checkbox_widget = self.table.cellWidget(row, 4)
        if checkbox_widget:
            registered_checkbox = checkbox_widget.findChild(QCheckBox)
            registered_checkbox.blockSignals(True)
            registered_checkbox.setChecked(bool(item.get("is_registered")))
            registered_checkbox.blockSignals(False)

        percentage_item = self.table.item(row, 3)
        start_edit = self.table.cellWidget(row, 0)
        end_edit = self.table.cellWidget(row, 1)

        if is_valid_range:
            percentage_item.setText(f"{percentage:.2f}%")
            if custom_duration is None:
                duration_spin.setStyleSheet(
                    "QDoubleSpinBox { border: none; background: transparent; color: black; }"
                )
            percentage_item.setForeground(Qt.GlobalColor.black)
            start_edit.setStyleSheet("")
            end_edit.setStyleSheet("")

            if custom_duration is not None:
                tooltip = f"手动覆盖工时：{custom_duration:.2f} 小时；点击刷新按钮恢复自动计算。"
                duration_widget.setToolTip(tooltip)
                percentage_item.setToolTip(tooltip)
            elif duration_details["lunch_break_applied"]:
                tooltip = (
                    f"原始时长 {duration_details['raw_hours']:.2f} 小时，"
                    f"已跳过午休 {duration_details['lunch_break_hours']:.2f} 小时，"
                    f"计入 {duration_hours:.2f} 小时。"
                )
                duration_widget.setToolTip(tooltip)
                percentage_item.setToolTip(tooltip)
            else:
                duration_widget.setToolTip("")
                percentage_item.setToolTip("")
        else:
            percentage_item.setText("0.00%")
            duration_spin.setStyleSheet(
                "QDoubleSpinBox { border: none; background: transparent; color: #f56c6c; }"
            )
            percentage_item.setForeground(Qt.GlobalColor.red)
            invalid_style = "QTimeEdit { border: 1px solid #f56c6c; border-radius: 6px; padding: 6px 8px; }"
            start_edit.setStyleSheet(invalid_style)
            end_edit.setStyleSheet(invalid_style)
            tooltip = "结束时间必须晚于开始时间，该行暂按 0 小时处理。"
            duration_widget.setToolTip(tooltip)
            percentage_item.setToolTip(tooltip)

    def build_items_from_table(self, date_key=None):
        date_key = date_key or self._loaded_date_key or self.current_date_key()
        day_total_hours = round(float(self.day_total_spin.value()), 2)
        lunch_settings = self.get_active_lunch_break_settings()
        items = []

        for row in range(self.table.rowCount()):
            start_edit = self.table.cellWidget(row, 0)
            end_edit = self.table.cellWidget(row, 1)
            task_edit = self.table.cellWidget(row, 5)
            duration_widget = self.table.cellWidget(row, 2)
            duration_spin = duration_widget.findChild(QDoubleSpinBox)
            is_custom = bool(duration_spin.property("is_custom"))
            custom_duration = normalize_custom_duration(duration_spin.value()) if is_custom else None

            checkbox_widget = self.table.cellWidget(row, 4)
            registered_checkbox = checkbox_widget.findChild(QCheckBox) if checkbox_widget else None
            is_registered = registered_checkbox.isChecked() if registered_checkbox else False

            item = {
                "id": str(task_edit.property("item_id") or uuid.uuid4()),
                "date": date_key,
                "start_time": start_edit.time().toString("HH:mm"),
                "end_time": end_edit.time().toString("HH:mm"),
                "task_text": task_edit.text(),
                "is_registered": is_registered,
                "custom_duration_hours": custom_duration,
            }
            auto_duration = calculate_duration_hours(
                item["start_time"],
                item["end_time"],
                lunch_settings["start_time"],
                lunch_settings["end_time"],
            )
            item["duration_hours"] = custom_duration if custom_duration is not None else auto_duration
            items.append(item)
            self.update_display_row(row, item, day_total_hours)

        return items

    def persist_current_day(self, date_key=None):
        if self.is_loading:
            return

        date_key = date_key or self._loaded_date_key or self.current_date_key()
        lunch_settings = self.get_active_lunch_break_settings()
        day = ensure_day(
            self.data,
            date_key,
            lunch_settings["start_time"],
            lunch_settings["end_time"],
        )
        day["day_total_hours"] = round(float(self.day_total_spin.value()), 2)
        day["items"] = self.build_items_from_table(date_key)
        if date_key == self.current_date_key():
            self.refresh_summary()
        self.save_data()

    def save_data(self):
        try:
            save_worklog_data(self.data_file, self.data)
        except Exception as error:
            logger.exception("任务工时数据保存失败: %s", self.data_file)
            QMessageBox.critical(self, "保存失败", f"任务工时数据保存失败：\n{error}")

    def refresh_summary(self):
        date_key = self.current_date_key()
        lunch_settings = self.get_active_lunch_break_settings()
        day = ensure_day(
            self.data,
            date_key,
            lunch_settings["start_time"],
            lunch_settings["end_time"],
        )
        summary = summarize_day(
            day["items"],
            day["day_total_hours"],
            lunch_settings["start_time"],
            lunch_settings["end_time"],
        )

        summary_lines = [
            f"标准工时：<b>{day['day_total_hours']:.2f}</b> 小时",
            f"已记录：<b>{summary['total_hours']:.2f}</b> 小时",
            f"占用比例：<b>{summary['percentage']:.2f}%</b>",
            f"差值：<b>{summary['difference_hours']:.2f}</b> 小时",
            f"状态：<b style='color:{summary['color']};'>{summary['status']}</b>",
        ]

        if summary["lunch_break_valid"]:
            summary_lines.insert(
                1,
                f"全局午休：<b>{lunch_settings['start_time']}</b> - <b>{lunch_settings['end_time']}</b>",
            )
            if summary["lunch_break_applied_count"] > 0:
                summary_lines.append(
                    f"<span style='color:#409eff;'>已自动跳过午休 {summary['lunch_break_hours']:.2f} 小时，涉及 {summary['lunch_break_applied_count']} 条记录。</span>"
                )
        else:
            summary_lines.append(
                "<span style='color:#e6a23c;'>当前午休设置无效，系统暂不扣减午休时间。请确保结束时间晚于开始时间。</span>"
            )

        if summary["invalid_count"] > 0:
            summary_lines.append(
                f"<span style='color:#f56c6c;'>当前有 {summary['invalid_count']} 条记录的结束时间不晚于开始时间，暂按 0 小时计算。</span>"
            )
        elif day["items"]:
            custom_count = sum(
                1
                for item in day["items"]
                if normalize_custom_duration(item.get("custom_duration_hours")) is not None
            )
            if custom_count:
                summary_lines.append(
                    f"<span style='color:#409eff;'>当前有 {custom_count} 条记录使用手动工时覆盖，已实时保存。</span>"
                )
            else:
                summary_lines.append("<span style='color:#67c23a;'>当前所有任务时间范围有效，已实时保存。</span>")
        else:
            summary_lines.append("<span style='color:#909399;'>当前日期还没有任务记录。</span>")

        self.summary_card.setStyleSheet(
            f"QFrame#SummaryCard {{ background-color: #f7f9fc; border: 1px solid {summary['color']}; border-radius: 10px; }}"
        )
        self.summary_label.setText("<br>".join(summary_lines))

    def add_task_row(self):
        date_key = self.current_date_key()
        lunch_settings = self.get_active_lunch_break_settings()
        day = ensure_day(
            self.data,
            date_key,
            lunch_settings["start_time"],
            lunch_settings["end_time"],
        )
        start_time, end_time = get_next_task_time_range(
            day["items"],
            lunch_settings["start_time"],
            lunch_settings["end_time"],
        )
        item = create_task_item(
            date_key,
            start_time,
            end_time,
            lunch_start_text=lunch_settings["start_time"],
            lunch_end_text=lunch_settings["end_time"],
        )
        self.insert_table_row(item, self.day_total_spin.value())
        self.persist_current_day()

    def delete_task_row(self, item_id):
        self.persist_current_day()
        date_key = self._loaded_date_key or self.current_date_key()
        lunch_settings = self.get_active_lunch_break_settings()
        day = ensure_day(
            self.data,
            date_key,
            lunch_settings["start_time"],
            lunch_settings["end_time"],
        )
        day["items"] = [item for item in day["items"] if item.get("id") != item_id]
        self.save_data()
        self.load_current_date()

    def _find_row_by_item_id(self, item_id):
        for row in range(self.table.rowCount()):
            task_edit = self.table.cellWidget(row, 5)
            if task_edit and task_edit.property("item_id") == item_id:
                return row
        return -1

    def mark_duration_custom_and_persist(self, item_id):
        row = self._find_row_by_item_id(item_id)
        if row < 0:
            return
        duration_widget = self.table.cellWidget(row, 2)
        duration_spin = duration_widget.findChild(QDoubleSpinBox) if duration_widget else None
        if duration_spin:
            duration_spin.setProperty("is_custom", True)
        self.persist_current_day()

    def reset_duration(self, item_id):
        row = self._find_row_by_item_id(item_id)
        if row < 0:
            return
        duration_widget = self.table.cellWidget(row, 2)
        duration_spin = duration_widget.findChild(QDoubleSpinBox) if duration_widget else None
        if duration_spin:
            duration_spin.setProperty("is_custom", False)
        self.persist_current_day()

    def on_table_input_changed(self, *_args):
        self.persist_current_day()

    def on_day_total_changed(self, _value):
        self.persist_current_day()

    def on_lunch_break_changed(self, _time):
        if self.is_loading:
            return
        self.save_lunch_break_settings()
        self.recalculate_all_days()
        self.load_current_date()

    def on_date_changed(self, _date):
        if self.is_loading:
            return
        # date_edit 已经切到新日期，使用 _loaded_date_key 保存旧页面，避免串日。
        self.persist_current_day(self._loaded_date_key)
        self.load_current_date()

    def on_prev_date_clicked(self):
        self.date_edit.setDate(self.date_edit.date().addDays(-1))

    def on_next_date_clicked(self):
        self.date_edit.setDate(self.date_edit.date().addDays(1))
