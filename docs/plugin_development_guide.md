# 🛠️ ToolX - 插件开发指南

欢迎为 ToolX 开发新功能！本项目采用了非常轻量级的 `importlib` 动态加载机制，你可以轻松开发自己的专属工具并将其挂载到应用主界面的左侧导航中。

## 1. 📂 目录结构规范

所有的插件必须存放在 `plugins/` 目录下。你应该为你的插件创建一个独立的文件夹，文件夹名称最好为英文小写并使用下划线（如 `my_awesome_tool`）。

```text
ToolX/
├── core/                    # 核心架构代码
├── plugins/                 # 插件存放根目录
│   ├── quick_copy/          # 内置的快速复制插件
│   ├── my_awesome_tool/     # 你的插件目录
│   │   ├── plugin.py        # 必须有的插件入口文件
│   │   └── (其他你的代码或资源)
├── main.py                  # 应用入口
└── toolx_config.json        # 用户配置文件
```

**⚠️ 核心要求**：
* 插件文件夹内**必须且仅必须**包含一个名为 `plugin.py` 的入口文件。

---

## 2. 📝 编写 `plugin.py`

你的 `plugin.py` 必须引入 `core.plugin_interface.PluginInterface` 并实现它，同时向外导出一个 `get_plugin(config_manager)` 的工厂方法。

### 最简示例代码：

```python
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from core.plugin_interface import PluginInterface

# 1. 编写你的工具 UI 组件 (必须继承自 QWidget)
class MyToolWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        label = QLabel("🚀 这是我的牛逼工具页面！")
        layout.addWidget(label)

# 2. 编写插件描述类 (必须继承 PluginInterface)
class MyAwesomePlugin(PluginInterface):
    def __init__(self, config_manager=None):
        super().__init__(config_manager)
        self.widget = None

    def get_id(self) -> str:
        # 要求全局唯一，例如文件夹名
        return "my_awesome_tool"

    def get_name(self) -> str:
        # 左侧导航栏展示的中文名字
        return "我的牛逼工具"

    def get_icon(self):
        # 左侧导航栏展示的图标（建议返回一个 Emoji 字符串即可）
        return "🌟"

    def get_widget(self, parent: QWidget) -> QWidget:
        # 返回你的 UI 组件实例（懒加载模式，只有界面渲染时才实例化）
        if self.widget is None:
            self.widget = MyToolWidget(parent)
        return self.widget
        
    def on_load(self):
        # 插件当被扫描加载进系统时的生命周期回调（可选）
        print("MyAwesomePlugin 已加载")

    def on_unload(self):
        # 插件被卸载或程序退出时的生命周期回调（可选）
        pass

# 3. 必须提供的入口方法，框架通过该方法获取插件实例
def get_plugin(config_manager):
    return MyAwesomePlugin(config_manager)
```

## 3. 🧪 测试你的插件

编写完 `plugin.py` 后，只需重启主程序 `main.py`。
由于项目内建了自动扫描与基于 `importlib` 的热导入装载，主界面启动后你的插件就会自动出现在左侧导航栏的末尾列表里！

> **关于本地配置存储**：
> 如果你的插件需要保存用户的配置设置，可以直接利用在 `__init__` 中传入的 `config_manager` 对象，调用 `self.config_manager.set(key, value)` 及 `get(key)` 方法。此参数将由框架持久化到全局的 JSON 配置中。也可以自己在插件目录内维护配置文件。
