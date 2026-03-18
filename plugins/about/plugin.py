from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
from core.plugin_interface import PluginInterface

class AboutWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                font-family: 'Segoe UI', 'Microsoft YaHei';
            }
            QLabel#Title {
                font-size: 24px;
                font-weight: bold;
                color: #409eff;
                margin-bottom: 10px;
            }
            QLabel#Version {
                font-size: 14px;
                color: #909399;
                margin-bottom: 20px;
            }
            QLabel#Desc {
                font-size: 15px;
                color: #606266;
                line-height: 1.5;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        title = QLabel("🧰 ToolX")
        title.setObjectName("Title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        version = QLabel("Version 1.0.0")
        version.setObjectName("Version")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        desc = QLabel("一个基于 PyQt6 构建的现代、可扩展的插件化桌面工具箱。<br>"
                      "致力于将常用的独立小脚本和小工具整合在一个统一、美观的界面中。<br><br>"
                      "支持通过 importlib 动态按需加载自研或第三方插件。<br><br>"
                      "开源地址：<a href='https://github.com/AkenClub/toolx'>https://github.com/AkenClub/toolx</a><br>"
                      "开源协议：MIT License")
        desc.setTextFormat(Qt.TextFormat.RichText)
        desc.setOpenExternalLinks(True)
        desc.setObjectName("Desc")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(title)
        layout.addWidget(version)
        layout.addWidget(desc)


class AboutPlugin(PluginInterface):
    def __init__(self, config_manager=None):
        super().__init__(config_manager)
        self.widget = None

    def get_id(self) -> str:
        return "sys_about"

    def get_name(self) -> str:
        return "关于本软件"

    def get_icon(self):
        return "ℹ️"

    def get_widget(self, parent: QWidget) -> QWidget:
        if self.widget is None:
            self.widget = AboutWidget(parent)
        return self.widget

def get_plugin(config_manager):
    return AboutPlugin(config_manager)
