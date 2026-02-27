"""
NeoSec 主入口文件 (Main Entry Point)

渗透测试百宝箱 - 企业级自动化安全测试框架
"""

import sys
import argparse
from pathlib import Path
from typing import Optional

from src.core import get_engine, ConfigParser
from src.utils import setup_logger, get_logger
from src.execution import ProcessRunner, WorkflowDAG, WorkflowExecutor
from src.core.exceptions import NeoSecBaseException


def parse_arguments() -> argparse.Namespace:
    """
    解析命令行参数 (Parse Command Line Arguments)

    Returns:
        解析后的参数对象
    """
    parser = argparse.ArgumentParser(
        prog="neosec",
        description="NeoSec - 企业级自动化渗透测试框架",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 使用默认工作流扫描目标
  python main.py scan -t 192.168.1.1

  # 使用自定义工作流
  python main.py scan -t example.com -w configs/custom_workflow.yaml

  # 列出所有可用工具
  python main.py list-tools

  # 生成默认配置文件
  python main.py init-config
        """
    )

    # 全局参数
    parser.add_argument(
        "-c", "--config",
        type=Path,
        default=Path("configs/neosec.yaml"),
        help="配置文件路径（默认: configs/neosec.yaml）"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="启用详细输出（DEBUG 级别）"
    )

    parser.add_argument(
        "--log-file",
        type=Path,
        help="日志文件路径（可选）"
    )

    # 子命令
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # scan 命令
    scan_parser = subparsers.add_parser("scan", help="执行安全扫描")
    scan_parser.add_argument(
        "-t", "--target",
        required=True,
        help="扫描目标（IP、域名或 URL）"
    )
    scan_parser.add_argument(
        "-w", "--workflow",
        type=Path,
        help="工作流配置文件路径"
    )
    scan_parser.add_argument(
        "-o", "--output",
        type=Path,
        help="输出目录（默认: data/reports）"
    )

    # list-tools 命令
    list_parser = subparsers.add_parser("list-tools", help="列出所有可用工具")
    list_parser.add_argument(
        "--category",
        choices=["recon", "scanner", "fuzzer"],
        help="按分类过滤工具"
    )

    # init-config 命令
    init_parser = subparsers.add_parser("init-config", help="生成默认配置文件")
    init_parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("configs/neosec.yaml"),
        help="配置文件输出路径"
    )

    # validate 命令
    validate_parser = subparsers.add_parser("validate", help="验证依赖和配置")

    return parser.parse_args()


def command_scan(args: argparse.Namespace, logger) -> int:
    """
    执行扫描命令 (Execute Scan Command)

    Args:
        args: 命令行参数
        logger: 日志实例

    Returns:
        退出码（0 表示成功）
    """
    logger.info(f"开始扫描目标: {args.target}")

    # 获取引擎实例
    engine = get_engine()

    try:
        # 初始化引擎（加载插件）
        logger.info("正在加载插件...")
        engine.initialize()
        logger.info(f"已加载 {len(engine.loaded_plugins)} 个插件")

        # 如果指定了工作流文件，加载工作流
        if args.workflow:
            logger.info(f"加载工作流配置: {args.workflow}")
            workflow_config = ConfigParser.load_workflow_from_file(args.workflow)
        else:
            logger.warning("未指定工作流，使用默认扫描流程")
            # TODO: 实现默认工作流
            logger.error("默认工作流尚未实现，请使用 -w 参数指定工作流文件")
            return 1

        # 构建 DAG
        logger.info(f"构建工作流 DAG: {workflow_config.name}")
        dag = WorkflowDAG(workflow_config)

        # 显示拓扑排序结果
        task_layers = dag.topological_sort()
        logger.info(f"工作流包含 {len(dag.nodes)} 个任务，分为 {len(task_layers)} 层")
        for i, layer in enumerate(task_layers):
            logger.debug(f"  第 {i+1} 层: {', '.join(layer)}")

        # 定义任务执行函数
        def execute_task(task):
            """执行单个任务"""
            logger.info(f"执行任务: {task.id} (工具: {task.tool})")

            # 构建命令
            command = engine.pm.hook.neosec_build_command(
                tool_name=task.tool,
                target=task.target or args.target,
                options=task.options
            )

            if not command:
                logger.error(f"无法构建工具 '{task.tool}' 的命令")
                return None

            # 执行命令
            runner = ProcessRunner(tool_name=task.tool, timeout=600)
            try:
                result = runner.run_sync(command)
                logger.info(f"任务 {task.id} 完成，耗时: {result.execution_time:.2f}s")

                # 解析输出
                parsed_data = engine.pm.hook.neosec_parse_output(
                    tool_name=task.tool,
                    raw_output=result.stdout,
                    output_format="xml"  # TODO: 根据工具动态确定
                )

                return parsed_data

            except Exception as e:
                logger.error(f"任务 {task.id} 执行失败: {e}")
                return None

        # 执行工作流
        logger.info("开始执行工作流...")
        executor = WorkflowExecutor(dag, execute_task, max_concurrent=3)
        scan_result = executor.execute_workflow_sync()

        # 输出结果统计
        logger.info("=" * 60)
        logger.info("扫描完成！")
        logger.info(f"发现资产: {scan_result.total_assets} 个")
        logger.info(f"发现漏洞: {scan_result.total_vulnerabilities} 个")
        logger.info(f"  - 严重: {scan_result.critical_count}")
        logger.info(f"  - 高危: {scan_result.high_count}")
        logger.info(f"  - 中危: {scan_result.medium_count}")
        logger.info(f"  - 低危: {scan_result.low_count}")
        logger.info(f"  - 信息: {scan_result.info_count}")
        logger.info(f"总耗时: {scan_result.duration_seconds} 秒")
        logger.info("=" * 60)

        return 0

    except NeoSecBaseException as e:
        logger.error(f"执行失败: {e}")
        return 1
    except Exception as e:
        logger.exception(f"未预期的错误: {e}")
        return 1


def command_list_tools(args: argparse.Namespace, logger) -> int:
    """
    列出所有可用工具 (List Available Tools)

    Args:
        args: 命令行参数
        logger: 日志实例

    Returns:
        退出码
    """
    engine = get_engine()

    try:
        # 初始化引擎
        engine.initialize()

        # 获取工具列表
        tools = engine.list_available_tools(category=args.category)

        if not tools:
            logger.info("未找到可用工具")
            return 0

        logger.info(f"可用工具列表 ({len(tools)} 个):")
        logger.info("=" * 60)

        for tool_name in sorted(tools):
            tool_info = engine.get_tool_info(tool_name)
            if tool_info:
                logger.info(f"  [{tool_info['category']}] {tool_name}")
                logger.info(f"    描述: {tool_info.get('description', 'N/A')}")
                logger.info(f"    依赖: {', '.join(tool_info.get('required_binaries', []))}")
                logger.info("")

        return 0

    except Exception as e:
        logger.error(f"列出工具失败: {e}")
        return 1


def command_init_config(args: argparse.Namespace, logger) -> int:
    """
    生成默认配置文件 (Generate Default Configuration)

    Args:
        args: 命令行参数
        logger: 日志实例

    Returns:
        退出码
    """
    try:
        output_path = args.output
        output_path.parent.mkdir(parents=True, exist_ok=True)

        ConfigParser.create_default_config(output_path)
        logger.info(f"默认配置文件已生成: {output_path}")

        return 0

    except Exception as e:
        logger.error(f"生成配置文件失败: {e}")
        return 1


def command_validate(args: argparse.Namespace, logger) -> int:
    """
    验证依赖和配置 (Validate Dependencies and Configuration)

    Args:
        args: 命令行参数
        logger: 日志实例

    Returns:
        退出码
    """
    engine = get_engine()

    try:
        # 初始化引擎
        logger.info("正在加载插件...")
        engine.initialize()

        # 验证依赖
        logger.info("正在验证工具依赖...")
        dependencies = engine.pm.hook.neosec_validate_dependencies()

        all_available = True
        for dep_dict in dependencies:
            if isinstance(dep_dict, dict):
                for tool, available in dep_dict.items():
                    status = "✓" if available else "✗"
                    logger.info(f"  {status} {tool}: {'可用' if available else '不可用'}")
                    if not available:
                        all_available = False

        if all_available:
            logger.info("所有依赖验证通过！")
            return 0
        else:
            logger.warning("部分依赖不可用，请安装缺失的工具")
            return 1

    except Exception as e:
        logger.error(f"验证失败: {e}")
        return 1


def main() -> int:
    """
    主函数 (Main Function)

    Returns:
        退出码
    """
    # 解析命令行参数
    args = parse_arguments()

    # 设置日志
    log_level = "DEBUG" if args.verbose else "INFO"
    logger = setup_logger(
        log_level=log_level,
        log_file=args.log_file,
        enable_color=True
    )

    # 显示欢迎信息
    logger.info("=" * 60)
    logger.info("NeoSec - 企业级自动化渗透测试框架")
    logger.info("=" * 60)

    # 根据子命令执行相应操作
    if args.command == "scan":
        return command_scan(args, logger)
    elif args.command == "list-tools":
        return command_list_tools(args, logger)
    elif args.command == "init-config":
        return command_init_config(args, logger)
    elif args.command == "validate":
        return command_validate(args, logger)
    else:
        logger.error("请指定一个命令（scan/list-tools/init-config/validate）")
        logger.info("使用 --help 查看帮助信息")
        return 1


if __name__ == "__main__":
    sys.exit(main())
