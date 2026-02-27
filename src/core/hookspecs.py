"""
插件钩子规范模块 (Plugin Hook Specifications Module)

本模块定义了 NeoSec 框架基于 pluggy 的所有钩子规范 (Hook Specifications)。
这些规范构成了插件系统的契约接口，所有适配器插件必须通过 @hookimpl 实现这些钩子。

架构设计理念：
- 采用发布-订阅模式 (Publish-Subscribe Pattern)
- 多个插件可同时监听同一钩子事件
- 实现完全解耦的事件驱动架构 (Event-Driven Architecture)
"""

from typing import Any, Optional
import pluggy

# 创建钩子规范标记器 (Hook Specification Marker)
hookspec = pluggy.HookspecMarker("neosec")

# 创建钩子实现标记器 (Hook Implementation Marker) - 供适配器使用
hookimpl = pluggy.HookimplMarker("neosec")


@hookspec
def neosec_add_cli_options(parser: Any) -> None:
    """
    CLI 参数注册钩子 (CLI Options Registration Hook)

    允许各个工具适配器向主程序的命令行参数解析器 (Argument Parser) 注册自定义参数。
    例如：Nmap 适配器可以注册 --nmap-rate 参数。

    Args:
        parser: argparse.ArgumentParser 实例

    示例实现:
        @hookimpl
        def neosec_add_cli_options(parser):
            parser.add_argument('--nmap-rate', type=int, default=1000)
    """


@hookspec
def neosec_validate_dependencies() -> dict[str, bool]:
    """
    依赖预检钩子 (Dependency Validation Hook)

    在框架启动时调用，检查所有已启用插件所需的外部工具是否存在且可执行。
    每个适配器返回其依赖工具的检查结果。

    Returns:
        字典，键为工具名称，值为是否可用的布尔值
        例如: {"nmap": True, "nuclei": False}

    示例实现:
        @hookimpl
        def neosec_validate_dependencies():
            return {"nmap": shutil.which("nmap") is not None}
    """


@hookspec
def neosec_register_tool() -> dict[str, Any]:
    """
    工具注册钩子 (Tool Registration Hook)

    每个适配器通过此钩子向框架注册自己的元数据信息。

    Returns:
        工具元数据字典，包含以下字段:
        - name: 工具名称 (str)
        - category: 工具分类 (str) - "recon", "scanner", "fuzzer" 等
        - version: 适配器版本 (str)
        - description: 工具描述 (str)
        - required_binaries: 依赖的二进制文件列表 (list[str])

    示例实现:
        @hookimpl
        def neosec_register_tool():
            return {
                "name": "nmap",
                "category": "recon",
                "version": "1.0.0",
                "description": "Network Mapper - 网络端口扫描器",
                "required_binaries": ["nmap"]
            }
    """


@hookspec(firstresult=True)
def neosec_build_command(
    tool_name: str,
    target: str,
    options: dict[str, Any]
) -> Optional[list[str]]:
    """
    命令构建钩子 (Command Building Hook)

    根据目标和选项构建外部工具的完整命令行参数列表。
    使用 firstresult=True 确保只有匹配的适配器响应。

    Args:
        tool_name: 工具名称（如 "nmap"）
        target: 扫描目标（IP、域名或 URL）
        options: 工具特定的配置选项字典

    Returns:
        命令参数列表（如 ["nmap", "-sV", "-p-", "192.168.1.1"]）
        如果适配器不处理该工具，返回 None

    示例实现:
        @hookimpl
        def neosec_build_command(tool_name, target, options):
            if tool_name != "nmap":
                return None
            cmd = ["nmap", "-sV", target]
            if options.get("fast_mode"):
                cmd.insert(1, "-T4")
            return cmd
    """


@hookspec
def neosec_on_scan_start(target: str, workflow_name: str) -> None:
    """
    扫描启动钩子 (Scan Start Hook)

    在整个扫描工作流开始前触发，用于初始化资源、记录日志等。

    Args:
        target: 扫描目标
        workflow_name: 工作流名称

    示例实现:
        @hookimpl
        def neosec_on_scan_start(target, workflow_name):
            logger.info(f"开始扫描目标: {target}, 工作流: {workflow_name}")
    """


@hookspec
def neosec_on_tool_execute(
    tool_name: str,
    command: list[str],
    target: str
) -> None:
    """
    工具执行前钩子 (Tool Pre-Execution Hook)

    在每个外部工具执行前触发，用于日志记录、资源分配等。

    Args:
        tool_name: 工具名称
        command: 完整命令列表
        target: 扫描目标

    示例实现:
        @hookimpl
        def neosec_on_tool_execute(tool_name, command, target):
            logger.debug(f"执行工具: {tool_name}, 命令: {' '.join(command)}")
    """


@hookspec(firstresult=True)
def neosec_parse_output(
    tool_name: str,
    raw_output: str,
    output_format: str
) -> Optional[dict[str, Any]]:
    """
    输出解析钩子 (Output Parsing Hook)

    将外部工具的原始输出解析为标准化的内部数据结构。
    使用 firstresult=True 确保只有对应的适配器处理。

    Args:
        tool_name: 工具名称
        raw_output: 原始输出字符串或文件路径
        output_format: 输出格式（"json", "xml", "text"）

    Returns:
        解析后的标准化数据字典，包含 Asset 或 Vulnerability 对象列表
        如果适配器不处理该工具，返回 None

    示例实现:
        @hookimpl
        def neosec_parse_output(tool_name, raw_output, output_format):
            if tool_name != "nmap":
                return None
            # 解析 XML 输出...
            return {"assets": [...], "vulnerabilities": [...]}
    """


@hookspec
def neosec_on_result_parsed(
    tool_name: str,
    parsed_data: dict[str, Any]
) -> None:
    """
    结果解析完成钩子 (Result Parsed Hook)

    在适配器完成输出解析后触发，用于报告生成、通知推送等后置处理。

    Args:
        tool_name: 工具名称
        parsed_data: 解析后的标准化数据

    示例实现:
        @hookimpl
        def neosec_on_result_parsed(tool_name, parsed_data):
            # 生成 HTML 报告
            # 发送 Slack 通知
            pass
    """


@hookspec
def neosec_on_scan_complete(
    target: str,
    workflow_name: str,
    results: dict[str, Any]
) -> None:
    """
    扫描完成钩子 (Scan Complete Hook)

    在整个扫描工作流完成后触发，用于资源清理、最终报告生成等。

    Args:
        target: 扫描目标
        workflow_name: 工作流名称
        results: 汇总的扫描结果

    示例实现:
        @hookimpl
        def neosec_on_scan_complete(target, workflow_name, results):
            logger.info(f"扫描完成: {target}")
            # 生成最终报告
    """


@hookspec
def neosec_on_error(
    error: Exception,
    context: dict[str, Any]
) -> None:
    """
    错误处理钩子 (Error Handling Hook)

    当框架或插件执行过程中发生异常时触发。

    Args:
        error: 捕获的异常对象
        context: 错误上下文信息（工具名称、目标等）

    示例实现:
        @hookimpl
        def neosec_on_error(error, context):
            logger.error(f"错误: {error}, 上下文: {context}")
            # 发送告警通知
    """
