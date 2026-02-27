# NeoSec 快速开始指南

## 环境要求

- Python 3.9 或更高版本
- Git
- 外部安全工具（可选，根据需要安装）

## 安装步骤

### 1. 克隆项目（如果从 Git 仓库）

```bash
git clone <repository-url>
cd NeoSec
```

### 2. 创建虚拟环境（推荐）

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 4. 验证安装

```bash
python main.py --help
```

应该看到类似输出：
```
usage: neosec [-h] [-c CONFIG] [-v] [--log-file LOG_FILE]
              {scan,list-tools,init-config,validate} ...

NeoSec - 企业级自动化渗透测试框架
```

## 基础使用

### 1. 验证依赖

检查系统中已安装的安全工具：

```bash
python main.py validate
```

输出示例：
```
[2026-02-27 10:00:00] [INFO    ] 正在加载插件...
[2026-02-27 10:00:01] [INFO    ] 正在验证工具依赖...
[2026-02-27 10:00:01] [INFO    ]   ✓ nmap: 可用
[2026-02-27 10:00:01] [INFO    ] 所有依赖验证通过！
```

### 2. 列出可用工具

```bash
# 列出所有工具
python main.py list-tools

# 按分类过滤
python main.py list-tools --category recon
```

### 3. 初始化配置文件

```bash
python main.py init-config -o configs/my_config.yaml
```

### 4. 执行扫描

```bash
# 基础扫描
python main.py scan -t 192.168.1.1 -w configs/default_workflow.yaml

# 启用详细日志
python main.py scan -t example.com -w configs/default_workflow.yaml -v

# 保存日志到文件
python main.py scan -t 10.0.0.1 -w configs/default_workflow.yaml --log-file scan.log
```

## 安装外部工具

### Nmap（网络扫描）

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install nmap

# CentOS/RHEL
sudo yum install nmap

# macOS
brew install nmap

# Windows
# 从 https://nmap.org/download.html 下载安装包
```

### Nuclei（漏洞扫描）

```bash
# 使用 Go 安装
go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest

# 或下载预编译二进制文件
# https://github.com/projectdiscovery/nuclei/releases
```

### Ffuf（Web 模糊测试）

```bash
# 使用 Go 安装
go install github.com/ffuf/ffuf/v2@latest

# 或下载预编译二进制文件
# https://github.com/ffuf/ffuf/releases
```

### SQLmap（SQL 注入测试）

```bash
# 使用 pip 安装
pip install sqlmap

# 或从 GitHub 克隆
git clone --depth 1 https://github.com/sqlmapproject/sqlmap.git
```

## 自定义工作流

### 创建工作流文件

在 `configs/` 目录下创建 `my_workflow.yaml`：

```yaml
name: "my_custom_scan"
description: "自定义扫描工作流"
global_timeout: 3600

tasks:
  # 第一步：端口扫描
  - id: "port_scan"
    tool: "nmap"
    depends_on: []
    target: null  # 从命令行继承
    options:
      scan_type: "syn"
      ports: "1-1000"
      service_detection: true
      timing: 4
      min_rate: 1000

  # 第二步：漏洞扫描（依赖端口扫描）
  - id: "vuln_scan"
    tool: "nuclei"
    depends_on: ["port_scan"]
    options:
      templates: ["cves", "vulnerabilities"]
      severity: ["critical", "high"]
```

### 执行自定义工作流

```bash
python main.py scan -t 192.168.1.1 -w configs/my_workflow.yaml -v
```

## 使用 Makefile（Linux/macOS）

项目提供了 Makefile 简化常用操作：

```bash
# 查看帮助
make help

# 安装依赖
make install

# 运行测试
make test

# 验证依赖
make validate

# 执行扫描
make run-scan TARGET=192.168.1.1

# 列出工具
make list-tools

# 清理临时文件
make clean
```

## 常见问题

### Q1: 提示 "依赖工具不可用"

**A**: 确保已安装相应的外部工具，并且工具在系统 PATH 中。可以使用以下命令检查：

```bash
# Linux/macOS
which nmap
which nuclei

# Windows
where nmap
where nuclei
```

### Q2: 如何指定工具的完整路径？

**A**: 编辑 `configs/neosec.yaml`，在 `tools` 部分指定 `binary_path`：

```yaml
tools:
  nmap:
    binary_path: "/usr/local/bin/nmap"  # 完整路径
```

### Q3: 扫描超时怎么办？

**A**: 在工作流配置中增加 `global_timeout` 或单个任务的超时时间：

```yaml
global_timeout: 7200  # 2 小时

tasks:
  - id: "slow_scan"
    tool: "nmap"
    options:
      timeout: 1800  # 30 分钟
```

### Q4: 如何查看详细的调试信息？

**A**: 使用 `-v` 参数启用 DEBUG 级别日志：

```bash
python main.py scan -t 192.168.1.1 -w configs/default_workflow.yaml -v
```

### Q5: 如何保存扫描结果？

**A**: 扫描结果会自动保存到 `data/reports/` 目录。可以通过 `-o` 参数指定输出目录：

```bash
python main.py scan -t 192.168.1.1 -w configs/default_workflow.yaml -o /path/to/output
```

## 开发模式

### 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试
pytest tests/test_core/test_engine.py -v

# 生成覆盖率报告
pytest tests/ --cov=src --cov-report=html
```

### 代码风格检查

```bash
# 使用 flake8
flake8 src/ --max-line-length=120

# 使用 mypy 进行类型检查
mypy src/ --ignore-missing-imports
```

## 下一步

- 阅读 [README.md](../README.md) 了解项目详情
- 查看 [DESIGN_SUMMARY.md](DESIGN_SUMMARY.md) 了解架构设计
- 查看 [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) 了解项目结构
- 参考 [research.md](../research.md) 了解技术细节

## 获取帮助

如果遇到问题：

1. 查看日志文件（如果使用了 `--log-file` 参数）
2. 使用 `-v` 参数启用详细日志
3. 运行 `python main.py validate` 检查依赖
4. 查看项目文档和示例配置

---

**安全提示**: 仅在授权的环境中使用本工具进行安全测试。未经授权的扫描可能违反法律。
