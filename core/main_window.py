import logging
from PyQt6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                             QListWidget, QListWidgetItem, QStackedWidget,
                             QLabel, QPushButton, QFrame, QSizePolicy)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon
from core.app_paths import get_resource_path
from core.settings.settings_widget import SettingsWidget
from core.system_context import SystemContext


logger = logging.getLogger(__name__)


class _NavigationEntry:
    def __init__(self, plugin_id, name, icon):
        self.plugin_id = plugin_id
        self.name = name
        self.icon = icon

    def get_id(self):
        return self.plugin_id

    def get_name(self):
        return self.name

    def get_icon(self):
        return self.icon


class MainWindow(QMainWindow):
    SIDEBAR_EXPANDED_WIDTH = 220
    SIDEBAR_COLLAPSED_WIDTH = 60
    NAV_ITEM_HEIGHT = 46
    SYSTEM_PLUGIN_IDS = ("sys_settings", "sys_about")

    def __init__(self, config_manager, plugin_manager, system_context=None):
        super().__init__()
        self.config_manager = config_manager
        self.plugin_manager = plugin_manager
        if system_context is not None:
            self.system_context = system_context
        elif hasattr(plugin_manager, "get_system_context"):
            self.system_context = plugin_manager.get_system_context()
        else:
            self.system_context = SystemContext.create(
                app_settings=config_manager,
                plugin_manager=plugin_manager,
            )
        self.plugin_widgets = {} # plugin_id -> QWidget (in stacked widget)
        self.system_entries = {}
        self._sidebar_expanded = True
        
        self.initUI()
        self.load_plugins_to_ui()

    def initUI(self):
        self.setWindowTitle('ToolX')
        self.setWindowIcon(QIcon(get_resource_path("assets/app_icon.ico")))
        
        # 恢复窗口大小
        w, h = self.config_manager.get("window_size", [900, 600])
        self.resize(w, h)
        
        # 现代简约主题 QSS
        self.setStyleSheet("""
            QMainWindow {
                background-color: #ffffff;
            }
            #Sidebar {
                background-color: #f5f7fa;
                border-right: 1px solid #e4e7ed;
            }
            QListWidget#PluginNavigation,
            QListWidget#SystemNavigation {
                background-color: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item {
                padding: 11px 16px;
                border-radius: 6px;
                margin: 3px 8px;
                color: #606266;
                font-size: 15px;
            }
            QListWidget::item:hover {
                background-color: #e4e7ed;
                color: #303133;
            }
            QListWidget::item:selected {
                background-color: #409eff;
                color: white;
                font-weight: bold;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 4px 2px 4px 0;
            }
            QScrollBar::handle:vertical {
                background: #c8d0db;
                border-radius: 3px;
                min-height: 24px;
            }
            QScrollBar::handle:vertical:hover {
                background: #aeb8c6;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0;
            }
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: transparent;
            }
            QFrame#SidebarDivider {
                background-color: #e9edf2;
                border: none;
                max-height: 1px;
            }
            QPushButton#SidebarToggle {
                border: 1px solid #e6ebf1;
                border-radius: 8px;
                font-size: 24px;
                color: #606266;
                background-color: #eef2f6;
            }
            QPushButton#SidebarToggle:hover {
                border-color: #dce5ee;
                color: #409eff;
                background-color: #e5ebf2;
            }
            QPushButton#SidebarToggle:pressed {
                border-color: #d4dfe9;
                background-color: #dce5ee;
            }
        """)

        # 主窗口中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ====== 左侧边栏 ======
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(self.SIDEBAR_EXPANDED_WIDTH)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 10, 0, 8)
        sidebar_layout.setSpacing(0)

        # 上方只放普通插件，列表占据剩余空间并在插件过多时滚动。
        self.nav_list = self._create_navigation_list(
            "PluginNavigation", scroll_bar_policy=Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.nav_list.currentRowChanged.connect(self.switch_page)

        # 下方系统入口不参与伸缩，始终贴在侧边栏底部。
        self.system_nav_list = self._create_navigation_list(
            "SystemNavigation", scroll_bar_policy=Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.system_nav_list.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.system_nav_list.currentRowChanged.connect(self.switch_system_page)

        sidebar_divider = QFrame()
        sidebar_divider.setObjectName("SidebarDivider")
        sidebar_divider.setFrameShape(QFrame.Shape.NoFrame)
        sidebar_divider.setFixedHeight(1)

        # 只保留一个位于底部的折叠按钮，按钮占满可用宽度以扩大点击区域。
        sidebar_footer = QWidget()
        self.sidebar_footer_layout = QHBoxLayout(sidebar_footer)
        self.sidebar_footer_layout.setContentsMargins(8, 8, 8, 2)
        self.sidebar_footer_layout.setSpacing(0)

        self.btn_toggle = QPushButton("‹")
        self.btn_toggle.setObjectName("SidebarToggle")
        self.btn_toggle.setFixedHeight(44)
        self.btn_toggle.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle.setToolTip("收起侧边栏")
        self.btn_toggle.clicked.connect(self.toggle_sidebar)

        self.sidebar_footer_layout.addWidget(self.btn_toggle)

        sidebar_layout.addWidget(self.nav_list, 1)
        sidebar_layout.addWidget(sidebar_divider)
        sidebar_layout.addWidget(self.system_nav_list)
        sidebar_layout.addWidget(sidebar_footer)
        
        # ====== 右侧内容区 ======
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet("background-color: #ffffff;")

        # 空白欢迎页
        welcome_page = QWidget()
        welcome_layout = QVBoxLayout(welcome_page)
        welcome_label = QLabel("欢迎使用 ToolX\n请在左侧选择一个工具开始工作")
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_label.setStyleSheet("color: #909399; font-size: 16px;")
        welcome_layout.addWidget(welcome_label)
        self.stacked_widget.addWidget(welcome_page)

        # 添加到主布局
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.stacked_widget)
        
    def toggle_sidebar(self):
        self._sidebar_expanded = not self._sidebar_expanded
        new_width = (
            self.SIDEBAR_EXPANDED_WIDTH
            if self._sidebar_expanded
            else self.SIDEBAR_COLLAPSED_WIDTH
        )
        self.sidebar.setFixedWidth(new_width)
        self._apply_sidebar_state()

    def _create_navigation_list(self, object_name, scroll_bar_policy):
        nav_list = QListWidget()
        nav_list.setObjectName(object_name)
        nav_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        nav_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        nav_list.setVerticalScrollBarPolicy(scroll_bar_policy)
        nav_list.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        nav_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        return nav_list

    def _apply_sidebar_state(self):
        expanded = self._sidebar_expanded
        self.btn_toggle.setFixedHeight(44)
        self.btn_toggle.setMinimumWidth(0)
        self.btn_toggle.setMaximumWidth(16777215)
        self.btn_toggle.setText("‹" if expanded else "›")
        self.btn_toggle.setToolTip("收起侧边栏" if expanded else "展开侧边栏")
        if expanded:
            self.sidebar_footer_layout.setContentsMargins(8, 8, 8, 2)
        else:
            self.sidebar_footer_layout.setContentsMargins(6, 8, 6, 2)

        for nav_list in (self.nav_list, self.system_nav_list):
            if expanded:
                nav_list.setStyleSheet("")
            else:
                nav_list.setStyleSheet(
                    "QListWidget::item { padding: 10px 0px; margin: 2px 5px; }"
                )
            self._refresh_navigation_list(nav_list)

    def _refresh_navigation_list(self, nav_list):
        for row in range(nav_list.count()):
            item = nav_list.item(row)
            p_id = item.data(Qt.ItemDataRole.UserRole)
            plugin = self.system_entries.get(p_id)
            if plugin is None:
                plugin = self.plugin_manager.get_plugin(p_id)
            if plugin:
                self._set_navigation_item_display(item, plugin)

    def _set_navigation_item_display(self, item, plugin):
        icon = plugin.get_icon()
        name = plugin.get_name()
        if isinstance(icon, QIcon):
            item.setIcon(icon)
            icon_text = ""
        else:
            item.setIcon(QIcon())
            icon_text = "" if icon is None else str(icon)

        if self._sidebar_expanded:
            item.setText(f"{icon_text}  {name}" if icon_text else name)
            item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            item.setToolTip("")
        else:
            item.setText(icon_text)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setToolTip(name)

    def load_plugins_to_ui(self):
        """将加载的插件添加到侧边栏和堆叠区域"""
        plugins = self.plugin_manager.get_plugins()
        pinned = self.config_manager.get("pinned_plugins", [])

        # 优先显示 pinned 的普通工具；系统入口始终只出现在底部。
        for p_id in pinned:
            if p_id in plugins and p_id not in self.SYSTEM_PLUGIN_IDS:
                self.add_plugin_item(plugins[p_id], self.nav_list)

        # 显示其它普通工具
        for p_id, plugin in plugins.items():
            if p_id not in pinned and p_id not in self.SYSTEM_PLUGIN_IDS:
                self.add_plugin_item(plugin, self.nav_list)

        # 系统入口由核心直接注册，不依赖普通插件扫描结果。
        self.add_system_page(
            "sys_settings",
            "设置",
            "⚙️",
            lambda parent: SettingsWidget(self.system_context, parent),
        )

        self._resize_system_navigation()

        # 如果有插件，默认选中第一个普通插件；没有普通插件时选设置入口。
        if self.nav_list.count() > 0:
            self.nav_list.setCurrentRow(0)
        elif self.system_nav_list.count() > 0:
            self.system_nav_list.setCurrentRow(0)

    def add_system_page(self, page_id, name, icon, factory):
        if page_id in self.plugin_widgets:
            return False
        try:
            widget = factory(self)
            if not isinstance(widget, QWidget):
                raise TypeError("核心页面 factory 必须返回 QWidget 实例")
            self.stacked_widget.addWidget(widget)
            entry = _NavigationEntry(page_id, name, icon)
            self.system_entries[page_id] = entry
            self.plugin_widgets[page_id] = widget
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, self.NAV_ITEM_HEIGHT))
            item.setData(Qt.ItemDataRole.UserRole, page_id)
            self.system_nav_list.addItem(item)
            self._set_navigation_item_display(item, entry)
            return True
        except Exception:
            logger.exception("核心页面 %s 创建失败", page_id)
            return False

    def add_plugin_item(self, plugin, nav_list=None):
        if nav_list is None:
            nav_list = self.nav_list
        p_id = "<unknown>"
        try:
            p_id = plugin.get_id()
            if p_id in self.plugin_widgets:
                return False  # 已经添加过了

            # 插件页面创建失败时只跳过该插件，不能拖垮主窗口。
            widget = plugin.get_widget(self)
            if not isinstance(widget, QWidget):
                raise TypeError("get_widget() 必须返回 QWidget 实例")
            self.stacked_widget.addWidget(widget)
            self.plugin_widgets[p_id] = widget

            item = QListWidgetItem()
            item.setSizeHint(QSize(0, self.NAV_ITEM_HEIGHT))
            item.setData(Qt.ItemDataRole.UserRole, p_id)
            nav_list.addItem(item)
            self._set_navigation_item_display(item, plugin)
            return True
        except Exception:
            logger.exception("插件页面创建失败：%s，已跳过该插件", p_id)
            return False

    def switch_page(self, row):
        self._switch_page(self.nav_list, row)

    def switch_system_page(self, row):
        self._switch_page(self.system_nav_list, row)

    def _switch_page(self, source_list, row):
        if row < 0:
            return
        item = source_list.item(row)
        if item is None:
            return
        p_id = item.data(Qt.ItemDataRole.UserRole)

        if p_id in self.plugin_widgets:
            for nav_list in (self.nav_list, self.system_nav_list):
                if nav_list is source_list:
                    continue
                nav_list.blockSignals(True)
                try:
                    nav_list.clearSelection()
                    nav_list.setCurrentRow(-1)
                finally:
                    nav_list.blockSignals(False)

            widget = self.plugin_widgets[p_id]
            self.stacked_widget.setCurrentWidget(widget)

    def _resize_system_navigation(self):
        if self.system_nav_list.count() == 0:
            self.system_nav_list.setFixedHeight(0)
            return
        self.system_nav_list.setFixedHeight(
            self.system_nav_list.count() * self.NAV_ITEM_HEIGHT + 4
        )

    def closeEvent(self, event):
        # 记住窗口尺寸
        self.config_manager.set("window_size", [self.width(), self.height()])
        self.plugin_manager.unload_all()
        super().closeEvent(event)
