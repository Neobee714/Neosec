"""
资产数据模型 (Asset Data Model)

定义网络资产的标准化数据结构，用于统一表示扫描发现的主机、端口、服务等信息。
"""

from typing import Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class AssetType(str, Enum):
    """资产类型枚举 (Asset Type Enumeration)"""
    HOST = "host"  # 主机
    PORT = "port"  # 端口
    SERVICE = "service"  # 服务
    WEB_APP = "web_app"  # Web 应用
    SUBDOMAIN = "subdomain"  # 子域名
    URL = "url"  # URL 地址


class ServiceProtocol(str, Enum):
    """服务协议枚举 (Service Protocol Enumeration)"""
    TCP = "tcp"
    UDP = "udp"
    SCTP = "sctp"


class Port(BaseModel):
    """
    端口模型 (Port Model)

    表示主机上的单个开放端口及其服务信息。
    """
    port_number: int = Field(..., description="端口号", ge=1, le=65535)
    protocol: ServiceProtocol = Field(ServiceProtocol.TCP, description="传输协议")
    state: str = Field("open", description="端口状态（open/closed/filtered）")
    service_name: Optional[str] = Field(None, description="服务名称（如 http, ssh）")
    service_version: Optional[str] = Field(None, description="服务版本")
    service_product: Optional[str] = Field(None, description="服务产品名称")
    banner: Optional[str] = Field(None, description="服务 Banner 信息")

    @field_validator('state')
    @classmethod
    def validate_state(cls, v: str) -> str:
        """验证端口状态"""
        valid_states = ["open", "closed", "filtered", "unfiltered", "open|filtered", "closed|filtered"]
        if v not in valid_states:
            raise ValueError(f"无效的端口状态: {v}")
        return v


class Host(BaseModel):
    """
    主机模型 (Host Model)

    表示网络中的单个主机资产。
    """
    ip_address: str = Field(..., description="IP 地址")
    hostname: Optional[str] = Field(None, description="主机名")
    mac_address: Optional[str] = Field(None, description="MAC 地址")
    os_name: Optional[str] = Field(None, description="操作系统名称")
    os_version: Optional[str] = Field(None, description="操作系统版本")
    os_accuracy: Optional[int] = Field(None, description="操作系统识别准确度（0-100）")
    ports: list[Port] = Field(default_factory=list, description="开放端口列表")
    status: str = Field("up", description="主机状态（up/down）")
    discovered_at: datetime = Field(default_factory=datetime.now, description="发现时间")

    @field_validator('ip_address')
    @classmethod
    def validate_ip(cls, v: str) -> str:
        """验证 IP 地址格式（简单验证）"""
        parts = v.split('.')
        if len(parts) != 4:
            raise ValueError(f"无效的 IP 地址格式: {v}")
        for part in parts:
            if not part.isdigit() or not 0 <= int(part) <= 255:
                raise ValueError(f"无效的 IP 地址: {v}")
        return v


class WebApplication(BaseModel):
    """
    Web 应用模型 (Web Application Model)

    表示 Web 应用及其技术栈信息。
    """
    url: str = Field(..., description="应用 URL")
    title: Optional[str] = Field(None, description="页面标题")
    status_code: Optional[int] = Field(None, description="HTTP 状态码")
    server: Optional[str] = Field(None, description="Web 服务器类型")
    technologies: list[str] = Field(default_factory=list, description="检测到的技术栈")
    cms: Optional[str] = Field(None, description="内容管理系统（CMS）")
    cms_version: Optional[str] = Field(None, description="CMS 版本")
    frameworks: list[str] = Field(default_factory=list, description="Web 框架")
    javascript_libraries: list[str] = Field(default_factory=list, description="JavaScript 库")
    headers: dict[str, str] = Field(default_factory=dict, description="HTTP 响应头")
    cookies: list[str] = Field(default_factory=list, description="Cookie 列表")


class Subdomain(BaseModel):
    """
    子域名模型 (Subdomain Model)

    表示发现的子域名资产。
    """
    domain: str = Field(..., description="子域名")
    ip_addresses: list[str] = Field(default_factory=list, description="解析的 IP 地址列表")
    cname: Optional[str] = Field(None, description="CNAME 记录")
    source: Optional[str] = Field(None, description="发现来源（如 subfinder, amass）")
    discovered_at: datetime = Field(default_factory=datetime.now, description="发现时间")


class Asset(BaseModel):
    """
    通用资产模型 (Generic Asset Model)

    统一的资产容器，可以包含不同类型的资产数据。
    """
    asset_id: str = Field(..., description="资产唯一标识符")
    asset_type: AssetType = Field(..., description="资产类型")
    target: str = Field(..., description="扫描目标（IP/域名/URL）")
    source_tool: str = Field(..., description="发现该资产的工具名称")

    # 类型特定数据（根据 asset_type 选择使用）
    host_data: Optional[Host] = Field(None, description="主机数据")
    web_app_data: Optional[WebApplication] = Field(None, description="Web 应用数据")
    subdomain_data: Optional[Subdomain] = Field(None, description="子域名数据")

    # 元数据
    metadata: dict[str, any] = Field(default_factory=dict, description="额外元数据")
    discovered_at: datetime = Field(default_factory=datetime.now, description="发现时间")
    last_updated: datetime = Field(default_factory=datetime.now, description="最后更新时间")

    def update_timestamp(self) -> None:
        """更新最后修改时间戳"""
        self.last_updated = datetime.now()
