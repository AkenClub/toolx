# ToolX 插件开发指南

ToolX 的普通功能插件运行在宿主进程中，但只能通过宿主传入的
`PluginContext` 访问自己的配置、数据和有限的公共服务。设置、关于和插件
生命周期管理属于核心系统功能，不需要也不能通过普通插件实现。

## 1. 插件目录和清单

内置插件放在项目的 `plugins/<id>/` 下；用户插件使用 `.toolx-plugin` 扩展名，
本质上是一个 ZIP 包，且 `plugin.json` 必须位于包根目录：

```text
example.toolx-plugin
├── plugin.json
├── plugin.py
└── 其他 Python 模块或资源
```

清单至少包含以下字段：

```json
{
  "id": "example",
  "name": "示例插件",
  "version": "1.0.0",
  "api_version": 1,
  "min_toolx_version": "1.0.0",
  "entry": "plugin.py:get_plugin",
  "description": "插件说明",
  "author": "作者",
  "homepage": "https://example.com",
  "repository": "https://github.com/example/example",
  "license": "MIT",
  "permissions": [],
  "dependencies": [],
  "settings": {"has_pages": false}
}
```

`id` 是稳定的全局标识，只能使用小写字母、数字、下划线和短横线；`name` 是
可翻译的展示名称。`version` 使用三段式语义版本号。`entry` 的代码会在清单
校验通过、用户确认并安装后才加载。

## 2. 编写插件

插件工厂接收 `PluginContext`，并返回 `PluginInterface` 实例：

```python
from PyQt6.QtWidgets import QLabel, QWidget

from core.plugin_interface import PluginInterface


class ExamplePlugin(PluginInterface):
    def get_id(self):
        return "example"

    def get_name(self):
        return "示例插件"

    def get_icon(self):
        return "🌟"

    def get_widget(self, parent: QWidget):
        return QLabel("Hello ToolX", parent)


def get_plugin(context):
    return ExamplePlugin(context)
```

插件可使用以下接口：

```python
context.config.get("key", default)
context.config.set("key", value)
context.config.update({"key": value})
context.config.reset()

context.storage.read_json("data.json")
context.storage.write_json("data.json", {"items": []})
context.storage.data_dir()
context.storage.cache_dir()

context.services.logger.info("插件已加载")
context.services.clipboard.read()
context.services.clipboard.write("文本")
context.services.open_url("https://example.com")
context.services.open_path(context.storage.data_dir())
context.services.theme
context.services.app_info
context.services.request_restart()
```

配置文件固定保存到用户数据目录的
`plugin_data/<id>/settings.json`，业务数据和缓存也只能位于
`plugin_data/<id>/` 下。插件不能获得完整的 `ConfigManager`、`PluginManager`、
`MainWindow` 或其他插件的上下文。

## 3. 插件设置页

复杂设置可以贡献一个自定义页面。设置中心会统一处理页面创建、应用、取消
和恢复默认：

```python
from PyQt6.QtWidgets import QLineEdit, QVBoxLayout, QWidget

from core.plugin_interface import SettingsPage


class ExampleSettings(QWidget):
    def __init__(self, context, parent=None):
        super().__init__(parent)
        self.context = context
        self.edit = QLineEdit(self)
        QVBoxLayout(self).addWidget(self.edit)
        self.load()

    def load(self):
        self.edit.setText(self.context.config.get("text", ""))

    def apply(self):
        value = self.edit.text().strip()
        if not value:
            return False
        self.context.config.set("text", value)
        return True

    def reset(self):
        self.edit.clear()


class ExamplePlugin(PluginInterface):
    # 其他接口省略
    def get_settings_pages(self):
        return [
            SettingsPage(
                page_id="general",
                title="常规",
                path=("插件", self.get_name()),
                factory=lambda parent: ExampleSettings(self.context, parent),
                plugin_id=self.get_id(),
            )
        ]
```

插件功能页中的设置入口也应打开核心设置中心提供的页面，避免维护第二套配置
表单。

## 4. 导入和生命周期

用户可以在“设置 → 插件 → 插件管理”中查看元数据、导入本地包、启用、禁用和
卸载插件。启用和禁用默认在下次启动生效；卸载默认只删除插件代码，保留配置
和业务数据。“清理数据”是独立操作，必须经过明确确认。

导入阶段会检查 ZIP 路径穿越、文件数量和大小、清单字段、入口文件、ToolX/API
版本、插件 ID 冲突和依赖关系。第一版不会自动执行 `pip install`，插件应优先
依赖标准库、PyQt6 和 ToolX 公开 API。

生命周期钩子是可选的：

```python
def on_load(self):
    self.context.services.logger.info("loaded")

def on_unload(self):
    pass
```

## 5. 本地测试和打包

```powershell
python -m pytest -q
pyinstaller ToolX.spec
```

内置插件的 `plugin.json` 和代码会随程序打包；用户插件运行时从
`%APPDATA%\ToolX\installed_plugins\<id>\<version>` 加载。设置和关于页面位于
`core/settings/`，不再加入普通插件清单。
