from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class PluginManagerPage(QWidget):
    """Basic lifecycle controls for ordinary plugins."""

    def __init__(self, system_context, parent=None):
        super().__init__(parent)
        self.system_context = system_context
        layout = QVBoxLayout(self)
        title = QLabel("插件管理")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        self.plugin_list = QListWidget()
        self.plugin_list.setObjectName("PluginList")
        self.plugin_list.currentItemChanged.connect(self._update_button_state)
        layout.addWidget(self.plugin_list, 1)

        self.status_label = QLabel()
        self.status_label.setObjectName("Status")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        actions = QHBoxLayout()
        self.import_button = QPushButton("导入插件")
        self.enable_button = QPushButton("启用")
        self.disable_button = QPushButton("禁用")
        self.uninstall_button = QPushButton("卸载")
        self.uninstall_clean_button = QPushButton("卸载并清理")
        self.clear_data_button = QPushButton("清理数据")
        actions.addWidget(self.import_button)
        actions.addWidget(self.enable_button)
        actions.addWidget(self.disable_button)
        actions.addWidget(self.uninstall_button)
        actions.addWidget(self.uninstall_clean_button)
        actions.addWidget(self.clear_data_button)
        layout.addLayout(actions)

        self.import_button.clicked.connect(self.import_package)
        self.enable_button.clicked.connect(self.enable_selected)
        self.disable_button.clicked.connect(self.disable_selected)
        self.uninstall_button.clicked.connect(self.uninstall_selected)
        self.uninstall_clean_button.clicked.connect(self.uninstall_and_clear_selected)
        self.clear_data_button.clicked.connect(self.clear_selected_data)
        self.refresh()

    def _selected_id(self):
        item = self.plugin_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    def _update_button_state(self, *_args):
        enabled = self._selected_id() is not None
        self.enable_button.setEnabled(enabled)
        self.disable_button.setEnabled(enabled)
        self.uninstall_button.setEnabled(enabled)
        self.uninstall_clean_button.setEnabled(enabled)
        self.clear_data_button.setEnabled(enabled)

    def refresh(self):
        selected_id = self._selected_id()
        self.plugin_list.clear()
        for record in self.system_context.plugin_admin.list_installed():
            plugin_id = record.get("id", "")
            source = "内置" if record.get("source") == "builtin" else "用户"
            state = "已启用" if record.get("enabled", True) else "已禁用"
            item = QListWidgetItem(
                "%s  %s  (%s, %s)"
                % (record.get("name", plugin_id), record.get("version", ""), source, state)
            )
            item.setData(Qt.ItemDataRole.UserRole, plugin_id)
            item.setToolTip(record.get("description", "") or plugin_id)
            self.plugin_list.addItem(item)
            if plugin_id == selected_id:
                self.plugin_list.setCurrentItem(item)
        self._update_button_state()

    def _run_admin_action(self, action, success_message):
        plugin_id = self._selected_id()
        if not plugin_id:
            return False
        try:
            action(plugin_id)
        except Exception as error:
            self.status_label.setText(str(error))
            return False
        self.status_label.setText(success_message + "，重启 ToolX 后生效。")
        self.refresh()
        return True

    def import_package(self, package_path=None):
        if not package_path:
            package_path, _ = QFileDialog.getOpenFileName(
                self, "导入 ToolX 插件", "", "ToolX 插件 (*.toolx-plugin *.zip)"
            )
        if not package_path:
            return None
        try:
            manifest = self.system_context.plugin_admin.install_package(package_path)
        except Exception as error:
            self.status_label.setText(str(error))
            return None
        self.status_label.setText("已安装 %s，重启 ToolX 后生效。" % manifest.name)
        self.refresh()
        return manifest

    def enable_selected(self):
        return self._run_admin_action(
            self.system_context.plugin_admin.enable,
            "插件已启用",
        )

    def disable_selected(self):
        return self._run_admin_action(
            self.system_context.plugin_admin.disable,
            "插件已禁用",
        )

    def uninstall_selected(self):
        plugin_id = self._selected_id()
        if not plugin_id:
            return False
        record = self.system_context.plugin_admin.get_plugin(plugin_id) or {}
        if record.get("source") == "builtin":
            self.status_label.setText("内置插件不能卸载。")
            return False
        answer = QMessageBox.question(
            self,
            "确认卸载",
            "卸载后将移除插件代码，但默认保留配置和业务数据。继续吗？",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return False
        return self._run_admin_action(
            self.system_context.plugin_admin.uninstall,
            "插件已卸载",
        )

    def clear_selected_data(self):
        plugin_id = self._selected_id()
        if not plugin_id:
            return False
        answer = QMessageBox.question(
            self,
            "确认清理数据",
            "这会删除插件配置、业务数据和缓存，且通常无法恢复。继续吗？",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return False
        try:
            self.system_context.plugin_admin.clear_data(plugin_id, confirmed=True)
        except Exception as error:
            self.status_label.setText(str(error))
            return False
        self.status_label.setText("插件数据已清理。")
        return True

    def uninstall_and_clear_selected(self):
        plugin_id = self._selected_id()
        if not plugin_id:
            return False
        record = self.system_context.plugin_admin.get_plugin(plugin_id) or {}
        if record.get("source") == "builtin":
            self.status_label.setText("内置插件不能卸载。")
            return False
        answer = QMessageBox.question(
            self,
            "确认卸载并清理",
            "这会删除插件代码、配置、业务数据和缓存，且通常无法恢复。继续吗？",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return False
        try:
            self.system_context.plugin_admin.uninstall_and_clear(
                plugin_id, confirmed=True
            )
        except Exception as error:
            self.status_label.setText(str(error))
            return False
        self.status_label.setText("插件及其数据已卸载清理。")
        self.refresh()
        return True

    def apply(self):
        return True

    def reset(self):
        self.refresh()
        return True
