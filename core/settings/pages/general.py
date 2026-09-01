from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


class GeneralPage(QWidget):
    def __init__(self, system_context, parent=None):
        super().__init__(parent)
        self.system_context = system_context
        layout = QVBoxLayout(self)
        title = QLabel("基础设置")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        layout.addWidget(QLabel("ToolX 应用配置、窗口和插件布局由核心统一管理。"))
        layout.addStretch(1)

    def apply(self):
        return True

    def reset(self):
        return True
