"""测试工作流执行引擎"""
import asyncio
import types

import pytest

from neobee.core.engine import WorkflowEngine


class DummyConfig:
    """最小配置桩，用于隔离引擎逻辑测试。"""

    def get(self, key, default=None):
        if key == "defaults":
            return {}
        if key == "defaults.timeout":
            return 300
        return default

    def get_tool_path(self, tool_name):
        return tool_name


@pytest.mark.asyncio
async def test_execute_replaces_variables_and_previous_results_dynamically():
    engine = WorkflowEngine(DummyConfig(), verbose=False, quiet=True, dry_run=False)

    async def fake_run_tool(self, step):
        if step["tool"] == "producer":
            return {"open_ports": [80, 443], "target": step["args"]["target"]}
        if step["tool"] == "consumer":
            return {"received": step["args"]}
        raise AssertionError(f"unexpected tool: {step['tool']}")

    engine._run_tool = types.MethodType(fake_run_tool, engine)

    template = {
        "name": "dynamic_vars",
        "version": "1.0.0",
        "variables": {"target": "example.com"},
        "steps": [
            {
                "id": "produce",
                "order": 1,
                "tool": "producer",
                "args": {"target": "{{target}}"},
                "save_result_as": "scan",
            },
            {
                "id": "consume",
                "order": 2,
                "tool": "consumer",
                "depends_on": ["produce"],
                "args": {"host": "{{target}}", "ports": "{{scan.open_ports}}"},
                "save_result_as": "consume_result",
            },
        ],
    }

    result = await engine.execute(template, {})

    assert result["summary"]["failed"] == 0
    assert result["summary"]["successful"] == 2
    assert engine.context["results"]["consume_result"]["received"]["host"] == "example.com"
    assert engine.context["results"]["consume_result"]["received"]["ports"] == [80, 443]


@pytest.mark.asyncio
async def test_execute_for_each_collects_item_results():
    engine = WorkflowEngine(DummyConfig(), verbose=False, quiet=True, dry_run=False)

    async def fake_run_tool(self, step):
        return {"port": step["args"]["port"]}

    engine._run_tool = types.MethodType(fake_run_tool, engine)

    template = {
        "name": "for_each",
        "version": "1.0.0",
        "variables": {"ports": [{"port": 80}, {"port": 443}]},
        "steps": [
            {
                "id": "scan_each",
                "order": 1,
                "tool": "scanner",
                "for_each": "{{ports}}",
                "args": {"port": "{{item.port}}"},
                "save_result_as": "scan_results",
            }
        ],
    }

    result = await engine.execute(template, {})

    assert result["summary"]["failed"] == 0
    assert result["summary"]["successful"] == 1
    assert engine.context["results"]["scan_results"] == [{"port": 80}, {"port": 443}]


@pytest.mark.asyncio
async def test_same_order_dependency_is_not_race_skipped():
    engine = WorkflowEngine(DummyConfig(), verbose=False, quiet=True, dry_run=False)

    async def fake_run_tool(self, step):
        if step["id"] == "prepare":
            await asyncio.sleep(0.05)
        return {"ok": True}

    engine._run_tool = types.MethodType(fake_run_tool, engine)

    template = {
        "name": "same_order_dependency",
        "version": "1.0.0",
        "steps": [
            {"id": "prepare", "order": 1, "tool": "prep", "args": {}},
            {
                "id": "use",
                "order": 1,
                "tool": "use",
                "depends_on": ["prepare"],
                "args": {},
            },
        ],
    }

    result = await engine.execute(template, {})

    assert result["summary"]["failed"] == 0
    assert result["summary"]["skipped"] == 0
    assert result["summary"]["successful"] == 2
