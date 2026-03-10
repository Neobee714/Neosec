"""Tests for config module."""
from pathlib import Path

from neobee.core.config import Config


def test_config_default_values():
    config = Config()
    assert config.neosec_dir == Path.home() / ".neosec"
    assert config.templates_dir == config.neosec_dir / "templates"
    assert config.log_dir == config.neosec_dir / "log"
    assert config.history_dir == config.neosec_dir / "history"


def test_config_merge():
    config = Config()
    default = {"a": 1, "b": {"c": 2, "d": 3}}
    user = {"b": {"c": 5}, "e": 6}

    result = config._merge_config(default, user)

    assert result["a"] == 1
    assert result["b"]["c"] == 5
    assert result["b"]["d"] == 3
    assert result["e"] == 6


def test_config_get_nested():
    config = Config()
    config.config_data = {"tools": {"nmap": "/usr/bin/nmap"}}

    assert config.get("tools.nmap") == "/usr/bin/nmap"
    assert config.get("tools.ffuf", "default") == "default"
    assert config.get("nonexistent", "default") == "default"


def test_get_tool_path():
    config = Config()
    config.config_data = {"tools": {"nmap": "/usr/bin/nmap"}}

    assert config.get_tool_path("nmap") == "/usr/bin/nmap"
    assert config.get_tool_path("ffuf") == "ffuf"
