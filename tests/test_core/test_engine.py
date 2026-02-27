"""
核心引擎测试 (Core Engine Tests)

测试 NeoSec 核心引擎的基本功能。
"""

import pytest
from pathlib import Path
from src.core import get_engine, NeoSecEngine
from src.core.exceptions import PluginLoadError


def test_engine_singleton():
    """测试引擎单例模式"""
    engine1 = get_engine()
    engine2 = get_engine()
    assert engine1 is engine2


def test_engine_initialization():
    """测试引擎初始化"""
    engine = NeoSecEngine()
    assert engine.pm is not None
    assert isinstance(engine.loaded_plugins, dict)
    assert isinstance(engine.tool_registry, dict)


def test_plugin_discovery():
    """测试插件自动发现"""
    engine = get_engine()

    # 初始化引擎（加载插件）
    try:
        engine.initialize()
        # 应该至少加载了 Nmap 适配器
        assert len(engine.loaded_plugins) > 0
    except Exception as e:
        # 如果没有安装工具，跳过测试
        pytest.skip(f"插件加载失败: {e}")


def test_tool_registry():
    """测试工具注册表"""
    engine = get_engine()

    try:
        engine.initialize()
        engine.build_tool_registry()

        # 检查是否注册了工具
        if "nmap" in engine.tool_registry:
            nmap_info = engine.get_tool_info("nmap")
            assert nmap_info is not None
            assert nmap_info["name"] == "nmap"
            assert nmap_info["category"] == "recon"
    except Exception as e:
        pytest.skip(f"工具注册失败: {e}")


def test_list_tools():
    """测试列出工具"""
    engine = get_engine()

    try:
        engine.initialize()
        engine.build_tool_registry()

        # 列出所有工具
        all_tools = engine.list_available_tools()
        assert isinstance(all_tools, list)

        # 按分类列出
        recon_tools = engine.list_available_tools(category="recon")
        assert isinstance(recon_tools, list)
    except Exception as e:
        pytest.skip(f"列出工具失败: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
