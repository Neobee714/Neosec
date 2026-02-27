"""
数据模型测试 (Data Models Tests)

测试资产和漏洞数据模型。
"""

import pytest
from datetime import datetime
from src.models import (
    Asset, AssetType, Host, Port, ServiceProtocol,
    Vulnerability, SeverityLevel, VulnerabilityCategory, CVSSScore
)


def test_port_model():
    """测试端口模型"""
    port = Port(
        port_number=80,
        protocol=ServiceProtocol.TCP,
        state="open",
        service_name="http",
        service_version="Apache 2.4"
    )

    assert port.port_number == 80
    assert port.protocol == ServiceProtocol.TCP
    assert port.state == "open"


def test_host_model():
    """测试主机模型"""
    port = Port(port_number=22, protocol=ServiceProtocol.TCP, state="open")

    host = Host(
        ip_address="192.168.1.1",
        hostname="example.local",
        ports=[port],
        status="up"
    )

    assert host.ip_address == "192.168.1.1"
    assert host.hostname == "example.local"
    assert len(host.ports) == 1
    assert host.status == "up"


def test_asset_model():
    """测试资产模型"""
    host = Host(ip_address="10.0.0.1", status="up")

    asset = Asset(
        asset_id="host_10.0.0.1",
        asset_type=AssetType.HOST,
        target="10.0.0.1",
        source_tool="nmap",
        host_data=host
    )

    assert asset.asset_id == "host_10.0.0.1"
    assert asset.asset_type == AssetType.HOST
    assert asset.source_tool == "nmap"
    assert asset.host_data is not None


def test_cvss_score():
    """测试 CVSS 评分模型"""
    cvss = CVSSScore(
        version="3.1",
        base_score=9.8,
        vector_string="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
    )

    assert cvss.version == "3.1"
    assert cvss.base_score == 9.8


def test_vulnerability_model():
    """测试漏洞模型"""
    cvss = CVSSScore(version="3.1", base_score=7.5)

    vuln = Vulnerability(
        vuln_id="vuln_001",
        title="SQL Injection",
        description="SQL injection vulnerability in login form",
        severity=SeverityLevel.HIGH,
        category=VulnerabilityCategory.SQL_INJECTION,
        cvss=cvss,
        target="https://example.com",
        cve_id="CVE-2024-1234",
        source_tool="sqlmap"
    )

    assert vuln.vuln_id == "vuln_001"
    assert vuln.severity == SeverityLevel.HIGH
    assert vuln.category == VulnerabilityCategory.SQL_INJECTION
    assert vuln.cve_id == "CVE-2024-1234"
    assert not vuln.verified

    # 测试标记为已验证
    vuln.mark_as_verified()
    assert vuln.verified
    assert vuln.last_verified is not None


def test_invalid_cve_format():
    """测试无效的 CVE 格式"""
    with pytest.raises(ValueError):
        Vulnerability(
            vuln_id="vuln_002",
            title="Test",
            description="Test",
            severity=SeverityLevel.LOW,
            category=VulnerabilityCategory.OTHER,
            target="test",
            cve_id="INVALID-2024-1234",  # 无效格式
            source_tool="test"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
