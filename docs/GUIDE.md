# Neosec 使用指南

## 目录

1. [工作流模板](#工作流模板)
2. [步骤字段参考](#步骤字段参考)
3. [条件执行](#条件执行)
4. [脚本插件](#脚本插件)
5. [内置工具](#内置工具)
6. [输出结构](#输出结构)
7. [最佳实践](#最佳实践)

---

## 工作流模板

### 基本结构

```json
{
  "name": "my_workflow",
  "description": "描述信息",
  "version": "1.0.0",
  "variables": {
    "target": "",
    "wordlist": "/usr/share/wordlists/dirb/common.txt"
  },
  "steps": [ ... ]
}
```

### 工具参数格式

```json
{
  "args": {
    "-sV": true,             // 布尔标志：只添加 -sV
    "-p": "1-10000",        // 键值对：添加 -p 1-10000
    "target": "{{target}}"  // 位置参数：直接追加值
  }
}
```

等价命令：`nmap -sV -p 1-10000 192.168.1.1`

---

## 步骤字段参考

| 字段 | 必需 | 说明 |
|---|---|---|
| `id` | ✓ | 唯一标识符，用于 `depends_on` 引用 |
| `order` | ✓ | 执行顺序（数字越小越先执行，同 order 自动并行） |
| `tool` | ✓ | 工具名称、路径或脚本插件名 |
| `args` | ✓ | 工具参数 |
| `name` | — | 显示名称 |
| `depends_on` | — | 依赖步骤 ID 列表 |
| `when` | — | 条件执行配置 |
| `save_result_as` | — | 保存结果到上下文的变量名 |
| `timeout` | — | 超时秒数（默认 300） |
| `retry` | — | 失败重试次数（默认 0） |
| `continue_on_error` | — | 失败时是否继续（默认 false） |

---

## 条件执行

使用 `when` 根据前置步骤结果决定是否执行：

```json
{
  "id": "ffuf_80",
  "depends_on": ["port_scan"],
  "when": {
    "type": "contains",
    "source": "port_scan_result.open_ports",
    "value": 80
  },
  "tool": "ffuf"
}
```

### 条件类型

| 类型 | 说明 | 字段 |
|---|---|---|
| `contains` | 列表包含指定值 | `value` |
| `contains_any` | 列表包含任意一个值 | `values` |
| `not_contains_any` | 列表不包含任何值 | `values` |
| `equals` | 精确匹配 | `value` |
| `greater_than` | 大于 | `value` |
| `less_than` | 小于 | `value` |

### 数据传递

`save_result_as` 保存步骤结果，后续步骤通过 `{{variable}}` 引用：

```json
{ "save_result_as": "port_scan_result" }
```

```json
{ "source": "port_scan_result.open_ports" }
```

支持嵌套访问：`{{port_scan_result.services.0.port}}`

---

## 脚本插件

### 查找路径

```
用户目录  ~/.neosec/scripts/<tool_name>.py   （优先）
内置目录  neobee/scripts/<tool_name>.py
外部工具  PATH 中的可执行文件                （最后）
```

### 支持语言

| 扩展名 | 执行器 |
|---|---|
| `.py` | `python3` |
| `.sh` | `bash` |
| `.rb` | `ruby` |
| `.js` | `node` |
| `.pl` | `perl` |
| `.php` | `php` |
| 无扩展名 | 直接执行（需 `chmod +x` + shebang） |

### 接口协议

**stdin（engine → 脚本）：**

```json
{
  "args": { "source": "ffuf_80_result", "base_url": "http://..." },
  "context": {
    "variables": { "target": "192.168.1.1" },
    "results": { "ffuf_80_result": { "entries": [...] } }
  },
  "result_dir": "/home/user/.neosec/result/192.168.1.1",
  "step_id": "extract_html_80"
}
```

**stdout（脚本 → engine）：**

```json
{ "status": "success", "pages": 3, "output_file": "/path/to/output.txt" }
```

脚本自己负责将文件写入 `result_dir`；日志/调试信息输出到 **stderr**（不影响 stdout JSON 解析）。

### 示例脚本（Python）

```python
#!/usr/bin/env python3
import json, sys
from pathlib import Path

payload    = json.loads(sys.stdin.read())
args       = payload["args"]
results    = payload["context"]["results"]
result_dir = Path(payload["result_dir"])
step_id    = payload["step_id"]

# 从前置步骤获取 URL 列表
source  = results.get(args.get("source", ""), {})
entries = source.get("entries", [])
urls    = [e["url"] for e in entries if e.get("status") == 200]

# 写入结果文件
out = result_dir / f"{step_id}.txt"
out.write_text("\n".join(urls))
print(f"[my_tool] 处理了 {len(urls)} 个 URL", file=sys.stderr)

# 返回 JSON 结果
print(json.dumps({"status": "success", "count": len(urls), "output_file": str(out)}))
```

### 示例脚本（Bash）

```bash
#!/bin/bash
input=$(cat)  # 读取 stdin JSON
target=$(echo "$input" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['context']['variables']['target'])")
result_dir=$(echo "$input" | python3 -c "import sys,json; print(json.load(sys.stdin)['result_dir'])")

# 执行逻辑
echo "扫描 $target" >&2
whoami > "$result_dir/whoami.txt"

# 返回 JSON
echo '{"status": "success"}'
```

---

## 内置工具

### `html_extraction`

批量抓取 URL，清理 HTML 噪声后保存为纯净文本，适合后期提交给 AI 分析。

**参数：**

| 参数 | 说明 | 默认值 |
|---|---|---|
| `source` | context.results 中的 key（读取 entries） | — |
| `base_url` | URL 前缀，用于拼接 entries 的相对 path | — |
| `url_list` | 直接指定 URL 列表（与 source 二选一） | — |
| `filter_status` | 只处理这些状态码（逗号分隔） | `"200"` |
| `timeout` | 单请求超时秒数 | `10` |
| `verify_ssl` | 是否验证 SSL 证书 | `"false"` |

**清理规则：**

- 移除：`<script>` `<style>` `<svg>` `<img>` `<video>` `<audio>` `<iframe>` `<embed>` `<object>` `<noscript>`
- 移除：外联 CSS/favicon 的 `<link>` 标签
- 移除：所有事件属性（`onclick` `onload` 等）、`style` 属性、`class`、`id`、`data-*` 属性
- 移除：HTML 注释
- 保留：`<title>` `<h1-h6>` `<p>` `<a href>` `<form>` `<input>` `<textarea>` `<button>` `<meta name/content>` 等语义标签

**工作流配置示例：**

```json
{
  "id": "extract_html_80",
  "tool": "html_extraction",
  "depends_on": ["ffuf_port_80"],
  "args": {
    "source": "ffuf_80_result",
    "base_url": "http://{{target}}",
    "filter_status": "200,301,302",
    "timeout": "10",
    "verify_ssl": "false"
  }
}
```

**依赖安装：**

```bash
pipx inject neosec beautifulsoup4 httpx
```

---

## 输出结构

每次扫描的所有结果统一保存至 `~/.neosec/result/<target>/`：

```
~/.neosec/result/192.168.1.1/
  port_scan.txt            nmap 原始 stdout（过滤 SF 指纹/HTTP 响应体）
  ffuf_port_80.txt         ffuf :80 原始 stdout
  ffuf_port_443.txt        ffuf :443 原始 stdout（若端口开放）
  ffuf_port_8080.txt       ffuf :8080 原始 stdout
  extract_html_80.txt      去噪后的 HTML 源码（html_extraction）
  summary.txt              工作流摘要命令输出
  workflow_result.json     结构化结果数据
```

`workflow_result.json` 结构：

```json
{
  "workflow": { "name": "...", "start_time": "...", "duration": 17.1 },
  "variables": { "target": "192.168.1.1" },
  "steps": [
    {
      "id": "port_scan",
      "status": "success",
      "duration": 12.7,
      "result": {
        "open_ports": [22, 80, 8080],
        "services": [
          { "port": 80, "service": "http", "product": "Apache httpd", "version": "2.4.62" }
        ]
      }
    }
  ],
  "summary": { "total_steps": 7, "successful": 4, "failed": 0, "skipped": 3 }
}
```

---

## 最佳实践

### 扫描流程

1. 先用 `nmap_ffuf_workflow.json` 做快速侦察
2. 查看 `port_scan.txt` 和 `ffuf_port_*.txt` 了解攻击面
3. 对有价值的 Web 端口运行 `html_extraction_workflow.json`
4. 将 `extract_html_*.txt` 内容提交给 AI 分析潜在漏洞
5. 使用 `--report` 生成 Markdown 报告存档

### 模板设计

- 关键步骤设置 `"continue_on_error": false`
- 不稳定步骤设置 `"retry": 2-3`
- 合理设置 `timeout`，避免无限等待
- 用 `depends_on` + `when` 减少不必要的扫描

### 自定义扩展

- 用户脚本放在 `~/.neosec/scripts/`，优先级高于内置脚本
- 脚本日志输出到 stderr，结果 JSON 输出到 stdout
- 将文件写入 `result_dir`，保持统一的输出目录结构
