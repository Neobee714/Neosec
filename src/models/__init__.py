"""
数据模型模块 (Data Models Module)

NeoSec 框架的核心数据结构定义，包括资产和漏洞模型。
"""

from .asset import (
    Asset,
    AssetType,
    Host,
    Port,
    ServiceProtocol,
    WebApplication,
    Subdomain
)

from .vulnerability import (
    Vulnerability,
    SeverityLevel,
    VulnerabilityCategory,
    CVSSScore,
    Reference,
    ScanResult
)

__all__ = [
    # 资产模型
    "Asset",
    "AssetType",
    "Host",
    "Port",
    "ServiceProtocol",
    "WebApplication",
    "Subdomain",
    # 漏洞模型
    "Vulnerability",
    "SeverityLevel",
    "VulnerabilityCategory",
    "CVSSScore",
    "Reference",
    "ScanResult",
]
