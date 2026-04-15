# 🧰 ToolX

基于 PyQt6 构建的现代、简约、高扩展性的桌面工具箱应用。

初衷是为了整合散落在各处的独立小脚本与独立工具，将其放置于一个统一的侧边栏架构中进行管理与展示，为日常开发和工作提供便利。

---

## ✨ 核心特性

* **🚀 极简美学 UI**：采用现代化的扁平风格侧边栏设计风格，支持右侧无缝切换不同工具模块。
* **🔌 深度插件化架构**：核心业务功能完全解耦，采用内置 `importlib` 热加载机制。新增工具只需放入指定位置即能在右侧栏加载。
* **📌 便捷的置顶管理**：支持配置文件 `toolx_config.json` 自动存储你喜欢的工具栏布局与窗口设定。

## 📦 内置工具

目前初始自带以下工具插件：
1. **⚡ 极速中转站 (Quick Copy)**：帮助一键将超长文本中转、处理和极速复制生成临时文件的快捷助手，特别适合突破微信等平台的字数限制。
2. **⚙️ 系统设置 (Sys Settings)**：管理整体框架风格（框架预留）。
3. **ℹ️ 关于本软件 (Sys About)**：版本介绍与开源信息。
4. **🕒 任务工时 (Worklog)**：按天记录多条任务、精确时间范围、自动换算工时占比，并实时保存到本地。

## 🚀 快速开始

### 1. 环境准备

请确保您拥有 Python 3.9+ 环境。

```bash
# 建议新建虚拟环境
python -m venv venv
.\venv\Scripts\activate  # Windows 下

# 安装核心依赖
pip install PyQt6
```

### 2. 运行应用

```bash
python main.py
```

### 3. 打包应用 (打包为 EXE)

本项目已配置好了 PyInstaller 的打包配置 `ToolX.spec`。如果你需要将其打包成独立的 Windows 可执行文件，可以在虚拟环境下执行以下步骤：

```bash
# 安装打包工具
pip install pyinstaller

# 运行打包配置文件
pyinstaller ToolX.spec
```

打包完成后，生成的独立 `.exe` 文件将保存在项目根目录下的 `dist` 文件夹内。可以直接双击运行，或者分享给他人使用。

## 🛠️ 为它开发插件

您可以轻松在本项目上快速构建独属您自己的私有工具集合。详见完整的开发者文档：

👉 [插件开发指南 (Plugin Development Guide)](docs/plugin_development_guide.md)

---

## 🔗 开源地址

**GitHub 仓库**: [https://github.com/AkenClub/toolx](https://github.com/AkenClub/toolx)

### 项目声明
MIT License
