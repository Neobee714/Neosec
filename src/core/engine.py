"""
核心引擎模块 (Core Engine Module)

本模块实现 NeoSec 框架的核心引擎，负责：
1. 初始化 pluggy PluginManager (插件管理器)
2. 自动发现并加载所有适配器插件
3. 提供全局的插件调用接口
4. 管理框架的生命周期事件
"""

from typing import Any, Optional
import sys
from pathlib import Path
import pluggy

from .hookspecs import hookspec, hookimpl
from .exceptions import PluginLoadError, DependencyMissingError


class NeoSecEngine:
    """
    NeoSec 核心引擎类 (Core Engine Class)

    单例模式 (Singleton Pattern) 的核心调度引擎，管理整个框架的插件生态系统。
    """

    _instance: Optional['NeoSecEngine'] = None

    def __new__(cls) -> 'NeoSecEngine':
        """确保引擎为单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化核心引擎"""
        if hasattr(self, '_initialized'):
            return

        # 创建 pluggy 插件管理器 (PluginManager)
        self.pm: pluggy.PluginManager = pluggy.PluginManager("neosec")

        # 注册钩子规范 (Hook Specifications)
        # 导入 hookspecs 模块并添加规范
        from . import hookspecs as hookspecs_module
        self.pm.add_hookspecs(hookspecs_module)

        # 已加载的插件注册表 (Loaded Plugins Registry)
        self.loaded_plugins: dict[str, Any] = {}

        # 工具元数据缓存 (Tool Metadata Cache)
        self.tool_registry: dict[str, dict[str, Any]] = {}

        self._initialized = True

    def discover_and_load_plugins(self, plugin_dirs: Optional[list[Path]] = None) -> None:
        """
        自动发现并加载插件 (Auto-discover and Load Plugins)

        扫描指定目录下的所有 Python 模块，查找包含 @hookimpl 装饰器的插件并注册。

        Args:
            plugin_dirs: 插件目录列表，默认为 src/adapters/ 和 src/plugins/

        Raises:
            PluginLoadError: 插件加载失败时抛出
        """
        if plugin_dirs is None:
            # 默认插件目录
            base_path = Path(__file__).parent.parent
            plugin_dirs = [
                base_path / "adapters",
                base_path / "plugins"
            ]

        for plugin_dir in plugin_dirs:
            if not plugin_dir.exists():
                continue

            # 递归扫描所有 Python 文件
            for py_file in plugin_dir.rglob("*.py"):
                if py_file.name.startswith("_"):
                    continue

                # 构建模块路径
                relative_path = py_file.relative_to(base_path.parent)
                module_path = str(relative_path.with_suffix("")).replace("/", ".").replace("\\", ".")

                try:
                    # 动态导入模块
                    if module_path not in sys.modules:
                        module = __import__(module_path, fromlist=[""])
                    else:
                        module = sys.modules[module_path]

                    # 注册插件
                    self.pm.register(module, name=module_path)
                    self.loaded_plugins[module_path] = module

                except Exception as e:
                    raise PluginLoadError(
                        plugin_name=module_path,
                        reason=f"导入失败: {str(e)}"
                    )

    def register_plugin(self, plugin_module: Any, name: Optional[str] = None) -> None:
        """
        手动注册单个插件 (Manually Register a Plugin)

        Args:
            plugin_module: 插件模块对象
            name: 插件名称（可选，默认使用模块名）

        Raises:
            PluginLoadError: 插件注册失败时抛出
        """
        try:
            plugin_name = name or plugin_module.__name__
            self.pm.register(plugin_module, name=plugin_name)
            self.loaded_plugins[plugin_name] = plugin_module
        except Exception as e:
            raise PluginLoadError(
                plugin_name=plugin_name,
                reason=f"注册失败: {str(e)}"
            )

    def validate_all_dependencies(self) -> dict[str, bool]:
        """
        验证所有插件的依赖 (Validate All Plugin Dependencies)

        调用所有插件的 neosec_validate_dependencies 钩子，汇总依赖检查结果。

        Returns:
            依赖检查结果字典，键为工具名称，值为是否可用

        Raises:
            DependencyMissingError: 存在缺失的关键依赖时抛出
        """
        all_dependencies: dict[str, bool] = {}

        # 调用所有插件的依赖验证钩子
        results = self.pm.hook.neosec_validate_dependencies()

        # 合并所有插件返回的依赖字典
        for result in results:
            if isinstance(result, dict):
                all_dependencies.update(result)

        # 检查是否有缺失的依赖
        missing_tools = [tool for tool, available in all_dependencies.items() if not available]

        if missing_tools:
            raise DependencyMissingError(
                tool_name=", ".join(missing_tools),
                expected_path="请检查系统 PATH 环境变量或配置文件"
            )

        return all_dependencies

    def build_tool_registry(self) -> None:
        """
        构建工具注册表 (Build Tool Registry)

        调用所有插件的 neosec_register_tool 钩子，收集工具元数据。
        """
        self.tool_registry.clear()

        # 调用所有插件的工具注册钩子
        results = self.pm.hook.neosec_register_tool()

        for result in results:
            if isinstance(result, dict) and "name" in result:
                tool_name = result["name"]
                self.tool_registry[tool_name] = result

    def get_tool_info(self, tool_name: str) -> Optional[dict[str, Any]]:
        """
        获取工具元数据 (Get Tool Metadata)

        Args:
            tool_name: 工具名称

        Returns:
            工具元数据字典，如果工具不存在则返回 None
        """
        return self.tool_registry.get(tool_name)

    def list_available_tools(self, category: Optional[str] = None) -> list[str]:
        """
        列出所有可用工具 (List Available Tools)

        Args:
            category: 可选的工具分类过滤（"recon", "scanner", "fuzzer"）

        Returns:
            工具名称列表
        """
        if category is None:
            return list(self.tool_registry.keys())

        return [
            name for name, info in self.tool_registry.items()
            if info.get("category") == category
        ]

    def initialize(self, plugin_dirs: Optional[list[Path]] = None) -> None:
        """
        初始化引擎 (Initialize Engine)

        完整的初始化流程：加载插件 -> 验证依赖 -> 构建注册表

        Args:
            plugin_dirs: 插件目录列表

        Raises:
            PluginLoadError: 插件加载失败
            DependencyMissingError: 依赖缺失
        """
        # 1. 发现并加载所有插件
        self.discover_and_load_plugins(plugin_dirs)

        # 2. 构建工具注册表
        self.build_tool_registry()

        # 3. 验证依赖（可选，根据配置决定是否严格检查）
        # self.validate_all_dependencies()

    def shutdown(self) -> None:
        """
        关闭引擎 (Shutdown Engine)

        清理资源，卸载所有插件。
        """
        self.loaded_plugins.clear()
        self.tool_registry.clear()
        # pluggy 不提供显式的卸载方法，重新创建 PluginManager 即可
        self.pm = pluggy.PluginManager("neosec")


# 全局引擎实例 (Global Engine Instance)
_engine: Optional[NeoSecEngine] = None


def get_engine() -> NeoSecEngine:
    """
    获取全局引擎实例 (Get Global Engine Instance)

    Returns:
        NeoSecEngine 单例实例
    """
    global _engine
    if _engine is None:
        _engine = NeoSecEngine()
    return _engine
