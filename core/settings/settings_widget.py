import logging

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.plugin_interface import SettingsPage
from .pages.about import AboutPage
from .pages.appearance import AppearancePage
from .pages.general import GeneralPage
from .pages.plugin_manager import PluginManagerPage
from .pages.startup import StartupPage
from core.system_context import SystemContext


logger = logging.getLogger(__name__)


class SettingsWidget(QWidget):
    """IDE-style settings tree for application and plugin settings."""

    applied = pyqtSignal()

    def __init__(self, system_context=None, parent=None):
        super().__init__(parent)
        if isinstance(system_context, SystemContext):
            self.system_context = system_context
        elif system_context is not None and hasattr(system_context, "get"):
            # Compatibility for callers of the old settings plugin.  The
            # resulting system context still exposes no manager to plugins.
            self.system_context = SystemContext.create(app_settings=system_context)
        else:
            self.system_context = SystemContext.create()
        self.page_widgets = {}
        self.page_definitions = {}
        self._tree_nodes = {}
        self._build_ui()
        self._register_pages()

    def _build_ui(self):
        self.setObjectName("SettingsWidget")
        self.setStyleSheet(
            """
            QWidget#SettingsWidget { background-color: #ffffff; }
            QLineEdit#SettingsSearch { padding: 7px 9px; border: 1px solid #dcdfe6; border-radius: 5px; }
            QTreeWidget#SettingsTree { border: none; border-right: 1px solid #ebeef5; }
            QLabel#PageTitle { font-size: 20px; font-weight: bold; color: #303133; }
            QLabel#Status { color: #606266; }
            """
        )
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 12)
        outer.setSpacing(10)

        self.search_edit = QLineEdit()
        self.search_edit.setObjectName("SettingsSearch")
        self.search_edit.setPlaceholderText("搜索设置")
        self.search_edit.textChanged.connect(self._filter_tree)
        outer.addWidget(self.search_edit)

        content = QHBoxLayout()
        content.setSpacing(0)
        self.settings_tree = QTreeWidget()
        self.settings_tree.setObjectName("SettingsTree")
        self.settings_tree.setHeaderHidden(True)
        self.settings_tree.setMinimumWidth(190)
        self.settings_tree.setMaximumWidth(280)
        self.settings_tree.currentItemChanged.connect(self._on_tree_selection_changed)
        self.settings_stack = QStackedWidget()
        self.settings_stack.setObjectName("SettingsContent")
        content.addWidget(self.settings_tree)
        content.addWidget(self.settings_stack, 1)
        outer.addLayout(content, 1)

        self.status_label = QLabel()
        self.status_label.setObjectName("Status")
        outer.addWidget(self.status_label)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.reset_button = QPushButton("恢复默认")
        self.cancel_button = QPushButton("取消")
        self.apply_button = QPushButton("应用")
        self.ok_button = QPushButton("确定")
        self.reset_button.clicked.connect(self.reset_current_page)
        self.cancel_button.clicked.connect(self.cancel_changes)
        self.apply_button.clicked.connect(self.apply_changes)
        self.ok_button.clicked.connect(self.apply_changes)
        buttons.addWidget(self.reset_button)
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.apply_button)
        buttons.addWidget(self.ok_button)
        outer.addLayout(buttons)

    def _core_page_definitions(self):
        context = self.system_context
        return [
            SettingsPage("general", "常规", ("基础设置",), lambda parent: GeneralPage(context, parent)),
            SettingsPage("appearance", "外观与主题", ("基础设置",), lambda parent: AppearancePage(context, parent)),
            SettingsPage("startup", "启动行为", ("基础设置",), lambda parent: StartupPage(context, parent)),
            SettingsPage(
                "plugin_manager",
                "插件管理",
                ("插件",),
                lambda parent: PluginManagerPage(context, parent),
            ),
            SettingsPage("about", "关于 ToolX", (), lambda parent: AboutPage(context, parent)),
        ]

    def _register_pages(self):
        pages = self._core_page_definitions()
        try:
            pages.extend(self.system_context.plugin_settings.list_pages())
        except Exception:
            logger.exception("读取插件设置页失败")

        for page in pages:
            if not isinstance(page, SettingsPage):
                continue
            key = "%s:%s" % (page.plugin_id or "core", page.page_id)
            if key in self.page_definitions:
                logger.warning("设置页 ID 重复，已跳过: %s", key)
                continue
            try:
                widget = page.create_widget(self.settings_stack)
                if not isinstance(widget, QWidget):
                    raise TypeError("设置页 factory 必须返回 QWidget")
            except Exception:
                logger.exception("创建设置页失败: %s", key)
                continue
            self.page_definitions[key] = page
            self.page_widgets[key] = widget
            self.settings_stack.addWidget(widget)
            self._add_tree_item(page.path, page.title, key)

        if self.settings_tree.topLevelItemCount():
            first = self.settings_tree.topLevelItem(0)
            if first.childCount():
                self.settings_tree.setCurrentItem(first.child(0))
            else:
                self.settings_tree.setCurrentItem(first)

    def _add_tree_item(self, path, title, key):
        path = tuple(path or ())
        if not path:
            item = QTreeWidgetItem([str(title)])
            item.setData(0, Qt.ItemDataRole.UserRole, key)
            self.settings_tree.addTopLevelItem(item)
            return
        parent = None
        accumulated = []
        for component in path:
            accumulated.append(component)
            node_key = tuple(accumulated)
            node = self._tree_nodes.get(node_key)
            if node is None:
                node = QTreeWidgetItem([str(component)])
                if parent is None:
                    self.settings_tree.addTopLevelItem(node)
                else:
                    parent.addChild(node)
                node.setExpanded(True)
                self._tree_nodes[node_key] = node
            parent = node

        item = QTreeWidgetItem([str(title)])
        item.setData(0, Qt.ItemDataRole.UserRole, key)
        parent.addChild(item)

    def _on_tree_selection_changed(self, current, _previous):
        if current is None:
            return
        key = current.data(0, Qt.ItemDataRole.UserRole)
        if key in self.page_widgets:
            self.settings_stack.setCurrentWidget(self.page_widgets[key])

    def _filter_tree(self, text):
        text = text.strip().lower()

        def visit(item):
            own_match = not text or text in item.text(0).lower()
            child_match = False
            for index in range(item.childCount()):
                child_match = visit(item.child(index)) or child_match
            visible = own_match or child_match
            item.setHidden(not visible)
            return visible

        for index in range(self.settings_tree.topLevelItemCount()):
            visit(self.settings_tree.topLevelItem(index))

    def _current_page(self):
        item = self.settings_tree.currentItem()
        key = item.data(0, Qt.ItemDataRole.UserRole) if item is not None else None
        return key, self.page_widgets.get(key)

    def apply_changes(self):
        for key, widget in self.page_widgets.items():
            apply_method = getattr(widget, "apply", None)
            if not callable(apply_method):
                continue
            try:
                if apply_method() is False:
                    self.status_label.setText("设置页校验失败：%s" % key)
                    return False
            except Exception as error:
                logger.exception("应用设置页失败: %s", key)
                self.status_label.setText("应用设置失败：%s" % error)
                return False
        self.status_label.setText("设置已应用。")
        self.applied.emit()
        return True

    def reset_current_page(self):
        _key, widget = self._current_page()
        reset_method = getattr(widget, "reset", None) if widget is not None else None
        if callable(reset_method):
            reset_method()
            self.status_label.setText("当前设置页已恢复默认值，请点击应用保存。")

    def cancel_changes(self):
        for widget in self.page_widgets.values():
            load_method = getattr(widget, "load", None)
            if callable(load_method):
                load_method()
        self.status_label.setText("已取消未应用的修改。")

    def get_page_widget(self, plugin_id, page_id):
        return self.page_widgets.get("%s:%s" % (plugin_id, page_id))
