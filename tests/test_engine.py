"""测试工作流执行引擎"""
import asyncio
import json
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


def test_parse_nmap_xml_extracts_open_ports_and_services():
    engine = WorkflowEngine(DummyConfig(), verbose=False, quiet=True, dry_run=False)

    xml_output = """<?xml version="1.0"?>
<nmaprun>
  <host>
    <address addr="192.168.110.101" addrtype="ipv4" />
    <ports>
      <port protocol="tcp" portid="22">
        <state state="open" />
        <service name="ssh" product="OpenSSH" version="8.4" />
      </port>
      <port protocol="tcp" portid="443">
        <state state="open" />
        <service name="https" />
      </port>
      <port protocol="tcp" portid="3306">
        <state state="closed" />
        <service name="mysql" />
      </port>
    </ports>
  </host>
</nmaprun>
"""

    parsed = engine._parse_nmap_xml(xml_output)

    assert parsed is not None
    assert parsed["open_ports"] == [22, 443]
    assert len(parsed["services"]) == 2
    assert parsed["services"][0]["service"] == "ssh"


def test_parse_nmap_text_extracts_open_ports_for_when_conditions():
    engine = WorkflowEngine(DummyConfig(), verbose=False, quiet=True, dry_run=False)

    text_output = """Starting Nmap 7.98
Nmap scan report for 192.168.110.101
PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 8.4p1
80/tcp   open  http
443/tcp  open  https?
8080/tcp open  http    Apache httpd 2.4.62
Nmap done: 1 IP address (1 host up) scanned in 18.20 seconds
"""

    parsed = engine._parse_nmap_text(text_output)

    assert parsed["open_ports"] == [22, 80, 443, 8080]
    assert len(parsed["services"]) == 4


def test_check_condition_can_use_open_ports_list():
    engine = WorkflowEngine(DummyConfig(), verbose=False, quiet=True, dry_run=False)
    engine.context["results"]["port_scan_result"] = {"open_ports": [22, 80, 443, 8080]}

    step = {
        "when": {
            "type": "contains",
            "source": "port_scan_result.open_ports",
            "value": 8080,
        }
    }

    assert engine._check_condition(step)


def test_summarize_ffuf_output_strips_control_sequences():
    engine = WorkflowEngine(DummyConfig(), verbose=False, quiet=True, dry_run=False)

    ffuf_output = "\x1b[2Kadmin [Status: 301, Size: 0, Words: 1, Lines: 1, Duration: 20ms]\x1b[0m\n"
    summary = engine._summarize_ffuf_output(ffuf_output)

    assert "Found entries:" in summary
    assert "admin" in summary
    assert "[2K" not in summary
    assert "[0m" not in summary

def test_parse_ffuf_result_generates_markdown_report(tmp_path):
    engine = WorkflowEngine(DummyConfig(), verbose=False, quiet=True, dry_run=False)

    ffuf_json = {
        "commandline": "ffuf -u http://example.com/FUZZ -o ffuf_80_result.json -of json",
        "time": "2026-03-10T11:50:53Z",
        "results": [
            {
                "input": {"FUZZ": "admin"},
                "status": 301,
                "length": 0,
                "words": 1,
                "lines": 1,
                "duration": 20000000,
                "url": "http://example.com/admin",
                "host": "example.com",
                "content-type": "text/html",
                "redirectlocation": "/admin/",
            }
        ],
    }

    json_path = tmp_path / "ffuf_80_result.json"
    json_path.write_text(json.dumps(ffuf_json), encoding="utf-8")

    result = engine._parse_ffuf_result("", {"-o": str(json_path), "-of": "json"})

    assert len(result["entries"]) == 1
    assert result["entries"][0]["path"] == "admin"

    md_path = tmp_path / "ffuf_80_result.md"
    assert md_path.exists()

    md = md_path.read_text(encoding="utf-8")
    assert "# FFUF 扫描结果" in md
    assert "| admin | 301 |" in md


def test_summarize_ffuf_entries_contains_markdown_path():
    engine = WorkflowEngine(DummyConfig(), verbose=False, quiet=True, dry_run=False)

    summary = engine._summarize_ffuf_entries(
        {
            "entries": [
                {"path": "admin", "status": 301, "length": 0, "duration_ms": 20.0, "redirectlocation": "/admin/"}
            ],
            "report_markdown": "ffuf_80_result.md",
        }
    )

    assert "Readable report: ffuf_80_result.md" in summary
    assert "- admin [status=301" in summary