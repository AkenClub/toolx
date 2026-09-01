from PyQt6.QtWidgets import QComboBox, QLabel, QVBoxLayout, QWidget


class AppearancePage(QWidget):
    def __init__(self, system_context, parent=None):
        super().__init__(parent)
        self.system_context = system_context
        layout = QVBoxLayout(self)
        title = QLabel("外观与主题")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        layout.addWidget(QLabel("选择 ToolX 的界面主题："))
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("浅色", "light")
        self.theme_combo.addItem("深色", "dark")
        layout.addWidget(self.theme_combo)
        layout.addStretch(1)
        self.load()

    def load(self):
        settings = self.system_context.app_settings
        theme = settings.get("theme", "light") if settings is not None else "light"
        index = self.theme_combo.findData(theme)
        self.theme_combo.setCurrentIndex(max(index, 0))

    def apply(self):
        settings = self.system_context.app_settings
        if settings is not None:
            settings.set("theme", self.theme_combo.currentData())
        self.system_context.services.theme_changed.emit(str(self.theme_combo.currentData()))
        return True

    def reset(self):
        self.theme_combo.setCurrentIndex(self.theme_combo.findData("light"))
        return True
