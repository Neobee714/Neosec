"""
工具适配器基类 (Tool Adapter Base Class)

定义所有外部工具适配器的抽象基类，规范适配器的标准接口。
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
from pathlib import Path
import shutil

from ..core.hookspecs import hookimpl
from ..models import Asset, Vulnerability


class BaseAdapter(ABC):
    """
    工具适配器抽象基类 (Abstract Base Adapter Class)

    所有工具适配器必须继承此类并实现其抽象方法。
    """

    def __init__(self):
        """初始化适配器"""
        self.tool_name: str = self.get_tool_name()
        self.binary_path: Optional[str] = None
        self._validate_binary()

    @abstractmethod
    def get_tool_name(self) -> str:
        """
        获取工具名称 (Get Tool Name)

        Returns:
            工具名称字符串
        """
        pass

    @abstractmethod
    def get_tool_category(self) -> str:
        """
        获取工具分类 (Get Tool Category)

        Returns:
            工具分类（"recon", "scanner", "fuzzer"）
        """
        pass

    @abstractmethod
    def get_required_binaries(self) -> list[str]:
        """
        获取依赖的二进制文件列表 (Get Required Binaries)

        Returns:
            二进制文件名列表
        """
        pass

    @abstractmethod
    def build_command(
        self,
        target: str,
        options: dict[str, Any]
    ) -> list[str]:
        """
        构建命令行参数 (Build Command Line Arguments)

        Args:
            target: 扫描目标
            options: 工具特定选项

        Returns:
            命令参数列表
        """
        pass

    @abstractmethod
    def parse_output(
        self,
        raw_output: str,
        output_format: str
    ) -> dict[str, Any]:
        """
        解析工具输出 (Parse Tool Output)

        Args:
            raw_output: 原始输出字符串或文件路径
            output_format: 输出格式（"json", "xml", "text"）

        Returns:
            包含 assets 和 vulnerabilities 的字典
        """
        pass

    def _validate_binary(self) -> None:
        """
        验证二进制文件是否存在 (Validate Binary Existence)

        检查工具的二进制文件是否在系统 PATH 中。
        """
        required_binaries = self.get_required_binaries()
        for binary in required_binaries:
            path = shutil.which(binary)
            if path:
                self.binary_path = path
                break

    def is_available(self) -> bool:
        """
        检查工具是否可用 (Check Tool Availability)

        Returns:
            工具是否可用
        """
        return self.binary_path is not None

    # ========== Pluggy Hook 实现 ==========

    @hookimpl
    def neosec_register_tool(self) -> dict[str, Any]:
        """
        注册工具元数据 (Register Tool Metadata)

        实现 pluggy 钩子，向框架注册工具信息。
        """
        return {
            "name": self.get_tool_name(),
            "category": self.get_tool_category(),
            "version": "1.0.0",
            "description": f"{self.get_tool_name()} adapter",
            "required_binaries": self.get_required_binaries()
        }

    @hookimpl
    def neosec_validate_dependencies(self) -> dict[str, bool]:
        """
        验证依赖 (Validate Dependencies)

        实现 pluggy 钩子，检查工具是否可用。
        """
        return {self.get_tool_name(): self.is_available()}

    @hookimpl
    def neosec_build_command(
        self,
        tool_name: str,
        target: str,
        options: dict[str, Any]
    ) -> Optional[list[str]]:
        """
        构建命令 (Build Command)

        实现 pluggy 钩子，只处理匹配的工具。
        """
        if tool_name != self.get_tool_name():
            return None

        return self.build_command(target, options)

    @hookimpl
    def neosec_parse_output(
        self,
        tool_name: str,
        raw_output: str,
        output_format: str
    ) -> Optional[dict[str, Any]]:
        """
        解析输出 (Parse Output)

        实现 pluggy 钩子，只处理匹配的工具。
        """
        if tool_name != self.get_tool_name():
            return None

        return self.parse_output(raw_output, output_format)
