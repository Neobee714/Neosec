"""
核心模块 (Core Module)

NeoSec 框架的核心底座，包含插件系统、引擎、配置解析和异常定义。
"""

from .engine import NeoSecEngine, get_engine
from .hookspecs import hookspec, hookimpl
from .config_parser import (
    ConfigParser,
    GlobalConfig,
    ToolConfig,
    WorkflowConfig,
    WorkflowTask
)
from .exceptions import (
    NeoSecBaseException,
    ToolExecutionError,
    SubprocessDeadlockError,
    SubprocessTimeoutError,
    ConfigurationError,
    PluginLoadError,
    DependencyMissingError,
    WorkflowValidationError,
    DataParsingError
)

__all__ = [
    # 引擎
    "NeoSecEngine",
    "get_engine",
    # 钩子
    "hookspec",
    "hookimpl",
    # 配置
    "ConfigParser",
    "GlobalConfig",
    "ToolConfig",
    "WorkflowConfig",
    "WorkflowTask",
    # 异常
    "NeoSecBaseException",
    "ToolExecutionError",
    "SubprocessDeadlockError",
    "SubprocessTimeoutError",
    "ConfigurationError",
    "PluginLoadError",
    "DependencyMissingError",
    "WorkflowValidationError",
    "DataParsingError",
]
