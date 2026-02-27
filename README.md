# NeoSec - 企业级自动化渗透测试框架

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.9+-blue.svg)

## 项目简介

**NeoSec** 是一个基于 Python 的企业级自动化渗透测试框架，旨在将零散的开源安全工具（如 Nmap、Nuclei、Ffuf、SQLmap 等）整合为一个高度协同的自动化生态系统。

### 核心特性

- **插件化架构** - 基于 pluggy 的事件驱动插件系统，支持无限扩展
- **安全的进程管理** - 防止命令注入、死锁和僵尸进程
- **DAG 工作流编排** - 声明式 YAML 配置，支持任务依赖和并发执行
- **标准化数据模型** - 统一的资产和漏洞数据结构
- **企业级日志系统** - 彩色分级日志，支持文件和控制台双重输出

## 架构设计

```
NeoSec/
├── src/
│   ├── core/           # 核心引擎（插件系统、配置解析）
│   ├── execution/      # 进程调度和工作流编排
│   ├── models/         # 数据模型（资产、漏洞）
│   ├── adapters/       # 工具适配器（Nmap、Nuclei 等）
│   ├── plugins/        # 扩展插件（报告生成、通知等）
│   └── utils/          # 工具函数（日志、验证）
├── configs/            # 配置文件和工作流定义
├── data/               # 运行时数据和报告输出
└── tests/              # 单元测试和集成测试
```

## 快速开始

### 1. 安装依赖

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 安装外部安全工具（示例）
# Nmap
sudo apt-get install nmap  # Linux
brew install nmap          # macOS

# Nuclei
go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
```

### 2. 初始化配置

```bash
# 生成默认配置文件
python main.py init-config

# 验证依赖
python main.py validate
```

### 3. 列出可用工具

```bash
# 列出所有工具
python main.py list-tools

# 按分类过滤
python main.py list-tools --category recon
```

### 4. 执行扫描

```bash
# 使用默认工作流扫描目标
python main.py scan -t 192.168.1.1 -w configs/default_workflow.yaml

# 启用详细日志
python main.py scan -t example.com -w configs/default_workflow.yaml -v

# 保存日志到文件
python main.py scan -t 10.0.0.1 -w configs/default_workflow.yaml --log-file scan.log
```

## 工作流配置

工作流使用 YAML 格式定义，支持任务依赖和并发执行：

```yaml
name: "web_app_scan"
description: "Web 应用安全扫描"
global_timeout: 3600

tasks:
  - id: "port_scan"
    tool: "nmap"
    depends_on: []
    options:
      ports: "80,443,8080"
      service_detection: true

  - id: "nuclei_scan"
    tool: "nuclei"
    depends_on: ["port_scan"]
    options:
      templates: ["cves", "vulnerabilities"]
      severity: ["critical", "high"]
```

## 开发指南

### 添加新的工具适配器

1. 继承 `BaseAdapter` 基类
2. 实现必需的抽象方法
3. 使用 `@hookimpl` 装饰器注册钩子
4. 将适配器放置在 `src/adapters/` 目录下

示例：

```python
from src.adapters.base_adapter import BaseAdapter
from src.core.hookspecs import hookimpl

class MyToolAdapter(BaseAdapter):
    def get_tool_name(self) -> str:
        return "mytool"

    def get_tool_category(self) -> str:
        return "scanner"

    def get_required_binaries(self) -> list[str]:
        return ["mytool"]

    def build_command(self, target: str, options: dict) -> list[str]:
        return ["mytool", "-t", target]

    def parse_output(self, raw_output: str, output_format: str) -> dict:
        # 解析工具输出...
        return {"assets": [], "vulnerabilities": []}

# 创建全局实例
mytool_adapter = MyToolAdapter()
```

### 运行测试

```bash
# 运行所有测试
pytest tests/

# 运行特定测试
pytest tests/test_core/

# 生成覆盖率报告
pytest --cov=src tests/
```

## 架构原则

### 安全性

- **禁止 shell=True** - 所有命令以列表形式传递，防止命令注入
- **输入验证** - 严格的参数白名单校验
- **进程隔离** - 使用进程组管理，确保彻底清理

### 可扩展性

- **插件化设计** - 基于 pluggy 的钩子系统
- **松耦合架构** - 适配器之间完全独立
- **标准化接口** - 统一的数据模型和 API

### 可靠性

- **非阻塞 I/O** - 使用 asyncio 避免管道死锁
- **超时熔断** - 防止任务无限挂起
- **异常处理** - 精准的异常捕获和错误报告

## 技术栈

- **核心语言**: Python 3.9+
- **插件系统**: pluggy
- **数据验证**: pydantic
- **异步 I/O**: asyncio
- **配置解析**: PyYAML
- **日志系统**: colorlog
- **测试框架**: pytest

## 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 贡献指南

欢迎贡献代码、报告问题或提出建议！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 联系方式

- 项目主页: [GitHub Repository]
- 问题反馈: [Issues]
- 文档: [Wiki]

---

**免责声明**: 本工具仅用于授权的安全测试和教育目的。使用者需对其行为负责，开发者不承担任何滥用责任。
