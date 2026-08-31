import importlib
import logging
import os
import sys

from .plugin_interface import PluginInterface


logger = logging.getLogger(__name__)

class PluginManager:
    """
    负责扫描、加载和管理所有的工具插件。
    """
    def __init__(self, config_manager, plugin_package="plugins", plugin_dir=None):
        self.config_manager = config_manager
        self.plugin_package = plugin_package
        self.plugins = {}  # dict of plugin_id: PluginInterface

        # 获取真实的物理路径（适配 PyInstaller 打包后的 sys._MEIPASS）
        if plugin_dir is not None:
            self.plugin_dir = os.path.abspath(os.fspath(plugin_dir))
        else:
            if getattr(sys, "frozen", False):
                base_dir = sys._MEIPASS
            else:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.plugin_dir = os.path.join(base_dir, self.plugin_package)

        if not os.path.exists(self.plugin_dir):
            try:
                os.makedirs(self.plugin_dir)
            except Exception:
                logger.exception("无法创建插件目录: %s", self.plugin_dir)

    def load_all_plugins(self):
        """
        扫描 plugins 目录下所有的插件模块并加载
        """
        self.unload_all()

        try:
            folder_names = sorted(os.listdir(self.plugin_dir))
        except Exception:
            logger.exception("无法扫描插件目录: %s", self.plugin_dir)
            return self.plugins

        for folder_name in folder_names:
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

                factory = getattr(module, "get_plugin", None)
                if not callable(factory):
                    raise TypeError("未实现可调用的 get_plugin() 方法")

                plugin_instance = factory(self.config_manager)
                if not isinstance(plugin_instance, PluginInterface):
                    raise TypeError("get_plugin() 未返回 PluginInterface 实例")

                plugin_id = plugin_instance.get_id()
                plugin_name = plugin_instance.get_name()
                if not isinstance(plugin_id, str) or not plugin_id.strip():
                    raise ValueError("插件 ID 必须是非空字符串")
                if plugin_id != plugin_id.strip():
                    raise ValueError("插件 ID 不能包含首尾空白字符")
                if not isinstance(plugin_name, str) or not plugin_name.strip():
                    raise ValueError("插件名称必须是非空字符串")

                if plugin_id in self.plugins:
                    logger.error(
                        "发现重复插件 ID，跳过插件 %s (%s); 已保留已有插件",
                        folder_name,
                        plugin_id,
                    )
                    continue

                try:
                    plugin_instance.on_load()
                except Exception:
                    logger.exception("插件 %s 的 on_load() 执行失败", plugin_id)
                    try:
                        plugin_instance.on_unload()
                    except Exception:
                        logger.exception("插件 %s 的失败清理 on_unload() 也执行失败", plugin_id)
                    continue

                self.plugins[plugin_id] = plugin_instance
                logger.info("成功加载插件: %s (%s)", plugin_name, plugin_id)

            except Exception:
                # 单个插件的导入、工厂或生命周期错误不应阻止其它插件启动。
                logger.exception("加载插件 %s 时发生错误", folder_name)

        logger.info("插件扫描完成，共加载 %d 个插件", len(self.plugins))
        return self.plugins

    def get_plugins(self):
        """返回所有已加载插件的字典"""
        return self.plugins
        
    def get_plugin(self, plugin_id):
        """根据 ID 获取特定插件的实例"""
        return self.plugins.get(plugin_id)

    def unload_all(self):
        for plugin_id, plugin in list(self.plugins.items()):
            try:
                plugin.on_unload()
            except Exception:
                logger.exception("卸载插件 %s 失败", plugin_id)
        self.plugins.clear()
