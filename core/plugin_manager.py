import os
import sys
import importlib
from PyQt6.QtWidgets import QMessageBox

class PluginManager:
    """
    负责扫描、加载和管理所有的工具插件。
    """
    def __init__(self, config_manager, plugin_package="plugins"):
        self.config_manager = config_manager
        self.plugin_package = plugin_package
        self.plugins = {}  # dict of plugin_id: PluginInterface

        # 获取真实的物理路径（适配 PyInstaller 打包后的 sys._MEIPASS）
        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
        self.plugin_dir = os.path.join(base_dir, self.plugin_package)

        if not os.path.exists(self.plugin_dir):
            try:
                os.makedirs(self.plugin_dir)
            except Exception:
                pass

    def load_all_plugins(self):
        """
        扫描 plugins 目录下所有的插件模块并加载
        """
        self.plugins.clear()
        
        for folder_name in os.listdir(self.plugin_dir):
            plugin_path = os.path.join(self.plugin_dir, folder_name)
            if not os.path.isdir(plugin_path) or folder_name.startswith("__"):
                continue

            # 要求插件目录下必须有 plugin.py
            module_file = os.path.join(plugin_path, "plugin.py")
            if not os.path.exists(module_file):
                continue
                
            module_name = f"{self.plugin_package}.{folder_name}.plugin"
            
            try:
                module = importlib.import_module(module_name)
                # 重新加载模块以便于开发阶段获取最新代码
                importlib.reload(module)
                
                if hasattr(module, 'get_plugin'):
                    plugin_instance = module.get_plugin(self.config_manager)
                    if plugin_instance:
                        self.plugins[plugin_instance.get_id()] = plugin_instance
                        plugin_instance.on_load()
                        print(f"成功加载插件: {plugin_instance.get_name()} ({plugin_instance.get_id()})")
                else:
                    print(f"插件加载失败: {folder_name} 未实现 get_plugin() 方法。")
                    
            except Exception as e:
                print(f"加载插件 {folder_name} 时发生错误: {e}")

    def get_plugins(self):
        """返回所有已加载插件的字典"""
        return self.plugins
        
    def get_plugin(self, plugin_id):
        """根据 ID 获取特定插件的实例"""
        return self.plugins.get(plugin_id)

    def unload_all(self):
        for p in self.plugins.values():
            try:
                p.on_unload()
            except Exception as e:
                print(f"卸载插件 {p.get_id()} 失败: {e}")
        self.plugins.clear()
