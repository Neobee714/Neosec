"""
自定义异常类模块 (Custom Exception Classes Module)

本模块定义了 NeoSec 框架中所有自定义异常类型，用于精准捕获和处理系统运行时的各类错误场景。
严格遵循异常层级设计原则，避免使用宽泛的 Exception 捕获。
"""

from typing import Optional


class NeoSecBaseException(Exception):
    """
    NeoSec 框架基础异常类 (Base Exception for NeoSec Framework)

    所有自定义异常的根基类，提供统一的异常处理接口。
    """

    def __init__(self, message: str, details: Optional[dict] = None):
        """
        初始化异常实例

        Args:
            message: 异常描述信息
            details: 可选的详细错误上下文字典
        """
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        """返回格式化的异常信息"""
        if self.details:
            return f"{self.message} | 详情 (Details): {self.details}"
        return self.message


class ToolExecutionError(NeoSecBaseException):
    """
    工具执行异常 (Tool Execution Error)

    当外部安全工具（如 Nmap、Nuclei）执行失败时抛出此异常。
    包含工具名称、命令参数、退出码等关键调试信息。
    """

    def __init__(
        self,
        tool_name: str,
        command: list[str],
        exit_code: int,
        stderr: Optional[str] = None
    ):
        """
        初始化工具执行异常

        Args:
            tool_name: 工具名称（如 "nmap"）
            command: 执行的完整命令列表
            exit_code: 进程退出码 (Exit Code)
            stderr: 标准错误输出 (Standard Error Output)
        """
        details = {
            "tool": tool_name,
            "command": " ".join(command),
            "exit_code": exit_code,
            "stderr": stderr or "无错误输出 (No stderr output)"
        }
        message = f"工具 '{tool_name}' 执行失败，退出码: {exit_code}"
        super().__init__(message, details)


class SubprocessDeadlockError(NeoSecBaseException):
    """
    子进程死锁异常 (Subprocess Deadlock Error)

    当子进程因管道缓冲区耗尽 (Pipe Exhaustion) 或其他原因陷入死锁时抛出。
    """

    def __init__(self, tool_name: str, pid: int, reason: str):
        """
        初始化子进程死锁异常

        Args:
            tool_name: 工具名称
            pid: 进程ID (Process ID)
            reason: 死锁原因描述
        """
        details = {"tool": tool_name, "pid": pid, "reason": reason}
        message = f"子进程 '{tool_name}' (PID: {pid}) 陷入死锁"
        super().__init__(message, details)


class SubprocessTimeoutError(NeoSecBaseException):
    """
    子进程超时异常 (Subprocess Timeout Error)

    当子进程执行时间超过预设的 Timeout (超时限制) 时抛出。
    """

    def __init__(self, tool_name: str, timeout_seconds: int):
        """
        初始化子进程超时异常

        Args:
            tool_name: 工具名称
            timeout_seconds: 超时时长（秒）
        """
        details = {"tool": tool_name, "timeout": timeout_seconds}
        message = f"工具 '{tool_name}' 执行超时（{timeout_seconds}秒）"
        super().__init__(message, details)


class ConfigurationError(NeoSecBaseException):
    """
    配置错误异常 (Configuration Error)

    当 YAML 配置文件解析失败或配置项不合法时抛出。
    """

    def __init__(self, config_file: str, reason: str):
        """
        初始化配置错误异常

        Args:
            config_file: 配置文件路径
            reason: 错误原因
        """
        details = {"config_file": config_file, "reason": reason}
        message = f"配置文件 '{config_file}' 解析失败"
        super().__init__(message, details)


class PluginLoadError(NeoSecBaseException):
    """
    插件加载异常 (Plugin Load Error)

    当 pluggy 插件系统无法加载或注册插件时抛出。
    """

    def __init__(self, plugin_name: str, reason: str):
        """
        初始化插件加载异常

        Args:
            plugin_name: 插件名称
            reason: 加载失败原因
        """
        details = {"plugin": plugin_name, "reason": reason}
        message = f"插件 '{plugin_name}' 加载失败"
        super().__init__(message, details)


class DependencyMissingError(NeoSecBaseException):
    """
    依赖缺失异常 (Dependency Missing Error)

    当系统检测到必需的外部工具二进制文件不存在或无执行权限时抛出。
    """

    def __init__(self, tool_name: str, expected_path: Optional[str] = None):
        """
        初始化依赖缺失异常

        Args:
            tool_name: 缺失的工具名称
            expected_path: 预期的工具路径（可选）
        """
        details = {"tool": tool_name}
        if expected_path:
            details["expected_path"] = expected_path
        message = f"依赖工具 '{tool_name}' 未找到或无执行权限"
        super().__init__(message, details)


class WorkflowValidationError(NeoSecBaseException):
    """
    工作流验证异常 (Workflow Validation Error)

    当 DAG (Directed Acyclic Graph - 有向无环图) 工作流配置存在循环依赖或其他拓扑错误时抛出。
    """

    def __init__(self, workflow_name: str, reason: str):
        """
        初始化工作流验证异常

        Args:
            workflow_name: 工作流名称
            reason: 验证失败原因
        """
        details = {"workflow": workflow_name, "reason": reason}
        message = f"工作流 '{workflow_name}' 验证失败"
        super().__init__(message, details)


class DataParsingError(NeoSecBaseException):
    """
    数据解析异常 (Data Parsing Error)

    当适配器无法解析外部工具的输出（如 XML、JSON）时抛出。
    """

    def __init__(self, tool_name: str, data_format: str, reason: str):
        """
        初始化数据解析异常

        Args:
            tool_name: 工具名称
            data_format: 数据格式（如 "XML", "JSON"）
            reason: 解析失败原因
        """
        details = {
            "tool": tool_name,
            "format": data_format,
            "reason": reason
        }
        message = f"无法解析 '{tool_name}' 的 {data_format} 输出"
        super().__init__(message, details)
