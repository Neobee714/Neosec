"""
进程运行器测试 (Process Runner Tests)

测试进程管理和命令执行功能。
"""

import pytest
from src.execution import ProcessRunner
from src.core.exceptions import ToolExecutionError, SubprocessTimeoutError


def test_process_runner_initialization():
    """测试进程运行器初始化"""
    runner = ProcessRunner(tool_name="test_tool", timeout=60)
    assert runner.tool_name == "test_tool"
    assert runner.timeout == 60


def test_command_validation():
    """测试命令验证"""
    runner = ProcessRunner(tool_name="test")

    # 有效命令
    runner.validate_command(["echo", "hello"])

    # 无效命令（非列表）
    with pytest.raises(ValueError):
        runner.validate_command("echo hello")

    # 空命令
    with pytest.raises(ValueError):
        runner.validate_command([])

    # 包含危险字符
    with pytest.raises(ValueError):
        runner.validate_command(["echo", "hello; rm -rf /"])


def test_simple_command_execution():
    """测试简单命令执行"""
    runner = ProcessRunner(tool_name="echo", timeout=10)

    # 执行 echo 命令
    result = runner.run_sync(["echo", "hello world"])

    assert result.success
    assert result.exit_code == 0
    assert "hello world" in result.stdout


def test_command_timeout():
    """测试命令超时"""
    runner = ProcessRunner(tool_name="sleep", timeout=2)

    # 执行会超时的命令
    with pytest.raises(SubprocessTimeoutError):
        runner.run_sync(["sleep", "10"])


def test_command_failure():
    """测试命令执行失败"""
    runner = ProcessRunner(tool_name="false", timeout=10)

    # 执行会失败的命令
    with pytest.raises(ToolExecutionError):
        runner.run_sync(["false"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
