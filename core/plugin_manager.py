"""Discovery and runtime loading for ordinary ToolX feature plugins."""

from copy import deepcopy
import importlib
import importlib.util
import logging
import os
import sys

from .app_paths import PluginPaths, validate_plugin_id
from .plugin_admin import PluginAdminService
from .plugin_interface import PluginInterface
from .plugin_manifest import (
    PLUGIN_API_VERSION,
    TOOLX_VERSION,
    PluginManifest,
    PluginManifestError,
)
from .plugin_context import PluginContext


logger = logging.getLogger(__name__)


class PluginManager:
    """Load enabled feature plugins while keeping system pages out of the scan."""

    CORE_PLUGIN_DIRS = frozenset(("settings", "about"))

    def __init__(
        self,
        config_manager=None,
        plugin_package="plugins",
        plugin_dir=None,
        paths=None,
        plugin_admin=None,
    ):
        self.config_manager = config_manager
        self.plugin_package = plugin_package
        self.plugins = {}
        self.plugin_contexts = {}
        self.plugin_manifests = {}
        self.plugin_records = {}
        self._config_change_handlers = {}
        self._system_context = None

        if plugin_dir is not None:
            self.plugin_dir = os.path.abspath(os.fspath(plugin_dir))
        else:
            if getattr(sys, "frozen", False):
                base_dir = sys._MEIPASS
            else:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.plugin_dir = os.path.join(base_dir, self.plugin_package)

        if paths is None and config_manager is not None:
            paths = getattr(config_manager, "paths", None)
        if paths is None and config_manager is None and plugin_dir is not None:
            # Keep tests and embedders from writing a registry into the real
            # user's profile when they only provide a temporary plugin tree.
            paths = os.path.join(os.path.dirname(self.plugin_dir), ".toolx-data")
        self.paths = paths if isinstance(paths, PluginPaths) else PluginPaths(paths)

        os.makedirs(self.plugin_dir, exist_ok=True)
        self.plugin_admin = plugin_admin or PluginAdminService(
            app_settings=config_manager,
            paths=self.paths,
            plugin_manager=self,
            builtin_plugin_dir=self.plugin_dir,
        )
        if getattr(self.plugin_admin, "plugin_manager", None) is None:
            self.plugin_admin.plugin_manager = self
        # A supplied admin service may have been created before the manager;
        # make sure metadata-only discovery still sees this builtin root.
        if getattr(self.plugin_admin, "builtin_plugin_dir", None) is None:
            self.plugin_admin.builtin_plugin_dir = self.plugin_dir
        self.admin_service = self.plugin_admin
        self.plugin_registry = self.plugin_admin.registry

    def _read_manifest(self, plugin_dir, source="builtin"):
        manifest_file = os.path.join(plugin_dir, "plugin.json")
        if not os.path.isfile(manifest_file):
            return None
        try:
            manifest = PluginManifest.from_file(
                manifest_file,
                source=source,
                root_path=plugin_dir,
            )
            if not manifest.is_compatible(TOOLX_VERSION, PLUGIN_API_VERSION):
                raise PluginManifestError("插件与当前 ToolX 或插件 API 版本不兼容")
            return manifest
        except PluginManifestError:
            logger.exception("插件清单无效，跳过: %s", manifest_file)
            return False

    def _is_enabled(self, plugin_id, default=True):
        record = self.plugin_admin.get_plugin(plugin_id)
        return default if record is None else bool(record.get("enabled", default))

    def _builtin_candidates(self):
        try:
            folder_names = sorted(os.listdir(self.plugin_dir))
        except Exception:
            logger.exception("无法扫描插件目录: %s", self.plugin_dir)
            return

        for folder_name in folder_names:
            plugin_path = os.path.join(self.plugin_dir, folder_name)
            if (
                not os.path.isdir(plugin_path)
                or folder_name.startswith("__")
                or folder_name in self.CORE_PLUGIN_DIRS
            ):
                continue
            module_file = os.path.join(plugin_path, "plugin.py")
            if not os.path.isfile(module_file):
                continue

            manifest = self._read_manifest(plugin_path, source="builtin")
            if manifest is False:
                continue
            if manifest is not None:
                try:
                    self.plugin_admin.register_builtin(manifest, plugin_path)
                except Exception:
                    logger.exception("注册内置插件失败: %s", folder_name)
                    continue
                if not self._is_enabled(manifest.id):
                    continue
                yield {
                    "root": plugin_path,
                    "entry_file": manifest.entry_file,
                    "manifest": manifest,
                    "source": "builtin",
                    "folder_name": folder_name,
                }
                continue

            # Short-lived compatibility path for old builtin/test plugins
            # without plugin.json.  It still receives a restricted context.
            try:
                validate_plugin_id(folder_name)
            except ValueError:
                logger.warning("旧插件目录名不是合法插件 ID，跳过: %s", folder_name)
                continue
            if not self._is_enabled(folder_name):
                continue
            yield {
                "root": plugin_path,
                "entry_file": module_file,
                "manifest": None,
                "source": "builtin",
                "folder_name": folder_name,
            }

    def _imported_candidates(self):
        for record in self.plugin_admin.list_installed():
            if record.get("source") != "imported" or not record.get("enabled", True):
                continue
            plugin_path = record.get("install_path")
            if not plugin_path or not os.path.isdir(plugin_path):
                logger.error("已安装插件路径不存在，跳过: %s", record.get("id"))
                continue
            manifest = self._read_manifest(plugin_path, source="imported")
            if not manifest:
                continue
            yield {
                "root": plugin_path,
                "entry_file": manifest.entry_file,
                "manifest": manifest,
                "source": "imported",
                "folder_name": manifest.id,
            }

    def _load_builtin_module(self, candidate):
        folder_name = candidate["folder_name"]
        manifest = candidate.get("manifest")
        if manifest is None or manifest.entry_module == "plugin":
            module_name = "%s.%s.plugin" % (self.plugin_package, folder_name)
        else:
            package_name = "%s.%s" % (self.plugin_package, folder_name)
            importlib.import_module(package_name)
            module_name = "%s.%s" % (package_name, manifest.entry_module)
        importlib.invalidate_caches()
        if module_name in sys.modules:
            module = importlib.reload(sys.modules[module_name])
        else:
            module = importlib.import_module(module_name)
        # Preserve the old development workflow where editing an in-tree
        # plugin and restarting the manager picks up the latest source.
        return module

    def _load_imported_module(self, candidate):
        manifest = candidate["manifest"]
        root = candidate["root"]
        package_name = "_toolx_imported_%s_%s" % (
            manifest.id,
            manifest.version.replace(".", "_").replace("-", "_")
        )
        init_file = os.path.join(root, "__init__.py")
        if os.path.isfile(init_file):
            package_spec = importlib.util.spec_from_file_location(
                package_name,
                init_file,
                submodule_search_locations=[root],
            )
        else:
            package_spec = importlib.util.spec_from_loader(
                package_name,
                loader=None,
                is_package=True,
            )
            if package_spec is not None:
                package_spec.submodule_search_locations = [root]
        if package_spec is None:
            raise ImportError("无法创建插件包模块")
        package_module = importlib.util.module_from_spec(package_spec)
        sys.modules[package_name] = package_module
        if package_spec.loader is not None:
            package_spec.loader.exec_module(package_module)

        module_name = "%s.%s" % (package_name, manifest.entry_module)
        module_spec = importlib.util.spec_from_file_location(module_name, manifest.entry_file)
        if module_spec is None or module_spec.loader is None:
            raise ImportError("无法创建插件入口模块")
        module = importlib.util.module_from_spec(module_spec)
        sys.modules[module_name] = module
        module_spec.loader.exec_module(module)
        return module

    def _connect_config_notifications(self, plugin_id, plugin_instance, context):
        config = getattr(context, "config", None)
        changed_signal = getattr(config, "changed", None)
        if changed_signal is None:
            return

        def handle_change(key, value):
            try:
                plugin_instance.on_config_changed(key, value)
            except Exception:
                logger.exception("插件 %s 响应配置变化失败", plugin_id)

        changed_signal.connect(handle_change)
        self._config_change_handlers[plugin_id] = (config, handle_change)

    def _disconnect_config_notifications(self, plugin_id):
        handler_record = self._config_change_handlers.pop(plugin_id, None)
        if handler_record is None:
            return

        config, handle_change = handler_record
        try:
            config.changed.disconnect(handle_change)
        except (TypeError, RuntimeError):
            pass

    def _load_candidate(self, candidate):
        manifest = candidate["manifest"]
        plugin_id_hint = manifest.id if manifest is not None else candidate["folder_name"]
        context = PluginContext.create(
            plugin_id_hint,
            self.paths,
            app_settings=self.config_manager,
        )

        if candidate["source"] == "builtin":
            module = self._load_builtin_module(candidate)
        else:
            module = self._load_imported_module(candidate)

        factory = getattr(module, "get_plugin", None)
        if not callable(factory):
            raise TypeError("未实现可调用的 get_plugin() 方法")

        plugin_instance = factory(context)
        if not isinstance(plugin_instance, PluginInterface):
            raise TypeError("get_plugin() 未返回 PluginInterface 实例")

        plugin_id = plugin_instance.get_id()
        plugin_name = plugin_instance.get_name()
        try:
            validate_plugin_id(plugin_id)
        except ValueError as error:
            raise ValueError("插件 ID 无效: %s" % error) from error
        if not isinstance(plugin_name, str) or not plugin_name.strip():
            raise ValueError("插件名称必须是非空字符串")
        if manifest is not None and plugin_id != manifest.id:
            raise ValueError("插件实现 ID 与 plugin.json 不一致")
        if plugin_id in {"sys_settings", "sys_about", "settings", "about"}:
            raise ValueError("核心系统页面不能作为普通插件加载")
        if plugin_id in self.plugins:
            logger.error(
                "发现重复插件 ID，跳过插件 %s (%s); 已保留已有插件",
                candidate["folder_name"],
                plugin_id,
            )
            return

        # Legacy plugins may use a folder name different from their runtime
        # id. Rebind the context after validation; manifest-based plugins do
        # not take this path.
        if context.plugin_id != plugin_id:
            context = PluginContext.create(
                plugin_id,
                self.paths,
                app_settings=self.config_manager,
            )
            plugin_instance.context = context

        self._connect_config_notifications(plugin_id, plugin_instance, context)
        try:
            plugin_instance.on_load()
        except Exception:
            self._disconnect_config_notifications(plugin_id)
            logger.exception("插件 %s 的 on_load() 执行失败", plugin_id)
            try:
                plugin_instance.on_unload()
            except Exception:
                logger.exception("插件 %s 的失败清理 on_unload() 也执行失败", plugin_id)
            return

        self.plugins[plugin_id] = plugin_instance
        self.plugin_contexts[plugin_id] = context
        if manifest is not None:
            self.plugin_manifests[plugin_id] = manifest
        record = self.plugin_admin.get_plugin(plugin_id) or {
            "id": plugin_id,
            "version": manifest.version if manifest is not None else "0.0.0",
            "source": candidate["source"],
            "enabled": True,
            "install_path": candidate["root"],
        }
        self.plugin_records[plugin_id] = record
        logger.info("成功加载插件: %s (%s)", plugin_name, plugin_id)

    def load_all_plugins(self):
        """Load enabled ordinary plugins; a single failure is isolated."""
        self.unload_all()
        for candidate in list(self._builtin_candidates()) + list(self._imported_candidates()):
            try:
                self._load_candidate(candidate)
            except Exception:
                logger.exception("加载插件 %s 时发生错误", candidate.get("folder_name"))
        logger.info("插件扫描完成，共加载 %d 个插件", len(self.plugins))
        return self.plugins

    def get_plugins(self):
        return self.plugins

    def get_plugin(self, plugin_id):
        return self.plugins.get(plugin_id)

    def get_plugin_context(self, plugin_id):
        return self.plugin_contexts.get(plugin_id)

    def get_plugin_manifest(self, plugin_id):
        return self.plugin_manifests.get(plugin_id)

    def get_plugin_metadata(self, plugin_id):
        return deepcopy(self.plugin_records.get(plugin_id))

    def list_installed(self):
        return self.plugin_admin.list_installed()

    def get_system_context(self):
        if self._system_context is None:
            from .system_context import SystemContext

            self._system_context = SystemContext.create(
                app_settings=self.config_manager,
                plugin_manager=self,
                plugin_admin=self.plugin_admin,
            )
        return self._system_context

    def unload_all(self):
        for plugin_id, plugin in list(self.plugins.items()):
            self._disconnect_config_notifications(plugin_id)
            try:
                plugin.on_unload()
            except Exception:
                logger.exception("卸载插件 %s 失败", plugin_id)
        self.plugins.clear()
        self.plugin_contexts.clear()
        self.plugin_manifests.clear()
        self.plugin_records.clear()


FeaturePluginManager = PluginManager
