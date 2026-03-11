# Neosec

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Neosec 是一款面向渗透测试人员的工作流自动化 CLI 工具。通过 JSON 模板定义扫描流程，支持并行执行、条件执行、脚本插件扩展，并将结果整理到统一目录供后期分析。

## 特性

- **工作流自动化** — JSON 模板定义复杂渗透测试流程
- **并行执行** — 同一 order 的独立步骤自动并行，提升效率
- **条件执行** — 根据前置步骤结果（如开放端口）动态决策
- **脚本插件** — 支持 Python/Bash/Ruby/Node.js 等多语言脚本扩展工具
- **结构化输出** — 所有结果统一保存至 `~/.neosec/result/<ip>/`，原始 stdout 直接可读
- **内置解析器** — 自动解析 nmap XML、ffuf JSON，提取结构化数据
- **HTML 提取** — 内置 `html_extraction` 工具，去除噪声后保存页面源码供 AI 分析

## 安装

### 使用 pipx（推荐）

```bash
git clone https://github.com/Neobee714/neosec.git
cd neosec
pipx install .
pipx inject neosec beautifulsoup4 httpx
neosec init
```

### 使用 pip

```bash
git clone https://github.com/Neobee714/neosec.git
cd neosec
pip install -e .
neosec init
```

## 快速开始

### 初始化

```bash
neosec init
```

创建以下目录结构：

```
~/.neosec/
  config.yaml        # 配置文件
  templates/         # 用户模板目录
  scripts/           # 用户自定义脚本插件
  result/            # 扫描结果（按 IP 分目录）
  log/               # 日志
  history/           # 执行历史
```

### 执行工作流

```bash
# Nmap 端口扫描 + ffuf 目录爆破
neosec workflow -t nmap_ffuf_workflow.json -v target:192.168.1.1

# 追加 HTML 源码提取
neosec workflow -t html_extraction_workflow.json -v target:192.168.1.1

# 指定输出文件并生成 Markdown 报告
neosec workflow -t nmap_ffuf_workflow.json \
  -v target:192.168.1.1 \
  --output ./results/scan.json \
  --report
```

### 查看结果

```bash
ls ~/.neosec/result/192.168.1.1/
# port_scan.txt          nmap 原始输出（已过滤噪声）
# ffuf_port_80.txt       ffuf :80 原始输出
# ffuf_port_8080.txt     ffuf :8080 原始输出
# extract_html_80.txt    去噪后的 HTML 源码
# workflow_result.json   结构化结果数据
```

## 工作流模板

```json
{
  "name": "my_workflow",
  "version": "1.0.0",
  "variables": { "target": "" },
  "steps": [
    {
      "id": "port_scan",
      "order": 1,
      "tool": "nmap",
      "args": { "-sV": true, "-p": "1-10000", "target": "{{target}}" },
      "save_result_as": "port_scan_result",
      "timeout": 600
    },
    {
      "id": "ffuf_80",
      "order": 2,
      "depends_on": ["port_scan"],
      "when": { "type": "contains", "source": "port_scan_result.open_ports", "value": 80 },
      "tool": "ffuf",
      "args": { "-w": "/usr/share/wordlists/dirb/common.txt", "-u": "http://{{target}}/FUZZ" },
      "save_result_as": "ffuf_80_result"
    },
    {
      "id": "extract_html",
      "order": 3,
      "depends_on": ["ffuf_80"],
      "tool": "html_extraction",
      "args": {
        "source": "ffuf_80_result",
        "base_url": "http://{{target}}",
        "filter_status": "200,301"
      }
    }
  ]
}
```

## 脚本插件

在 `~/.neosec/scripts/` 放置脚本文件即可扩展新工具，优先级高于内置脚本：

```
~/.neosec/scripts/
  my_tool.py        # Python 脚本
  my_tool.sh        # Bash 脚本
  my_tool.js        # Node.js 脚本
```

脚本通过 stdin 接收 JSON 上下文，通过 stdout 返回 JSON 结果：

```python
import json, sys
payload = json.loads(sys.stdin.read())
args    = payload["args"]            # 工作流 step.args
results = payload["context"]["results"]  # 前置步骤结果
result_dir = payload["result_dir"]   # ~/.neosec/result/<ip>/

# ... 执行逻辑，将文件写入 result_dir ...

print(json.dumps({"status": "success", "pages": 3}))
```

支持的语言：`.py` `.sh` `.rb` `.js` `.pl` `.php` 及可执行文件（无扩展名）

## 内置模板

| 模板 | 说明 |
|---|---|
| `nmap_ffuf_workflow.json` | Nmap 端口扫描 + ffuf 目录爆破（80/443/8080/8000/8888） |
| `html_extraction_workflow.json` | 在 nmap_ffuf 基础上追加 HTML 源码提取 |

## 内置脚本插件

| 脚本 | 说明 |
|---|---|
| `html_extraction.py` | 批量抓取 URL，清理外联 CSS/图片/script 后保存纯净 HTML |

## 条件类型

| 类型 | 说明 |
|---|---|
| `contains` | 列表包含指定值 |
| `contains_any` | 列表包含任意一个值 |
| `not_contains_any` | 列表不包含任何指定值 |
| `equals` | 精确匹配 |
| `greater_than` | 大于 |
| `less_than` | 小于 |

## 命令参考

```bash
neosec workflow [OPTIONS]
  -t, --template TEXT     模板名称或文件路径
  -v, --variables TEXT    变量（格式: key:value，可多次指定）
  -o, --output TEXT       输出文件路径
  --report                生成 Markdown 报告
  --dry-run               干运行，不实际执行
  --verbose               详细输出
  --quiet                 静默模式

neosec history [OPTIONS]
  -n, --limit INTEGER     显示最近 N 条（默认 10）
  -w, --workflow TEXT     筛选工作流名称

neosec init               初始化配置和目录
neosec version            显示版本信息
```

## 配置文件

`~/.neosec/config.yaml`：

```yaml
tools:
  nmap: nmap
  ffuf: ffuf
  subfinder: subfinder
  nuclei: nuclei

defaults:
  wordlist: /usr/share/wordlists/dirb/common.txt
  timeout: 300
  retry: 1

output:
  default_path: ./
  default_filename: workflow_result.json
  log_path: ~/.neosec/log/
```

## 开发

```bash
poetry run pytest          # 运行测试
poetry run black src/      # 格式化
poetry run ruff check src/ # 检查
```

## 许可证

MIT — 详见 [LICENSE](LICENSE)
