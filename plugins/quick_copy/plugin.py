import os
import tempfile
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout,
                             QPlainTextEdit, QPushButton, QLabel, QFileDialog, QMessageBox, QLineEdit)
from PyQt6.QtCore import QMimeData, QUrl
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

from core.plugin_interface import PluginInterface

class QuickCopyWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # 在系统临时目录下专门建一个文件夹存放垃圾文件
        self.temp_dir = os.path.join(tempfile.gettempdir(), "WeChat_Temp_Files")
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
        self.current_temp_file = ""
        self.initUI()

    def initUI(self):
        # 现代简约风 QSS 样式表 (部分沿用主窗口风格，局部定制)
        self.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                font-family: 'Segoe UI', 'Microsoft YaHei';
                font-size: 14px;
            }
            QPlainTextEdit {
                background-color: #f5f7fa;
                border: 1px solid #dcdfe6;
                border-radius: 8px;
                padding: 10px;
                color: #303133;
            }
            QPushButton {
                background-color: #409eff;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #66b1ff;
            }
            QPushButton:pressed {
                background-color: #3a8ee6;
            }
            QPushButton#danger {
                background-color: #f56c6c;
            }
            QPushButton#danger:hover {
                background-color: #f78989;
            }
            QPushButton#secondary {
                background-color: #909399;
            }
            QPushButton#secondary:hover {
                background-color: #a6a9ad;
            }
            QLabel {
                color: #606266;
                font-weight: bold;
                font-size: 15px;
            }
            QLineEdit {
                border: 1px solid #dcdfe6;
                border-radius: 4px;
                padding: 6px;
                background-color: #f5f7fa;
                color: #303133;
            }
        """)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        # ====== 左侧：文本处理区 ======
        left_layout = QVBoxLayout()
        left_label = QLabel("📝 文本输入区")
        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText("在此输入或粘贴需要发送的长文本...")

        btn_layout_left = QHBoxLayout()
        self.btn_paste = QPushButton("快速粘贴")
        self.btn_clear_text = QPushButton("清空文本")
        self.btn_clear_text.setObjectName("secondary")

        self.btn_paste.clicked.connect(self.paste_text)
        self.btn_clear_text.clicked.connect(self.text_edit.clear)

        btn_layout_left.addWidget(self.btn_paste)
        btn_layout_left.addWidget(self.btn_clear_text)

        left_layout.addWidget(left_label)
        left_layout.addWidget(self.text_edit)
        left_layout.addLayout(btn_layout_left)

        # ====== 右侧：文件操作区 ======
        right_layout = QVBoxLayout()
        right_label = QLabel("🛠️ 临时文件操作")

        prefix_label = QLabel("文件名模板 (支持时间变量):")
        prefix_label.setStyleSheet("font-size: 13px; font-weight: normal; color: #606266; margin-top: 5px;")
        self.filename_template_edit = QLineEdit()
        self.filename_template_edit.setText("log_{{yyyy}}{{MM}}{{dd}}_{{HH}}{{mm}}{{ss}}")
        self.filename_template_edit.setPlaceholderText("如: 前缀-{{yyyy-MM-dd}}")

        self.status_label = QLabel("当前未生成临时文件")
        self.status_label.setStyleSheet("color: #909399; font-weight: normal; margin-top: 10px; margin-bottom: 15px;")
        self.status_label.setWordWrap(True)

        self.btn_generate_and_copy = QPushButton("🚀 一键复制为临时文件")
        self.btn_generate_and_copy.setStyleSheet("background-color: #67c23a; font-size: 15px;") # 绿色醒目
        
        self.btn_save_as = QPushButton("💾 另存为本地...")
        self.btn_save_as.setObjectName("secondary")
        self.btn_clear_temp = QPushButton("🗑️ 清空历史临时文件")
        self.btn_clear_temp.setObjectName("danger")

        # 绑定事件
        self.btn_generate_and_copy.clicked.connect(self.generate_and_copy)
        self.btn_save_as.clicked.connect(self.save_as_file)
        self.btn_clear_temp.clicked.connect(self.clear_temp_files)

        right_layout.addWidget(right_label)
        right_layout.addWidget(prefix_label)
        right_layout.addWidget(self.filename_template_edit)
        right_layout.addWidget(self.status_label)
        right_layout.addWidget(self.btn_generate_and_copy)
        right_layout.addStretch(1) # 中间加弹簧占位，把底部按钮推下去
        right_layout.addWidget(self.btn_save_as)
        right_layout.addWidget(self.btn_clear_temp)

        # 左边占总宽度的 2/3，右边占 1/3
        main_layout.addLayout(left_layout, 2) 
        main_layout.addLayout(right_layout, 1)

    def paste_text(self):
        clipboard = QApplication.clipboard()
        self.text_edit.setPlainText(clipboard.text())

    def generate_and_copy(self):
        text = self.text_edit.toPlainText()
        if not text.strip():
            QMessageBox.warning(self, "提示", "文本为空，请先输入或粘贴文本！")
            return

        template = self.filename_template_edit.text()
        if not template.strip():
            template = "微信长文本_{{yyyy}}{{MM}}{{dd}}_{{HH}}{{mm}}{{ss}}"
            
        now = datetime.now()
        filename = template.replace("{{yyyy}}", now.strftime("%Y")) \
                           .replace("{{yy}}", now.strftime("%y")) \
                           .replace("{{MM}}", now.strftime("%m")) \
                           .replace("{{dd}}", now.strftime("%d")) \
                           .replace("{{HH}}", now.strftime("%H")) \
                           .replace("{{hh}}", now.strftime("%H")) \
                           .replace("{{mm}}", now.strftime("%M")) \
                           .replace("{{ss}}", now.strftime("%S"))
        
        # 清理可能不合法的字符
        for char in ['<', '>', ':', '"', '/', '\\', '|', '?', '*']:
            filename = filename.replace(char, '_')
            
        if not filename.lower().endswith('.txt'):
            filename += ".txt"
            
        self.current_temp_file = os.path.join(self.temp_dir, filename)

        try:
            with open(self.current_temp_file, "w", encoding="utf-8") as f:
                f.write(text)
                
            # 直接复制到剪贴板
            mime_data = QMimeData()
            url = QUrl.fromLocalFile(self.current_temp_file)
            mime_data.setUrls([url])
            QApplication.clipboard().setMimeData(mime_data)
            
            self.status_label.setText(f"🎉 已生成并复制到剪贴板:\n{filename}\n快去微信输入框 Ctrl+V 吧！")
            self.status_label.setStyleSheet("color: #67c23a; font-weight: bold; margin-top: 10px; margin-bottom: 15px;")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"操作失败:\n{str(e)}")

    def save_as_file(self):
        text = self.text_edit.toPlainText()
        if not text.strip():
            QMessageBox.warning(self, "提示", "文本为空，没什么可保存的！")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "另存为", "", "文本文件 (*.txt);;所有文件 (*)")
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(text)
            QMessageBox.information(self, "成功", "文件已成功另存为！")

    def clear_temp_files(self):
        count = 0
        for filename in os.listdir(self.temp_dir):
            file_path = os.path.join(self.temp_dir, filename)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    count += 1
            except Exception:
                pass
        self.current_temp_file = ""
        self.status_label.setText("当前未生成临时文件")
        self.status_label.setStyleSheet("color: #909399; font-weight: normal; margin-bottom: 15px;")
        QMessageBox.information(self, "清理完毕", f"系统轻装上阵，已清理 {count} 个历史临时文件！")


class QuickCopyPlugin(PluginInterface):
    def __init__(self, config_manager):
        super().__init__(config_manager)
        self.widget = None

    def get_id(self) -> str:
        return "quick_copy"

    def get_name(self) -> str:
        return "极速中转站"

    def get_icon(self):
        return "⚡"

    def get_widget(self, parent: QWidget) -> QWidget:
        if self.widget is None:
            self.widget = QuickCopyWidget(parent)
        return self.widget

def get_plugin(config_manager):
    return QuickCopyPlugin(config_manager)
