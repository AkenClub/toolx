"""Validation and metadata model for ToolX plugin manifests."""

from dataclasses import dataclass, field
import json
import os
import re

from .app_paths import validate_plugin_id


PLUGIN_API_VERSION = 1
TOOLX_VERSION = "1.0.0"
SEMVER_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


class PluginManifestError(ValueError):
    """Raised when plugin.json is missing, malformed, or incompatible."""


def parse_version(version):
    if not isinstance(version, str) or not SEMVER_PATTERN.fullmatch(version):
        raise PluginManifestError("插件版本必须符合主版本.次版本.修订版本格式")
    return tuple(int(part) for part in version.split("."))


def is_version_at_least(actual, minimum):
    return parse_version(actual) >= parse_version(minimum)


def _validate_relative_resource(value, field_name):
    if value is None or value == "":
        return ""
    if not isinstance(value, str) or not value.strip():
        raise PluginManifestError("%s 必须是非空字符串" % field_name)
    normalized = value.replace("\\", "/")
    if normalized.startswith("/") or re.match(r"^[A-Za-z]:/", normalized):
        raise PluginManifestError("%s 必须是插件目录内的相对路径" % field_name)
    parts = [part for part in normalized.split("/") if part]
    if ".." in parts or any("\x00" in part for part in parts):
        raise PluginManifestError("%s 不能跳出插件目录" % field_name)
    return "/".join(parts)


@dataclass(frozen=True)
class PluginManifest:
    id: str
    name: str
    version: str
    entry: str
    api_version: int
    description: str = ""
    author: str = ""
    homepage: str = ""
    repository: str = ""
    license: str = ""
    min_toolx_version: str = ""
    icon: str = ""
    permissions: tuple = field(default_factory=tuple)
    dependencies: tuple = field(default_factory=tuple)
    settings: dict = field(default_factory=dict)
    source: str = "builtin"
    root_path: str = field(default="", compare=False, repr=False)

    @classmethod
    def from_file(cls, manifest_file, source="builtin", root_path=None):
        manifest_file = os.path.abspath(os.fspath(manifest_file))
        try:
            with open(manifest_file, "r", encoding="utf-8") as file:
                raw = json.load(file)
        except PluginManifestError:
            raise
        except Exception as error:
            raise PluginManifestError("读取 plugin.json 失败: %s" % error) from error
        return cls.from_mapping(
            raw,
            source=source,
            root_path=root_path or os.path.dirname(manifest_file),
        )

    @classmethod
    def from_directory(cls, plugin_dir, source="builtin"):
        plugin_dir = os.path.abspath(os.fspath(plugin_dir))
        return cls.from_file(
            os.path.join(plugin_dir, "plugin.json"),
            source=source,
            root_path=plugin_dir,
        )

    @classmethod
    def from_mapping(cls, raw, source="builtin", root_path=""):
        if not isinstance(raw, dict):
            raise PluginManifestError("plugin.json 根节点必须是 JSON 对象")

        required = ("id", "name", "version", "entry", "api_version")
        missing = [key for key in required if key not in raw]
        if missing:
            raise PluginManifestError("plugin.json 缺少必填字段: %s" % ", ".join(missing))

        try:
            plugin_id = validate_plugin_id(raw["id"])
        except ValueError as error:
            raise PluginManifestError(str(error)) from error

        name = raw["name"]
        if not isinstance(name, str) or not name.strip():
            raise PluginManifestError("插件 name 必须是非空字符串")
        version = raw["version"]
        parse_version(version)

        entry = raw["entry"]
        if not isinstance(entry, str) or entry.count(":") != 1:
            raise PluginManifestError("插件 entry 必须形如 plugin.py:get_plugin")
        entry_module, entry_function = entry.split(":", 1)
        entry_module = _validate_relative_resource(entry_module, "entry")
        if not entry_module.endswith(".py"):
            entry_module += ".py"
        if not entry_function.isidentifier():
            raise PluginManifestError("插件 entry 工厂方法名无效")

        api_version = raw["api_version"]
        if isinstance(api_version, bool) or not isinstance(api_version, int) or api_version < 1:
            raise PluginManifestError("api_version 必须是正整数")

        min_version = raw.get("min_toolx_version", "") or ""
        if min_version:
            parse_version(min_version)

        permissions = raw.get("permissions", []) or []
        if not isinstance(permissions, list) or not all(
            isinstance(permission, str) and permission.strip() for permission in permissions
        ):
            raise PluginManifestError("permissions 必须是字符串数组")

        dependencies = raw.get("dependencies", []) or []
        if not isinstance(dependencies, list):
            raise PluginManifestError("dependencies 必须是数组")
        normalized_dependencies = []
        for dependency in dependencies:
            if isinstance(dependency, str):
                try:
                    validate_plugin_id(dependency)
                except ValueError as error:
                    raise PluginManifestError("依赖插件 ID 无效") from error
                normalized_dependencies.append({"id": dependency})
            elif isinstance(dependency, dict):
                dependency_id = dependency.get("id")
                try:
                    validate_plugin_id(dependency_id)
                except ValueError as error:
                    raise PluginManifestError("依赖插件 ID 无效") from error
                minimum = dependency.get("version", dependency.get("min_version", "")) or ""
                if minimum:
                    parse_version(minimum)
                normalized_dependencies.append(
                    {"id": dependency_id, **({"version": minimum} if minimum else {})}
                )
            else:
                raise PluginManifestError("dependencies 项必须是字符串或对象")

        settings = raw.get("settings", {}) or {}
        if not isinstance(settings, dict):
            raise PluginManifestError("settings 必须是 JSON 对象")

        icon = _validate_relative_resource(raw.get("icon", "") or "", "icon")
        manifest = cls(
            id=plugin_id,
            name=name.strip(),
            version=version,
            entry="%s:%s" % (entry_module, entry_function),
            api_version=api_version,
            description=str(raw.get("description", "") or ""),
            author=str(raw.get("author", "") or ""),
            homepage=str(raw.get("homepage", "") or ""),
            repository=str(raw.get("repository", "") or ""),
            license=str(raw.get("license", "") or ""),
            min_toolx_version=min_version,
            icon=icon or "",
            permissions=tuple(permissions),
            dependencies=tuple(normalized_dependencies),
            settings=dict(settings),
            source=source,
            root_path=os.path.abspath(os.fspath(root_path)) if root_path else "",
        )
        manifest.validate_files()
        return manifest

    @property
    def entry_module(self):
        return self.entry.split(":", 1)[0][:-3].replace("/", ".").replace("\\", ".")

    @property
    def entry_function(self):
        return self.entry.split(":", 1)[1]

    @property
    def entry_file(self):
        return os.path.join(self.root_path, self.entry.split(":", 1)[0]) if self.root_path else ""

    @property
    def icon_file(self):
        return os.path.join(self.root_path, self.icon) if self.root_path and self.icon else ""

    def validate_files(self):
        if not self.root_path:
            return
        root = os.path.abspath(self.root_path)
        entry_file = os.path.abspath(self.entry_file)
        try:
            inside = os.path.commonpath([root, entry_file]) == root
        except ValueError:
            inside = False
        if not inside or not os.path.isfile(entry_file):
            raise PluginManifestError("插件入口文件不存在或位于插件目录之外")
        if self.icon:
            icon_file = os.path.abspath(self.icon_file)
            try:
                inside = os.path.commonpath([root, icon_file]) == root
            except ValueError:
                inside = False
            if not inside or not os.path.isfile(icon_file):
                raise PluginManifestError("插件图标文件不存在或位于插件目录之外")

    def is_compatible(self, toolx_version=TOOLX_VERSION, api_version=PLUGIN_API_VERSION):
        if self.api_version != api_version:
            return False
        return not self.min_toolx_version or is_version_at_least(toolx_version, self.min_toolx_version)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "homepage": self.homepage,
            "repository": self.repository,
            "license": self.license,
            "api_version": self.api_version,
            "min_toolx_version": self.min_toolx_version,
            "entry": self.entry,
            "icon": self.icon,
            "permissions": list(self.permissions),
            "dependencies": list(self.dependencies),
            "settings": self.settings,
        }
