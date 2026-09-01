from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


class StartupPage(QWidget):
    def __init__(self, system_context, parent=None):
        super().__init__(parent)
        self.system_context = system_context
        layout = QVBoxLayout(self)
        title = QLabel("启动行为")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        layout.addWidget(QLabel("启动项设置将在后续版本接入。插件启用状态修改后下次启动生效。"))
        layout.addStretch(1)

    def apply(self):
        return True

    def reset(self):
        return True
