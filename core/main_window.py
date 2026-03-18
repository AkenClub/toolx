import sys
from PyQt6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                             QListWidget, QListWidgetItem, QStackedWidget,
                             QLabel, QPushButton, QFrame, QApplication)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QFont

class MainWindow(QMainWindow):
    def __init__(self, config_manager, plugin_manager):
        super().__init__()
        self.config_manager = config_manager
        self.plugin_manager = plugin_manager
        self.plugin_widgets = {} # plugin_id -> QWidget (in stacked widget)
        
        self.initUI()
        self.load_plugins_to_ui()

    def initUI(self):
        self.setWindowTitle('ToolX')
        
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
            QListWidget {
                background-color: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item {
                padding: 12px 15px;
                border-radius: 6px;
                margin: 2px 10px;
                color: #606266;
                font-size: 14px;
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
            QLabel#Logo {
                font-size: 18px;
                font-weight: bold;
                color: #303133;
                padding: 20px 10px;
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
        self.sidebar.setFixedWidth(220)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 10)
        sidebar_layout.setSpacing(0)

        # 侧边栏头部
        sidebar_header = QWidget()
        sidebar_header.setFixedHeight(60)
        sidebar_header_layout = QHBoxLayout(sidebar_header)
        sidebar_header_layout.setContentsMargins(10, 0, 10, 0)
        sidebar_header_layout.setSpacing(10)
        
        self.btn_toggle = QPushButton("☰")
        self.btn_toggle.setFixedSize(40, 40)
        self.btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle.setStyleSheet("QPushButton { border: none; font-size: 20px; color: #606266; } QPushButton:hover { color: #409eff; }")
        self.btn_toggle.clicked.connect(self.toggle_sidebar)
        
        self.logo_label = QLabel("🧰 ToolX")
        self.logo_label.setObjectName("Logo")
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        
        sidebar_header_layout.addWidget(self.logo_label)
        sidebar_header_layout.addStretch()
        sidebar_header_layout.addWidget(self.btn_toggle)
        
        # 插件导航列表
        self.nav_list = QListWidget()
        self.nav_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.nav_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.nav_list.currentRowChanged.connect(self.switch_page)

        sidebar_layout.addWidget(sidebar_header)
        sidebar_layout.addWidget(self.nav_list)
        
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
        is_expanded = self.sidebar.width() == 220
        new_width = 60 if is_expanded else 220
        self.sidebar.setFixedWidth(new_width)
        self.logo_label.setVisible(not is_expanded)
        
        if is_expanded:
            self.nav_list.setStyleSheet("QListWidget::item { padding: 12px 0px; margin: 2px 5px; text-align: center; }")
        else:
            self.nav_list.setStyleSheet("")
            
        for i in range(self.nav_list.count()):
            item = self.nav_list.item(i)
            p_id = item.data(Qt.ItemDataRole.UserRole)
            plugin = self.plugin_manager.get_plugin(p_id)
            if plugin:
                if is_expanded:
                    item.setText(plugin.get_icon())
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    item.setToolTip(plugin.get_name())
                else:
                    item.setText(f"{plugin.get_icon()}  {plugin.get_name()}")
                    item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                    item.setToolTip("")

    def load_plugins_to_ui(self):
        """将加载的插件添加到侧边栏和堆叠区域"""
        plugins = self.plugin_manager.get_plugins()
        pinned = self.config_manager.get("pinned_plugins", [])
        
        # 优先显示 pinned 工具
        for p_id in pinned:
            if p_id in plugins:
                self.add_plugin_item(plugins[p_id])
                
        # 显示其它工具
        for p_id, plugin in plugins.items():
            if p_id not in pinned:
                # 排除 settings 等特殊系统级插件暂时放这，稍后可特殊处理
                self.add_plugin_item(plugin)
                
        # 如果有插件，默认选中第一个
        if self.nav_list.count() > 0:
            self.nav_list.setCurrentRow(0)

    def add_plugin_item(self, plugin):
        p_id = plugin.get_id()
        if p_id in self.plugin_widgets:
            return # 已经添加过了
            
        # 1. 获取并添加 Widget 到 StackedWidget
        widget = plugin.get_widget(self)
        self.stacked_widget.addWidget(widget)
        self.plugin_widgets[p_id] = widget
        
        # 2. 添加到侧边栏
        item = QListWidgetItem()
        if self.sidebar.width() == 60:
            item.setText(plugin.get_icon())
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setToolTip(plugin.get_name())
        else:
            item.setText(f"{plugin.get_icon()}  {plugin.get_name()}")
            item.setToolTip("")
        item.setData(Qt.ItemDataRole.UserRole, p_id)
        self.nav_list.addItem(item)

    def switch_page(self, row):
        if row < 0:
            return
        item = self.nav_list.item(row)
        p_id = item.data(Qt.ItemDataRole.UserRole)
        
        if p_id in self.plugin_widgets:
            widget = self.plugin_widgets[p_id]
            self.stacked_widget.setCurrentWidget(widget)

    def closeEvent(self, event):
        # 记住窗口尺寸
        self.config_manager.set("window_size", [self.width(), self.height()])
        self.plugin_manager.unload_all()
        super().closeEvent(event)
