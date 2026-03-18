from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QIcon

class PluginInterface:
    """
    工具箱插件的标准接口基类。
    所有自定义工具插件都必须继承并实现此内定义的方法。
    """
    
    def __init__(self, config_manager=None):
        """
        初始化插件
        :param config_manager: ConfigManager 实例，方便插件读写自身或全局配置
        """
        self.config_manager = config_manager

    def get_id(self) -> str:
        """
        返回插件的全局唯一标识符（建议全小写字母加下划线，例如：quick_copy）
        """
        raise NotImplementedError("Plugins must implement get_id()")

    def get_name(self) -> str:
        """
        返回插件在侧边栏显示的中文名称
        """
        raise NotImplementedError("Plugins must implement get_name()")

    def get_icon(self):
        """
        返回在侧边栏显示的图标，可以是 QIcon 对象或者支持 FontAwesome 等形式，也可以返回 Emoji 字符串。
        为了简单兼容，先返回字符串形式的 Emoji，例如 "📝"
        """
        return "🛠️"

    def get_widget(self, parent: QWidget) -> QWidget:
        """
        返回该插件的主要 UI 组件，用于嵌入主窗口的展示区中。
        """
        raise NotImplementedError("Plugins must implement get_widget()")

    def on_load(self):
        """生命周期函数：插件加载时调用（可选）"""
        pass

    def on_unload(self):
        """生命周期函数：插件卸载或退出时调用（可选）"""
        pass
