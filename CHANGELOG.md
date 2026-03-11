# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- subfinder 子域名枚举模板
- nuclei 漏洞扫描集成
- Web UI 界面

---

## [0.1.2] - 2026-03-11

### Added
- **脚本插件机制** — 在 `~/.neosec/scripts/` 或 `neobee/scripts/` 放置脚本即可扩展新工具
  - 查找优先级：用户目录 > 内置目录
  - 支持语言：`.py` `.sh` `.rb` `.js` `.pl` `.php` 及可执行文件
  - 接口协议：stdin 传入 JSON 上下文，stdout 返回 JSON 结果，stderr 用于日志
- **`html_extraction` 内置脚本** — 批量抓取 URL 并清理 HTML 噪声后保存
  - 移除：`<script>` `<style>` `<svg>` `<img>` `<video>` `<iframe>` 外联 CSS 注释 事件属性
  - 保留：`<title>` `<h1-h6>` `<p>` `<a>` `<form>` `<input>` `<button>` 等语义标签
  - 结果保存至 `~/.neosec/result/<ip>/<step_id>.txt`
- **`html_extraction_workflow.json`** — nmap + ffuf + HTML 提取完整工作流模板
- 新增依赖：`beautifulsoup4 ^4.12`、`httpx ^0.27`

### Changed
- ffuf `-o` 自动重定向到 `result_dir`，确保 entries 解析正确且文件整齐归档
- 脚本插件步骤跳过 `_save_tool_stdout`，避免覆盖插件自己写入的输出文件

---

## [0.1.1] - 2026-03-11

### Added
- **结构化输出目录** — 所有结果统一保存至 `~/.neosec/result/<ip>/`
  - `port_scan.txt` — nmap 原始 stdout（过滤 SF 指纹/HTTP 响应体噪声）
  - `ffuf_port_<port>.txt` — ffuf 原始 stdout
  - `summary.txt` — 工作流摘要
  - `workflow_result.json` — 结构化结果（同时保存到 `--output` 路径）
- **Markdown 报告优化**（`--report`）
  - 端口服务表（端口/协议/服务/版本）
  - ffuf 结果直接嵌入原始 stdout（代码块格式）
  - 执行步骤耗时汇总
  - 跳过步骤说明（含具体原因）
- **nmap 输出过滤** — 自动去除 SF 指纹数据、`fingerprint-strings` HTTP 响应体、`service unrecognized` 提示行
- **`nmap_ffuf_workflow.json`** — Nmap 端口扫描 + ffuf 多端口目录爆破内置模板

### Changed
- `workflow_result.json` 移除噪声字段：`raw_output`、`format`、`hosts`
- 跳过的步骤不再写入 JSON 输出，减少冗余数据
- 跳过步骤的 `error` 字段改为 `null`（原为 `"condition not met"`）
- ffuf stdout 输出显示表格式命中结果
- nmap verbose 输出显示按服务分行的端口摘要

---

## [0.1.0] - 2026-03-10

### Added

#### 核心功能
- 工作流执行引擎（asyncio 异步执行）
- 配置管理系统（YAML 配置文件，`~/.neosec/config.yaml`）
- 模板管理系统（内置模板 + 用户模板）
- 变量替换系统（支持嵌套字段访问 `{{result.field}}`）
- CLI 命令：`init` `workflow` `history` `version`
- Rich 终端 UI（实时进度显示）

#### 高级特性
- 并行执行（同一 `order` 的独立步骤自动并行）
- 条件执行（6 种条件类型：`contains` `contains_any` `not_contains_any` `equals` `greater_than` `less_than`）
- 步骤间数据传递（`save_result_as` + `{{variable}}`）
- 循环执行（`for_each`）
- 依赖管理（`depends_on`）
- 错误重试和超时控制
- 执行历史记录

#### 内置模板
- `sequential_workflow.json` — 基础顺序执行
- `sequential_workflow_v2.json` — 带超时和重试
- `parallel_workflow.json` — 并行侦察
- `conditional_web_workflow.json` — 条件执行 Web 扫描
- `conditional_service_workflow.json` — 按服务类型条件执行
- `data_passing_workflow.json` — 数据传递示例

#### 依赖
- Python 3.10+
- typer ^0.12.0
- rich ^13.7.0
- pyyaml ^6.0.1
- aiofiles ^23.2.1

---

[0.1.2]: https://github.com/Neobee714/neosec/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/Neobee714/neosec/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/Neobee714/neosec/releases/tag/v0.1.0
