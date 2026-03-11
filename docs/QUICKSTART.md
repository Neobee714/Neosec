# 快速开始指南

## 安装

### 前置要求

- Python 3.10+
- Kali Linux / Debian / Ubuntu（推荐）
- nmap、ffuf 已安装

### 使用 pipx（推荐）

```bash
git clone https://github.com/Neobee714/neosec.git
cd neosec
pipx install .
pipx inject neosec beautifulsoup4 httpx  # html_extraction 依赖
neosec init
```

### 使用 pip

```bash
git clone https://github.com/Neobee714/neosec.git
cd neosec
pip install -e .
neosec init
```

## 初始化

```bash
neosec init
```

创建以下目录结构：

```
~/.neosec/
  config.yaml        # 工具路径、默认参数配置
  templates/         # 用户模板目录
  scripts/           # 用户自定义脚本插件
  result/            # 扫描结果（按目标 IP 分目录）
  log/               # 日志
  history/           # 执行历史
```

## 第一个扫描

### 端口扫描 + 目录爆破

```bash
neosec workflow \
  -t ~/.neosec/templates/nmap_ffuf_workflow.json \
  -v target:192.168.1.1
```

执行完成后查看结果：

```bash
ls ~/.neosec/result/192.168.1.1/
# port_scan.txt        nmap 原始输出
# ffuf_port_80.txt     ffuf :80 扫描结果
# ffuf_port_8080.txt   ffuf :8080 扫描结果
# workflow_result.json 结构化数据

cat ~/.neosec/result/192.168.1.1/port_scan.txt
cat ~/.neosec/result/192.168.1.1/ffuf_port_80.txt
```

### 追加 HTML 源码提取

```bash
neosec workflow \
  -t ~/.neosec/templates/html_extraction_workflow.json \
  -v target:192.168.1.1

# 查看去噪后的 HTML，可直接粘贴给 AI 分析
cat ~/.neosec/result/192.168.1.1/extract_html_80.txt
```

### 生成 Markdown 报告

```bash
neosec workflow \
  -t ~/.neosec/templates/nmap_ffuf_workflow.json \
  -v target:192.168.1.1 \
  --output ./scan_result.json \
  --report

cat ./scan_result.md
```

## 常用命令

```bash
# 详细输出（显示每步命令和结果摘要）
neosec workflow -t <template> -v target:<ip> --verbose

# 干运行（只显示将要执行的命令，不实际运行）
neosec workflow -t <template> -v target:<ip> --dry-run

# 指定多个变量
neosec workflow -t <template> \
  -v target:192.168.1.1 \
  -v wordlist:/usr/share/wordlists/dirb/big.txt \
  -v ffuf_threads:80

# 查看执行历史
neosec history
neosec history --limit 20

# 显示版本
neosec --version
```

## 配置工具路径

编辑 `~/.neosec/config.yaml`：

```yaml
tools:
  nmap: /usr/bin/nmap
  ffuf: /usr/local/bin/ffuf

defaults:
  wordlist: /usr/share/wordlists/dirb/common.txt
  timeout: 300
  retry: 1
```

## 自定义脚本插件

在 `~/.neosec/scripts/` 创建脚本，在工作流中用 `"tool": "my_script"` 调用：

```bash
cat ~/.neosec/scripts/my_tool.py
```

```python
import json, sys
payload = json.loads(sys.stdin.read())
args = payload["args"]
result_dir = payload["result_dir"]

# 执行逻辑...

print(json.dumps({"status": "success"}))
```

支持语言：`.py` `.sh` `.rb` `.js` `.pl` `.php` 及可执行文件

## 故障排查

**工具未找到**

```bash
which nmap ffuf           # 确认工具已安装
# 在 config.yaml 中指定完整路径
```

**html_extraction 报依赖缺失**

```bash
pipx inject neosec beautifulsoup4 httpx
```

**执行超时**

在模板 step 中调大 `timeout`（单位：秒）：

```json
{ "timeout": 900 }
```

## 下一步

- 阅读完整指南：[docs/GUIDE.md](docs/GUIDE.md)
- 查看示例：[examples/](examples/)
- 了解脚本插件机制：[docs/GUIDE.md#脚本插件](docs/GUIDE.md)
