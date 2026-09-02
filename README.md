# 🧰 ToolX

基于 PyQt6 构建的现代、简约、高扩展性的桌面工具箱应用。

初衷是为了整合散落在各处的独立小脚本与独立工具，将其放置于一个统一的侧边栏架构中进行管理与展示，为日常开发和工作提供便利。

---

## ✨ 核心特性

* **🚀 极简美学 UI**：采用现代化的扁平风格侧边栏设计风格，支持右侧无缝切换不同工具模块。
* **🔌 深度插件化架构**：核心业务功能完全解耦，启动时通过 `plugin.json` 发现并加载插件。普通插件通过受限 `PluginContext` 使用自己的配置和数据，错误会被隔离并写入日志。
* **🧩 统一插件管理**：在核心设置中心导入 `.toolx-plugin`、查看元数据、启用、禁用和卸载插件；状态变更默认在下次启动生效。
* **📌 便捷的置顶管理**：支持用户数据目录中的 `toolx_config.json` 自动存储你喜欢的工具栏布局与窗口设定。

## 📦 内置工具

目前初始自带以下工具插件：
1. **⚡ 极速中转站 (Quick Copy)**：帮助一键将超长文本中转、处理和极速复制生成临时文件的快捷助手，特别适合突破微信等平台的字数限制。
2. **🕒 任务工时 (Worklog)**：按天记录多条任务，默认按时间范围自动计算工时并扣除午休；支持手动覆盖工时、已登记标记、占比汇总和实时保存。

“设置”现在是 ToolX 核心系统页面，固定显示在侧边栏底部；“关于”页面位于设置中心，不属于可卸载插件。

## 🚀 快速开始

### 1. 环境准备

请确保您拥有 Python 3.9+ 环境。

```bash
# 建议新建虚拟环境
python -m venv venv
.\venv\Scripts\activate  # Windows 下

# 安装运行依赖
python -m pip install -r requirements.txt

# 如需运行测试，再安装开发依赖
python -m pip install -r requirements-dev.txt
```

### 2. 运行应用

```bash
python main.py
```

### 3. 运行测试

```bash
python -m pytest -q
```

### 4. 打包应用 (打包为 EXE)

本项目已配置好了 PyInstaller 的打包配置 `ToolX.spec`。如果你需要将其打包成独立的 Windows 可执行文件，可以在虚拟环境下执行以下步骤：

```bash
# requirements-dev.txt 已包含 PyInstaller；如果尚未安装开发依赖：
python -m pip install -r requirements-dev.txt

# 运行打包配置文件
pyinstaller ToolX.spec
```

打包完成后，生成的独立 `.exe` 文件将保存在项目根目录下的 `dist` 文件夹内。可以直接双击运行，或者分享给他人使用。
打包配置会使用 `assets/app_icon.ico` 作为 EXE、窗口、任务栏和侧边栏图标；替换图标资源后重新执行上述命令即可生效。

## 💾 用户数据位置

配置和任务工时数据保存在当前用户的数据目录中。Windows 默认位置为：

```text
%APPDATA%\ToolX\
├── toolx_config.json              # ToolX 应用配置
├── plugin_registry.json           # 插件安装状态
├── plugin_data\                   # 插件配置、业务数据和缓存
│   ├── worklog\settings.json
│   └── quick_copy\settings.json
├── installed_plugins\             # 用户导入的插件代码
└── logs\toolx.log
```

首次启动时会尝试迁移旧版工作目录或 exe 目录中的 `toolx_config.json` 和 `plugins/worklog/data.json`，旧文件会保留作为备份；旧版工时配置会迁移到 `plugin_data/worklog/settings.json`。

工时规则：任务默认使用开始/结束时间自动计算，并扣除与全局午休的重叠部分；如果业务上需要，可以直接编辑“工时”列形成手动覆盖，点击该行刷新按钮即可恢复自动计算。`已登记` 仅表示登记状态，不参与工时计算。

## 🛠️ 为它开发插件

您可以轻松在本项目上快速构建独属您自己的私有工具集合。详见完整的开发者文档：

👉 [插件开发指南 (Plugin Development Guide)](docs/plugin_development_guide.md)

---

## 🔗 开源地址

**GitHub 仓库**: [https://github.com/AkenClub/toolx](https://github.com/AkenClub/toolx)

### 项目声明
MIT License
