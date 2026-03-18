import sys
import os

# 将当前目录加入系统路径，确保从 main.py 启动时能正确 import core 与 plugins 模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from core.config_manager import ConfigManager
from core.plugin_manager import PluginManager
from core.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    
    # 初始化配置管理器
    config = ConfigManager(config_file="toolx_config.json")
    
    # 初始化插件管理器
    plugin_mgr = PluginManager(config_manager=config, plugin_package="plugins")
    
    # 加载全部插件
    plugin_mgr.load_all_plugins()
    
    # 初始化并展示主界面
    main_window = MainWindow(config_manager=config, plugin_manager=plugin_mgr)
    main_window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
