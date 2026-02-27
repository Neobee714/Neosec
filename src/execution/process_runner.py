"""
进程运行器模块 (Process Runner Module)

本模块实现安全、健壮的子进程管理机制，包括：
1. 防止命令注入 (Command Injection Prevention)
2. 非阻塞 I/O 处理 (Non-blocking I/O Handling)
3. 超时熔断机制 (Timeout Circuit Breaker)
4. 进程树彻底清理 (Process Tree Cleanup)
"""

import asyncio
import os
import signal
import subprocess
from typing import Optional, Callable
from pathlib import Path
from datetime import datetime

from ..core.exceptions import (
    ToolExecutionError,
    SubprocessTimeoutError,
    SubprocessDeadlockError
)


class ProcessResult:
    """
    进程执行结果模型 (Process Execution Result Model)

    封装子进程的执行结果数据。
    """

    def __init__(
        self,
        command: list[str],
        exit_code: int,
        stdout: str,
        stderr: str,
        execution_time: float,
        timed_out: bool = False
    ):
        self.command = command
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.execution_time = execution_time
        self.timed_out = timed_out

    @property
    def success(self) -> bool:
        """判断进程是否成功执行（退出码为 0）"""
        return self.exit_code == 0 and not self.timed_out

    def __repr__(self) -> str:
        return (
            f"ProcessResult(command={' '.join(self.command)}, "
            f"exit_code={self.exit_code}, "
            f"execution_time={self.execution_time:.2f}s, "
            f"timed_out={self.timed_out})"
        )


class ProcessRunner:
    """
    进程运行器类 (Process Runner Class)

    提供安全的子进程执行接口，防止常见的进程管理陷阱。
    """

    def __init__(
        self,
        tool_name: str,
        timeout: int = 300,
        output_callback: Optional[Callable[[str], None]] = None
    ):
        """
        初始化进程运行器

        Args:
            tool_name: 工具名称（用于日志和错误报告）
            timeout: 超时时间（秒），默认 300 秒
            output_callback: 可选的实时输出回调函数
        """
        self.tool_name = tool_name
        self.timeout = timeout
        self.output_callback = output_callback

    def validate_command(self, command: list[str]) -> None:
        """
        验证命令参数 (Validate Command Arguments)

        确保命令以列表形式传入，防止命令注入。

        Args:
            command: 命令参数列表

        Raises:
            ValueError: 命令格式不合法
        """
        if not isinstance(command, list):
            raise ValueError(
                f"命令必须以列表形式传入，当前类型: {type(command)}"
            )

        if len(command) == 0:
            raise ValueError("命令列表不能为空")

        # 检查命令中是否包含危险字符（基础检查）
        dangerous_chars = [";", "|", "&", "$", "`", "\n", "\r"]
        for arg in command:
            for char in dangerous_chars:
                if char in str(arg):
                    raise ValueError(
                        f"命令参数包含危险字符 '{char}': {arg}"
                    )

    async def run_async(
        self,
        command: list[str],
        cwd: Optional[Path] = None,
        env: Optional[dict] = None
    ) -> ProcessResult:
        """
        异步执行子进程 (Execute Subprocess Asynchronously)

        使用 asyncio 实现非阻塞的进程执行和输出捕获。

        Args:
            command: 命令参数列表
            cwd: 工作目录（可选）
            env: 环境变量字典（可选）

        Returns:
            ProcessResult 实例

        Raises:
            SubprocessTimeoutError: 进程超时
            ToolExecutionError: 进程执行失败
        """
        # 验证命令
        self.validate_command(command)

        start_time = datetime.now()
        stdout_data = []
        stderr_data = []

        try:
            # 创建子进程（使用 asyncio.create_subprocess_exec 避免 shell=True）
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env,
                # 在 Unix 系统上创建新的进程组
                preexec_fn=os.setsid if os.name != 'nt' else None
            )

            # 异步读取 stdout 和 stderr
            async def read_stream(stream, data_list, is_stderr=False):
                """异步读取流数据"""
                while True:
                    line = await stream.readline()
                    if not line:
                        break

                    decoded_line = line.decode('utf-8', errors='replace').rstrip()
                    data_list.append(decoded_line)

                    # 调用实时输出回调
                    if self.output_callback and not is_stderr:
                        self.output_callback(decoded_line)

            # 并发读取两个流
            try:
                await asyncio.wait_for(
                    asyncio.gather(
                        read_stream(process.stdout, stdout_data),
                        read_stream(process.stderr, stderr_data, is_stderr=True),
                        process.wait()
                    ),
                    timeout=self.timeout
                )
                timed_out = False

            except asyncio.TimeoutError:
                # 超时处理：杀死整个进程树
                await self._kill_process_tree(process)
                timed_out = True

            # 计算执行时间
            execution_time = (datetime.now() - start_time).total_seconds()

            # 构建结果
            result = ProcessResult(
                command=command,
                exit_code=process.returncode or -1,
                stdout="\n".join(stdout_data),
                stderr="\n".join(stderr_data),
                execution_time=execution_time,
                timed_out=timed_out
            )

            # 如果超时，抛出异常
            if timed_out:
                raise SubprocessTimeoutError(
                    tool_name=self.tool_name,
                    timeout_seconds=self.timeout
                )

            # 如果退出码非零，抛出异常
            if result.exit_code != 0:
                raise ToolExecutionError(
                    tool_name=self.tool_name,
                    command=command,
                    exit_code=result.exit_code,
                    stderr=result.stderr
                )

            return result

        except (SubprocessTimeoutError, ToolExecutionError):
            raise
        except Exception as e:
            raise ToolExecutionError(
                tool_name=self.tool_name,
                command=command,
                exit_code=-1,
                stderr=str(e)
            )

    async def _kill_process_tree(self, process: asyncio.subprocess.Process) -> None:
        """
        杀死整个进程树 (Kill Entire Process Tree)

        确保子进程及其所有衍生进程都被终止。

        Args:
            process: asyncio 子进程对象
        """
        if process.returncode is not None:
            return  # 进程已经结束

        try:
            if os.name == 'nt':
                # Windows: 使用 taskkill 杀死进程树
                subprocess.run(
                    ['taskkill', '/F', '/T', '/PID', str(process.pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            else:
                # Unix: 向进程组发送 SIGTERM，然后 SIGKILL
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    await asyncio.sleep(2)  # 等待优雅退出
                    if process.returncode is None:
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass  # 进程已经不存在

        except Exception:
            # 最后的手段：直接杀死主进程
            try:
                process.kill()
            except ProcessLookupError:
                pass

    def run_sync(
        self,
        command: list[str],
        cwd: Optional[Path] = None,
        env: Optional[dict] = None
    ) -> ProcessResult:
        """
        同步执行子进程 (Execute Subprocess Synchronously)

        提供同步接口，内部使用 asyncio.run() 执行异步方法。

        Args:
            command: 命令参数列表
            cwd: 工作目录（可选）
            env: 环境变量字典（可选）

        Returns:
            ProcessResult 实例
        """
        return asyncio.run(self.run_async(command, cwd, env))


class ProcessPool:
    """
    进程池管理器 (Process Pool Manager)

    管理多个并发进程的执行，限制最大并发数。
    """

    def __init__(self, max_concurrent: int = 5):
        """
        初始化进程池

        Args:
            max_concurrent: 最大并发进程数
        """
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.running_tasks: list[asyncio.Task] = []

    async def submit(
        self,
        runner: ProcessRunner,
        command: list[str],
        cwd: Optional[Path] = None,
        env: Optional[dict] = None
    ) -> ProcessResult:
        """
        提交任务到进程池 (Submit Task to Process Pool)

        Args:
            runner: ProcessRunner 实例
            command: 命令参数列表
            cwd: 工作目录
            env: 环境变量

        Returns:
            ProcessResult 实例
        """
        async with self.semaphore:
            return await runner.run_async(command, cwd, env)

    async def run_batch(
        self,
        tasks: list[tuple[ProcessRunner, list[str], Optional[Path], Optional[dict]]]
    ) -> list[ProcessResult]:
        """
        批量执行任务 (Execute Batch Tasks)

        Args:
            tasks: 任务列表，每个任务为 (runner, command, cwd, env) 元组

        Returns:
            ProcessResult 列表
        """
        coroutines = [
            self.submit(runner, cmd, cwd, env)
            for runner, cmd, cwd, env in tasks
        ]

        results = await asyncio.gather(*coroutines, return_exceptions=True)
        return results
