from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from core.app_paths import get_resource_path
from core.plugin_context import TOOLX_VERSION


class AboutPage(QWidget):
    """Core system information page; it is not a feature plugin."""

    LOGO_SIZE = QSize(112, 112)

    def __init__(self, system_context=None, parent=None):
        super().__init__(parent)
        self.system_context = system_context
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet(
            """
            QWidget { background-color: #ffffff; font-family: 'Segoe UI', 'Microsoft YaHei'; }
            QLabel#Title { font-size: 24px; font-weight: bold; color: #409eff; margin-bottom: 10px; }
            QLabel#Logo { background-color: transparent; margin-bottom: 8px; }
            QLabel#Version { font-size: 14px; color: #909399; margin-bottom: 20px; }
            QLabel#Desc { font-size: 15px; color: #606266; line-height: 1.5; }
            """
        )
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        logo = QLabel()
        logo.setObjectName("Logo")
        logo.setAccessibleName("ToolX logo")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setFixedSize(self.LOGO_SIZE)
        logo_pixmap = QPixmap(get_resource_path("assets/app_icon.png"))
        if logo_pixmap.isNull():
            logo.setText("ToolX")
        else:
            logo.setPixmap(
                logo_pixmap.scaled(
                    self.LOGO_SIZE,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

        title = QLabel("ToolX")
        title.setObjectName("Title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version = QLabel("Version %s" % TOOLX_VERSION)
        version.setObjectName("Version")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc = QLabel(
            "一个基于 PyQt6 构建的现代、可扩展的插件化桌面工具箱。<br>"
            "致力于将常用的独立小脚本和小工具整合在一个统一、美观的界面中。<br><br>"
            "支持通过 plugin.json 管理内置或用户导入插件。<br><br>"
            "开源地址：<a href='https://github.com/AkenClub/toolx'>https://github.com/AkenClub/toolx</a><br>"
            "开源协议：MIT License"
        )
        desc.setTextFormat(Qt.TextFormat.RichText)
        desc.setOpenExternalLinks(True)
        desc.setObjectName("Desc")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(logo, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        layout.addWidget(version)
        layout.addWidget(desc)
