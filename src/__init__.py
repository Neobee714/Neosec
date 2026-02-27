"""
NeoSec 框架 (NeoSec Framework)

企业级自动化渗透测试框架 - 基于 Python 的高延展性安全测试工具集成平台
"""

__version__ = "1.0.0"
__author__ = "NeoSec Team"
__description__ = "Enterprise-grade Automated Penetration Testing Framework"

from .core import get_engine, NeoSecEngine
from .models import Asset, Vulnerability, ScanResult
from .execution import ProcessRunner, WorkflowDAG
from .utils import get_logger, setup_logger

__all__ = [
    "get_engine",
    "NeoSecEngine",
    "Asset",
    "Vulnerability",
    "ScanResult",
    "ProcessRunner",
    "WorkflowDAG",
    "get_logger",
    "setup_logger",
]
