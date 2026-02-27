"""
验证器模块 (Validators Module)

提供输入验证工具，防止命令注入和参数污染。
"""

import re
import ipaddress
from typing import Union
from urllib.parse import urlparse


class InputValidator:
    """
    输入验证器类 (Input Validator Class)

    提供各种输入数据的安全验证方法。
    """

    # 危险字符模式（用于防止命令注入）
    DANGEROUS_CHARS_PATTERN = re.compile(r'[;&|`$\n\r<>]')

    # IP 地址模式
    IP_PATTERN = re.compile(
        r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
        r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    )

    # 域名模式
    DOMAIN_PATTERN = re.compile(
        r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)*'
        r'[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$'
    )

    # 端口范围模式
    PORT_RANGE_PATTERN = re.compile(r'^(\d+)(-(\d+))?$')

    @staticmethod
    def is_valid_ip(ip: str) -> bool:
        """
        验证 IP 地址 (Validate IP Address)

        Args:
            ip: IP 地址字符串

        Returns:
            是否为有效的 IPv4 或 IPv6 地址
        """
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False

    @staticmethod
    def is_valid_ip_network(network: str) -> bool:
        """
        验证 IP 网络段 (Validate IP Network)

        Args:
            network: IP 网络段字符串（如 "192.168.1.0/24"）

        Returns:
            是否为有效的 IP 网络段
        """
        try:
            ipaddress.ip_network(network, strict=False)
            return True
        except ValueError:
            return False

    @staticmethod
    def is_valid_domain(domain: str) -> bool:
        """
        验证域名 (Validate Domain Name)

        Args:
            domain: 域名字符串

        Returns:
            是否为有效的域名
        """
        if len(domain) > 253:
            return False
        return bool(InputValidator.DOMAIN_PATTERN.match(domain))

    @staticmethod
    def is_valid_url(url: str) -> bool:
        """
        验证 URL (Validate URL)

        Args:
            url: URL 字符串

        Returns:
            是否为有效的 URL
        """
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    @staticmethod
    def is_valid_port(port: Union[int, str]) -> bool:
        """
        验证端口号 (Validate Port Number)

        Args:
            port: 端口号（整数或字符串）

        Returns:
            是否为有效的端口号（1-65535）
        """
        try:
            port_num = int(port)
            return 1 <= port_num <= 65535
        except (ValueError, TypeError):
            return False

    @staticmethod
    def is_valid_port_range(port_range: str) -> bool:
        """
        验证端口范围 (Validate Port Range)

        Args:
            port_range: 端口范围字符串（如 "80", "1-1000", "80,443,8080"）

        Returns:
            是否为有效的端口范围
        """
        # 处理逗号分隔的多个端口
        if ',' in port_range:
            ports = port_range.split(',')
            return all(InputValidator.is_valid_port_range(p.strip()) for p in ports)

        # 处理单个端口或范围
        match = InputValidator.PORT_RANGE_PATTERN.match(port_range)
        if not match:
            return False

        start_port = int(match.group(1))
        if not InputValidator.is_valid_port(start_port):
            return False

        # 如果是范围
        if match.group(3):
            end_port = int(match.group(3))
            if not InputValidator.is_valid_port(end_port):
                return False
            if start_port > end_port:
                return False

        return True

    @staticmethod
    def contains_dangerous_chars(text: str) -> bool:
        """
        检查是否包含危险字符 (Check for Dangerous Characters)

        用于防止命令注入攻击。

        Args:
            text: 待检查的文本

        Returns:
            是否包含危险字符
        """
        return bool(InputValidator.DANGEROUS_CHARS_PATTERN.search(text))

    @staticmethod
    def sanitize_string(text: str, allow_spaces: bool = True) -> str:
        """
        清理字符串 (Sanitize String)

        移除或转义危险字符。

        Args:
            text: 待清理的文本
            allow_spaces: 是否允许空格

        Returns:
            清理后的字符串
        """
        # 移除危险字符
        sanitized = InputValidator.DANGEROUS_CHARS_PATTERN.sub('', text)

        # 如果不允许空格，移除空格
        if not allow_spaces:
            sanitized = sanitized.replace(' ', '')

        return sanitized

    @staticmethod
    def validate_target(target: str) -> tuple[bool, str]:
        """
        验证扫描目标 (Validate Scan Target)

        综合验证目标是否为有效的 IP、IP 段、域名或 URL。

        Args:
            target: 扫描目标字符串

        Returns:
            (是否有效, 目标类型) 元组
            目标类型可能为: "ip", "network", "domain", "url", "invalid"
        """
        # 检查危险字符
        if InputValidator.contains_dangerous_chars(target):
            return False, "invalid"

        # 检查 IP 地址
        if InputValidator.is_valid_ip(target):
            return True, "ip"

        # 检查 IP 网络段
        if InputValidator.is_valid_ip_network(target):
            return True, "network"

        # 检查 URL
        if InputValidator.is_valid_url(target):
            return True, "url"

        # 检查域名
        if InputValidator.is_valid_domain(target):
            return True, "domain"

        return False, "invalid"

    @staticmethod
    def validate_command_arg(arg: str) -> bool:
        """
        验证命令行参数 (Validate Command Argument)

        确保参数不包含危险字符。

        Args:
            arg: 命令行参数

        Returns:
            是否为安全的参数
        """
        return not InputValidator.contains_dangerous_chars(arg)
