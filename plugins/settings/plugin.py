from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
from core.plugin_interface import PluginInterface

class SettingsWidget(QWidget):
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.initUI()

    def initUI(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                font-family: 'Segoe UI', 'Microsoft YaHei';
            }
            QLabel#Title {
                font-size: 20px;
                font-weight: bold;
                color: #303133;
                margin-bottom: 20px;
            }
            QLabel {
                font-size: 14px;
                color: #606266;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        
        title = QLabel("⚙️ 设置 (Settings)")
        title.setObjectName("Title")
        
        desc = QLabel("这里是全局设置页面，未来可以添加诸如：\n- 主题切换 (浅色/深色)\n- 开机自启\n- 插件管理开关等功能")
        desc.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        layout.addWidget(title)
        layout.addWidget(desc)
        layout.addStretch(1)


class SettingsPlugin(PluginInterface):
    def __init__(self, config_manager):
        super().__init__(config_manager)
        self.widget = None

    def get_id(self) -> str:
        return "sys_settings"

    def get_name(self) -> str:
        return "系统设置"

    def get_icon(self):
        return "⚙️"

    def get_widget(self, parent: QWidget) -> QWidget:
        if self.widget is None:
            self.widget = SettingsWidget(self.config_manager, parent)
        return self.widget

def get_plugin(config_manager):
    return SettingsPlugin(config_manager)
