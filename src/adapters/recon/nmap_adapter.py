"""
Nmap 适配器 (Nmap Adapter)

Network Mapper (网络映射器) 工具的适配器实现。
负责构建 Nmap 命令、解析 XML 输出并转换为标准化的资产模型。
"""

from typing import Any
import xml.etree.ElementTree as ET
from pathlib import Path

from ..base_adapter import BaseAdapter
from ...models import Asset, AssetType, Host, Port, ServiceProtocol
from ...core.exceptions import DataParsingError


class NmapAdapter(BaseAdapter):
    """
    Nmap 工具适配器 (Nmap Tool Adapter)

    实现 Nmap 的命令构建和 XML 输出解析。
    """

    def get_tool_name(self) -> str:
        """返回工具名称"""
        return "nmap"

    def get_tool_category(self) -> str:
        """返回工具分类"""
        return "recon"

    def get_required_binaries(self) -> list[str]:
        """返回依赖的二进制文件"""
        return ["nmap"]

    def build_command(
        self,
        target: str,
        options: dict[str, Any]
    ) -> list[str]:
        """
        构建 Nmap 命令 (Build Nmap Command)

        Args:
            target: 扫描目标（IP 或 IP 段）
            options: 选项字典，支持以下参数：
                - scan_type: 扫描类型（"syn", "tcp", "udp"），默认 "syn"
                - ports: 端口范围（如 "1-1000"），默认 "1-65535"
                - service_detection: 是否启用服务检测，默认 True
                - os_detection: 是否启用操作系统检测，默认 False
                - timing: 时间模板（0-5），默认 4
                - min_rate: 最小发包速率，默认 1000
                - output_file: 输出文件路径（可选）

        Returns:
            Nmap 命令参数列表
        """
        cmd = [self.binary_path or "nmap"]

        # 扫描类型
        scan_type = options.get("scan_type", "syn")
        if scan_type == "syn":
            cmd.append("-sS")  # SYN 扫描
        elif scan_type == "tcp":
            cmd.append("-sT")  # TCP 连接扫描
        elif scan_type == "udp":
            cmd.append("-sU")  # UDP 扫描

        # 端口范围
        ports = options.get("ports", "1-65535")
        cmd.extend(["-p", ports])

        # 服务版本检测
        if options.get("service_detection", True):
            cmd.append("-sV")

        # 操作系统检测
        if options.get("os_detection", False):
            cmd.append("-O")

        # 时间模板（加速扫描）
        timing = options.get("timing", 4)
        cmd.append(f"-T{timing}")

        # 最小发包速率
        min_rate = options.get("min_rate", 1000)
        cmd.extend(["--min-rate", str(min_rate)])

        # 禁用 DNS 解析（加速）
        if options.get("no_dns", True):
            cmd.append("-n")

        # 输出格式：强制 XML
        output_file = options.get("output_file")
        if output_file:
            cmd.extend(["-oX", output_file])
        else:
            # 如果没有指定输出文件，使用 -oX - 输出到 stdout
            cmd.extend(["-oX", "-"])

        # 添加目标
        cmd.append(target)

        return cmd

    def parse_output(
        self,
        raw_output: str,
        output_format: str
    ) -> dict[str, Any]:
        """
        解析 Nmap XML 输出 (Parse Nmap XML Output)

        Args:
            raw_output: XML 字符串或文件路径
            output_format: 输出格式（必须为 "xml"）

        Returns:
            包含 assets 列表的字典

        Raises:
            DataParsingError: XML 解析失败
        """
        if output_format != "xml":
            raise DataParsingError(
                tool_name=self.tool_name,
                data_format=output_format,
                reason="Nmap 适配器仅支持 XML 格式"
            )

        try:
            # 判断是文件路径还是 XML 字符串
            if Path(raw_output).exists():
                tree = ET.parse(raw_output)
                root = tree.getroot()
            else:
                root = ET.fromstring(raw_output)

            assets = []

            # 遍历所有主机
            for host_elem in root.findall("host"):
                # 检查主机状态
                status = host_elem.find("status")
                if status is None or status.get("state") != "up":
                    continue

                # 提取 IP 地址
                address_elem = host_elem.find("address[@addrtype='ipv4']")
                if address_elem is None:
                    continue
                ip_address = address_elem.get("addr")

                # 提取主机名
                hostname = None
                hostnames_elem = host_elem.find("hostnames/hostname")
                if hostnames_elem is not None:
                    hostname = hostnames_elem.get("name")

                # 提取 MAC 地址
                mac_address = None
                mac_elem = host_elem.find("address[@addrtype='mac']")
                if mac_elem is not None:
                    mac_address = mac_elem.get("addr")

                # 提取操作系统信息
                os_name = None
                os_version = None
                os_accuracy = None
                os_elem = host_elem.find("os/osmatch")
                if os_elem is not None:
                    os_name = os_elem.get("name")
                    os_accuracy = int(os_elem.get("accuracy", 0))

                # 提取端口信息
                ports = []
                for port_elem in host_elem.findall("ports/port"):
                    port_state = port_elem.find("state")
                    if port_state is None or port_state.get("state") != "open":
                        continue

                    port_number = int(port_elem.get("portid"))
                    protocol = port_elem.get("protocol", "tcp")

                    # 提取服务信息
                    service_elem = port_elem.find("service")
                    service_name = None
                    service_version = None
                    service_product = None
                    banner = None

                    if service_elem is not None:
                        service_name = service_elem.get("name")
                        service_product = service_elem.get("product")
                        service_version = service_elem.get("version")
                        # 构建 banner
                        if service_product:
                            banner = service_product
                            if service_version:
                                banner += f" {service_version}"

                    # 创建 Port 对象
                    port = Port(
                        port_number=port_number,
                        protocol=ServiceProtocol.TCP if protocol == "tcp" else ServiceProtocol.UDP,
                        state="open",
                        service_name=service_name,
                        service_version=service_version,
                        service_product=service_product,
                        banner=banner
                    )
                    ports.append(port)

                # 创建 Host 对象
                host = Host(
                    ip_address=ip_address,
                    hostname=hostname,
                    mac_address=mac_address,
                    os_name=os_name,
                    os_version=os_version,
                    os_accuracy=os_accuracy,
                    ports=ports,
                    status="up"
                )

                # 创建 Asset 对象
                asset = Asset(
                    asset_id=f"host_{ip_address}",
                    asset_type=AssetType.HOST,
                    target=ip_address,
                    source_tool=self.tool_name,
                    host_data=host
                )
                assets.append(asset)

            return {
                "assets": assets,
                "vulnerabilities": []  # Nmap 不直接报告漏洞
            }

        except ET.ParseError as e:
            raise DataParsingError(
                tool_name=self.tool_name,
                data_format="xml",
                reason=f"XML 解析错误: {str(e)}"
            )
        except Exception as e:
            raise DataParsingError(
                tool_name=self.tool_name,
                data_format="xml",
                reason=f"数据处理错误: {str(e)}"
            )


# 创建全局实例以便 pluggy 自动发现
nmap_adapter = NmapAdapter()
