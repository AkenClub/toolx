"""Plugin registry, package validation, and lifecycle administration."""

from copy import deepcopy
from dataclasses import dataclass
import json
import logging
import os
import posixpath
import shutil
import tempfile
import zipfile

from .app_paths import PluginPaths, validate_plugin_id
from .atomic_json import atomic_write_json
from .plugin_manifest import (
    PLUGIN_API_VERSION,
    TOOLX_VERSION,
    PluginManifest,
    PluginManifestError,
    is_version_at_least,
)


logger = logging.getLogger(__name__)
MAX_PACKAGE_BYTES = 50 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024
MAX_PACKAGE_FILES = 1000
CORE_PLUGIN_IDS = frozenset(("sys_settings", "sys_about", "settings", "about"))


class PluginAdminError(ValueError):
    """Raised when a plugin administration operation is not safe or valid."""


class PluginRegistry:
    """Atomic JSON registry for installed plugin versions and enabled state."""

    def __init__(self, paths=None, registry_file=None):
        if registry_file is None and paths is not None and not isinstance(paths, PluginPaths):
            possible_file = os.fspath(paths)
            if possible_file.lower().endswith(".json"):
                registry_file = possible_file
                paths = None
        if registry_file is not None:
            registry_file = os.path.abspath(os.fspath(registry_file))
            self.paths = paths if isinstance(paths, PluginPaths) else PluginPaths(
                os.path.dirname(registry_file)
            )
            self.file_path = registry_file
        else:
            self.paths = paths if isinstance(paths, PluginPaths) else PluginPaths(paths)
            self.file_path = self.paths.plugin_registry_file
        self.records = self._load()

    def _load(self):
        if not os.path.exists(self.file_path):
            return {}
        try:
            with open(self.file_path, "r", encoding="utf-8") as file:
                raw = json.load(file)
            if isinstance(raw, dict) and isinstance(raw.get("plugins"), dict):
                raw = raw["plugins"]
            if isinstance(raw, list):
                raw = {item.get("id"): item for item in raw if isinstance(item, dict) and item.get("id")}
            if not isinstance(raw, dict):
                raise ValueError("插件注册表根节点必须是对象")
            return {
                plugin_id: deepcopy(record)
                for plugin_id, record in raw.items()
                if isinstance(plugin_id, str) and isinstance(record, dict)
            }
        except Exception:
            logger.exception("插件注册表读取失败: %s", self.file_path)
            return {}

    def save(self):
        atomic_write_json(self.file_path, {"plugins": self.records}, indent=2)

    def reload(self):
        self.records = self._load()
        return self.records

    def get(self, plugin_id):
        return deepcopy(self.records.get(plugin_id))

    def list(self):
        return [deepcopy(record) for record in self.records.values()]

    def upsert(self, plugin_id, record=None, **values):
        validate_plugin_id(plugin_id)
        current = deepcopy(self.records.get(plugin_id, {}))
        if record is not None:
            if not isinstance(record, dict):
                raise TypeError("插件注册信息必须是对象")
            current.update(deepcopy(record))
        current.update(deepcopy(values))
        current["id"] = plugin_id
        self.records[plugin_id] = current
        return deepcopy(current)

    def remove(self, plugin_id):
        return self.records.pop(plugin_id, None)


@dataclass(frozen=True)
class PluginPackageValidation:
    manifest: PluginManifest
    source_path: str


def _dependency_id_and_version(dependency):
    if isinstance(dependency, str):
        return dependency, ""
    if isinstance(dependency, dict):
        return dependency.get("id"), dependency.get("version", dependency.get("min_version", "")) or ""
    return None, ""


class PluginAdminService:
    """System-only service used by settings to manage feature plugins."""

    def __init__(
        self,
        app_settings=None,
        paths=None,
        plugin_manager=None,
        builtin_plugin_dir=None,
        registry=None,
    ):
        if paths is None and app_settings is not None:
            paths = getattr(app_settings, "paths", None)
        self.paths = paths if isinstance(paths, PluginPaths) else PluginPaths(paths)
        self.app_settings = app_settings
        self.plugin_manager = plugin_manager
        self.builtin_plugin_dir = (
            os.path.abspath(os.fspath(builtin_plugin_dir))
            if builtin_plugin_dir is not None
            else None
        )
        self.registry = registry or PluginRegistry(self.paths)

    def register_builtin(self, manifest, install_path=None):
        if not isinstance(manifest, PluginManifest):
            raise TypeError("manifest 必须是 PluginManifest")
        if manifest.id in CORE_PLUGIN_IDS:
            raise PluginAdminError("核心系统页面不能注册为普通插件")
        current = self.registry.get(manifest.id) or {}
        record = self.registry.upsert(
            manifest.id,
            current,
            enabled=current.get("enabled", True),
            version=manifest.version,
            source="builtin",
            install_path=install_path or manifest.root_path,
            manifest=manifest.to_dict(),
        )
        self.registry.save()
        return record

    def _discover_builtin_records(self):
        records = {}
        if not self.builtin_plugin_dir or not os.path.isdir(self.builtin_plugin_dir):
            return records
        for folder_name in sorted(os.listdir(self.builtin_plugin_dir)):
            if folder_name.startswith("__") or folder_name in {"settings", "about"}:
                continue
            plugin_dir = os.path.join(self.builtin_plugin_dir, folder_name)
            if not os.path.isdir(plugin_dir):
                continue
            manifest_file = os.path.join(plugin_dir, "plugin.json")
            if not os.path.isfile(manifest_file):
                continue
            try:
                manifest = PluginManifest.from_file(manifest_file, source="builtin", root_path=plugin_dir)
                if manifest.id in CORE_PLUGIN_IDS:
                    continue
                current = self.registry.get(manifest.id) or {}
                records[manifest.id] = {
                    "id": manifest.id,
                    "name": manifest.name,
                    "version": manifest.version,
                    "source": "builtin",
                    "enabled": current.get("enabled", True),
                    "install_path": plugin_dir,
                    "manifest": manifest.to_dict(),
                }
            except PluginManifestError:
                logger.exception("内置插件清单无效: %s", manifest_file)
        return records

    def _discover_imported_records(self):
        records = {}
        if not os.path.isdir(self.paths.installed_plugins_root):
            return records
        for plugin_id in sorted(os.listdir(self.paths.installed_plugins_root)):
            if plugin_id in CORE_PLUGIN_IDS:
                continue
            plugin_root = os.path.join(self.paths.installed_plugins_root, plugin_id)
            if not os.path.isdir(plugin_root):
                continue
            record = self.registry.get(plugin_id) or {}
            version = record.get("version")
            install_path = record.get("install_path")
            if version and install_path:
                active_path = os.path.abspath(os.fspath(install_path))
                allowed_root = os.path.abspath(plugin_root)
                try:
                    path_is_safe = os.path.commonpath([allowed_root, active_path]) == allowed_root
                except ValueError:
                    path_is_safe = False
                if not path_is_safe:
                    logger.error("插件注册表中的安装路径越界，忽略: %s", plugin_id)
                    active_path = ""
                if active_path and not os.path.isdir(active_path):
                    active_path = ""
            else:
                active_path = ""
            if not active_path:
                versions = sorted(
                    name
                    for name in os.listdir(plugin_root)
                    if os.path.isdir(os.path.join(plugin_root, name))
                )
                if not versions:
                    continue
                version = versions[-1]
                active_path = os.path.join(plugin_root, version)
            try:
                manifest = PluginManifest.from_directory(active_path, source="imported")
            except PluginManifestError:
                logger.exception("已安装插件清单无效: %s", active_path)
                continue
            records[plugin_id] = {
                "id": manifest.id,
                "name": manifest.name,
                "version": manifest.version,
                "source": "imported",
                "enabled": record.get("enabled", True),
                "install_path": active_path,
                "manifest": manifest.to_dict(),
            }
        return records

    def list_installed(self):
        """Return metadata only; this method never imports plugin code."""
        self.registry.reload()
        records = self._discover_builtin_records()
        records.update(self._discover_imported_records())
        for plugin_id, record in self.registry.records.items():
            if plugin_id not in records and plugin_id not in CORE_PLUGIN_IDS:
                records[plugin_id] = deepcopy(record)
        return [records[plugin_id] for plugin_id in sorted(records)]

    def get_plugin(self, plugin_id):
        for record in self.list_installed():
            if record.get("id") == plugin_id:
                return record
        return None

    def _check_zip_members(self, archive):
        infos = archive.infolist()
        if len(infos) > MAX_PACKAGE_FILES:
            raise PluginAdminError("插件包文件数量超过限制")
        total_size = 0
        seen = set()
        for info in infos:
            name = info.filename.replace("\\", "/")
            normalized = posixpath.normpath(name)
            if (
                not name
                or name.startswith("/")
                or name.startswith("../")
                or "/../" in "/%s" % name
                or normalized in {".", ""}
                or normalized in seen
            ):
                raise PluginAdminError("插件包包含不安全或重复的 ZIP 路径")
            if len(normalized.split("/")) and normalized.split("/")[0].endswith(":"):
                raise PluginAdminError("插件包不能使用绝对路径")
            seen.add(normalized)
            if info.is_dir():
                continue
            mode = (info.external_attr >> 16) & 0o170000
            if mode == 0o120000:
                raise PluginAdminError("插件包不允许包含符号链接")
            total_size += info.file_size
            if total_size > MAX_UNCOMPRESSED_BYTES:
                raise PluginAdminError("插件包解压大小超过限制")
        if "plugin.json" not in seen:
            raise PluginAdminError("插件包根目录缺少 plugin.json")
        if not any(name.endswith("plugin.py") for name in seen):
            raise PluginAdminError("插件包缺少 Python 入口文件")
        return infos

    def _extract_package(self, package_path):
        package_path = os.path.abspath(os.fspath(package_path))
        if not os.path.isfile(package_path):
            raise PluginAdminError("插件包不存在")
        if os.path.getsize(package_path) > MAX_PACKAGE_BYTES:
            raise PluginAdminError("插件包大小超过限制")
        try:
            archive = zipfile.ZipFile(package_path, "r")
        except (OSError, zipfile.BadZipFile) as error:
            raise PluginAdminError("插件包不是有效的 ZIP 文件") from error

        staging_root = None
        try:
            infos = self._check_zip_members(archive)
            os.makedirs(self.paths.temp_root, exist_ok=True)
            staging_root = tempfile.mkdtemp(prefix="plugin-", dir=self.paths.temp_root)
            for info in infos:
                normalized = posixpath.normpath(info.filename.replace("\\", "/"))
                if info.is_dir():
                    os.makedirs(os.path.join(staging_root, *normalized.split("/")), exist_ok=True)
                    continue
                target = os.path.join(staging_root, *normalized.split("/"))
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with archive.open(info, "r") as source, open(target, "wb") as destination:
                    shutil.copyfileobj(source, destination, length=1024 * 1024)
            return staging_root
        except PluginAdminError:
            if staging_root:
                shutil.rmtree(staging_root, ignore_errors=True)
            raise
        except Exception as error:
            if staging_root:
                shutil.rmtree(staging_root, ignore_errors=True)
            raise PluginAdminError("插件包解压失败: %s" % error) from error
        finally:
            archive.close()

    def _validate_directory(self, directory):
        try:
            manifest = PluginManifest.from_directory(directory, source="imported")
        except PluginManifestError as error:
            raise PluginAdminError(str(error)) from error
        if not manifest.is_compatible(TOOLX_VERSION, PLUGIN_API_VERSION):
            raise PluginAdminError("插件与当前 ToolX 或插件 API 版本不兼容")
        if manifest.id in CORE_PLUGIN_IDS:
            raise PluginAdminError("插件 ID 不能覆盖核心系统页面")

        existing = self.get_plugin(manifest.id)
        if existing and existing.get("source") == "builtin":
            raise PluginAdminError("用户插件不能覆盖内置插件 ID")

        available = {record.get("id"): record for record in self.list_installed()}
        available[manifest.id] = {
            "id": manifest.id,
            "version": manifest.version,
        }
        for dependency in manifest.dependencies:
            dependency_id, minimum = _dependency_id_and_version(dependency)
            if dependency_id == manifest.id:
                raise PluginAdminError("插件不能依赖自身")
            dependency_record = available.get(dependency_id)
            if dependency_record is None:
                raise PluginAdminError("缺少依赖插件: %s" % dependency_id)
            if minimum and not is_version_at_least(dependency_record.get("version", "0.0.0"), minimum):
                raise PluginAdminError("依赖插件 %s 的版本不满足要求" % dependency_id)
        return manifest

    def validate_package(self, package_path):
        staging_root = self._extract_package(package_path)
        try:
            manifest = self._validate_directory(staging_root)
            return manifest
        finally:
            shutil.rmtree(staging_root, ignore_errors=True)

    def install_package(self, package_path):
        staging_root = self._extract_package(package_path)
        try:
            manifest = self._validate_directory(staging_root)
            target = self.paths.installed_plugin_dir(manifest.id, manifest.version)
            if os.path.exists(target):
                raise PluginAdminError("该插件版本已经安装")
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.move(staging_root, target)
            staging_root = None
            # Re-read from the final directory so callers receive paths that
            # remain valid after the temporary staging directory is removed.
            manifest = PluginManifest.from_directory(target, source="imported")

            current = self.registry.get(manifest.id) or {}
            self.registry.upsert(
                manifest.id,
                current,
                enabled=current.get("enabled", True),
                version=manifest.version,
                source="imported",
                install_path=target,
                manifest=manifest.to_dict(),
            )
            try:
                self.registry.save()
            except Exception:
                # The code remains in a versioned directory and can be
                # recovered on the next scan; do not delete it blindly.
                logger.exception("插件注册表保存失败，保留已安装代码: %s", target)
                raise
            return manifest
        finally:
            if staging_root:
                shutil.rmtree(staging_root, ignore_errors=True)

    def _require_record(self, plugin_id):
        try:
            validate_plugin_id(plugin_id)
        except ValueError as error:
            raise PluginAdminError(str(error)) from error
        record = self.get_plugin(plugin_id)
        if record is None:
            raise PluginAdminError("插件不存在: %s" % plugin_id)
        return record

    def _check_dependencies(self, record):
        available = {item.get("id"): item for item in self.list_installed()}
        for dependency in (record.get("manifest") or {}).get("dependencies", []) or []:
            dependency_id, minimum = _dependency_id_and_version(dependency)
            dependency_record = available.get(dependency_id)
            if dependency_record is None or not dependency_record.get("enabled", True):
                raise PluginAdminError("依赖插件未启用: %s" % dependency_id)
            if minimum:
                try:
                    meets_version = is_version_at_least(
                        dependency_record.get("version", "0.0.0"), minimum
                    )
                except Exception as error:
                    raise PluginAdminError("依赖插件版本无效: %s" % dependency_id) from error
                if not meets_version:
                    raise PluginAdminError("依赖插件 %s 的版本不满足要求" % dependency_id)

    def enable(self, plugin_id):
        record = self._require_record(plugin_id)
        if record.get("source") == "core":
            raise PluginAdminError("核心系统页面不需要启用")
        self._check_dependencies(record)
        self.registry.upsert(plugin_id, record, enabled=True)
        self.registry.save()
        return self.registry.get(plugin_id)

    def disable(self, plugin_id):
        record = self._require_record(plugin_id)
        enabled_dependents = []
        for other in self.list_installed():
            if other.get("id") == plugin_id or not other.get("enabled", True):
                continue
            manifest = other.get("manifest") or {}
            for dependency in manifest.get("dependencies", []) or []:
                dependency_id, _ = _dependency_id_and_version(dependency)
                if dependency_id == plugin_id:
                    enabled_dependents.append(other.get("id"))
        if enabled_dependents:
            raise PluginAdminError(
                "插件仍被启用的插件依赖: %s" % ", ".join(enabled_dependents)
            )
        self.registry.upsert(plugin_id, record, enabled=False)
        self.registry.save()
        return self.registry.get(plugin_id)

    def uninstall(self, plugin_id, clear_data=False, confirmed=False):
        record = self._require_record(plugin_id)
        if record.get("source") == "builtin":
            raise PluginAdminError("内置插件不能卸载")
        if clear_data and not confirmed:
            raise PluginAdminError("卸载并清理插件数据必须显式确认")
        install_root = os.path.abspath(os.path.join(self.paths.installed_plugins_root, plugin_id))
        trash_parent = None
        trash_target = None
        try:
            if os.path.exists(install_root):
                allowed_root = os.path.abspath(self.paths.installed_plugins_root)
                if os.path.commonpath([allowed_root, install_root]) != allowed_root:
                    raise PluginAdminError("插件安装路径无效")
                os.makedirs(self.paths.temp_root, exist_ok=True)
                trash_parent = tempfile.mkdtemp(prefix="uninstall-", dir=self.paths.temp_root)
                trash_target = os.path.join(trash_parent, plugin_id)
                shutil.move(install_root, trash_target)
            self.registry.remove(plugin_id)
            try:
                self.registry.save()
            except Exception:
                if trash_target and os.path.exists(trash_target):
                    os.makedirs(os.path.dirname(install_root), exist_ok=True)
                    shutil.move(trash_target, install_root)
                self.registry.reload()
                raise
            if clear_data:
                self._clear_data(plugin_id)
            return True
        except Exception as error:
            logger.exception("卸载插件失败: %s", plugin_id)
            raise PluginAdminError("卸载插件失败: %s" % error) from error
        finally:
            if trash_parent and os.path.exists(trash_parent):
                shutil.rmtree(trash_parent, ignore_errors=True)

    def _clear_data(self, plugin_id):
        data_root = os.path.abspath(self.paths.plugin_data_dir(plugin_id))
        allowed_root = os.path.abspath(self.paths.plugin_data_root)
        if os.path.commonpath([allowed_root, data_root]) != allowed_root:
            raise PluginAdminError("插件数据路径无效")
        if os.path.exists(data_root):
            shutil.rmtree(data_root)

    def reset_config(self, plugin_id):
        self._require_record(plugin_id)
        atomic_write_json(self.paths.plugin_config_file(plugin_id), {}, indent=2)
        return True

    def clear_data(self, plugin_id, confirmed=False):
        self._require_record(plugin_id)
        if not confirmed:
            raise PluginAdminError("清理插件数据必须显式确认")
        self._clear_data(plugin_id)
        return True

    def uninstall_and_clear(self, plugin_id, confirmed=False):
        return self.uninstall(plugin_id, clear_data=True, confirmed=confirmed)

    # Friendly aliases used by callers that model the settings action as an
    # import/uninstall operation rather than a package installation.
    install_plugin = install_package
    import_package = install_package
    uninstall_plugin = uninstall
