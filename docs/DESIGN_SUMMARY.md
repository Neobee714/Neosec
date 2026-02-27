# NeoSec 框架设计总结

## 项目概述

NeoSec 是一个严格按照 specification.md 和 research.md 要求设计的企业级自动化渗透测试框架。该框架采用现代软件工程最佳实践，将零散的开源安全工具整合为一个高度协同的自动化生态系统。

## 核心架构组件

### 1. 核心引擎层 (src/core/)

#### 插件系统 (hookspecs.py & engine.py)
- **技术选型**: 基于 pluggy 框架实现发布-订阅模式
- **核心钩子**:
  - `neosec_register_tool`: 工具注册
  - `neosec_validate_dependencies`: 依赖验证
  - `neosec_build_command`: 命令构建
  - `neosec_parse_output`: 输出解析
  - `neosec_on_scan_start/complete`: 生命周期事件
- **优势**: 完全解耦的事件驱动架构，支持无限扩展

#### 异常系统 (exceptions.py)
- 精准的异常层级设计，避免宽泛的 Exception 捕获
- 包含详细的错误上下文信息
- 主要异常类:
  - `ToolExecutionError`: 工具执行失败
  - `SubprocessTimeoutError`: 进程超时
  - `ConfigurationError`: 配置错误
  - `DataParsingError`: 数据解析失败

#### 配置解析器 (config_parser.py)
- 基于 Pydantic 的严格数据验证
- 支持 YAML 格式的配置文件
- 自动验证循环依赖和数据完整性

### 2. 数据模型层 (src/models/)

#### 资产模型 (asset.py)
- **Host**: 主机资产（IP、主机名、操作系统、端口列表）
- **Port**: 端口信息（端口号、协议、服务版本）
- **WebApplication**: Web 应用指纹
- **Subdomain**: 子域名资产
- **Asset**: 统一的资产容器

#### 漏洞模型 (vulnerability.py)
- **Vulnerability**: 标准化漏洞数据结构
- **CVSSScore**: CVSS 评分系统
- **SeverityLevel**: 严重程度枚举（Critical/High/Medium/Low/Info）
- **VulnerabilityCategory**: 漏洞分类（SQL注入、XSS、RCE等）
- **ScanResult**: 扫描结果汇总

### 3. 执行层 (src/execution/)

#### 进程运行器 (process_runner.py)
**安全特性**:
- ✅ 防止命令注入：强制列表形式传参，禁止 `shell=True`
- ✅ 非阻塞 I/O：使用 asyncio 避免管道死锁
- ✅ 超时熔断：自动杀死超时进程
- ✅ 进程树清理：使用 PGID 彻底清除僵尸进程

**核心类**:
- `ProcessRunner`: 单进程执行器
- `ProcessPool`: 进程池管理器（限制并发数）
- `ProcessResult`: 执行结果封装

#### 工作流 DAG 调度器 (workflow_dag.py)
- **拓扑排序**: Kahn 算法实现任务依赖解析
- **并发执行**: 同一层级的任务并行执行
- **循环检测**: 自动检测并拒绝循环依赖
- **状态管理**: 跟踪每个任务的执行状态

### 4. 适配器层 (src/adapters/)

#### 基类设计 (base_adapter.py)
- 抽象基类定义标准接口
- 自动实现 pluggy 钩子
- 内置依赖验证逻辑

#### Nmap 适配器示例 (recon/nmap_adapter.py)
- 命令构建：支持多种扫描模式（SYN/TCP/UDP）
- XML 解析：使用 ElementTree 构建 AST
- 数据转换：将 XML 转换为标准化的 Asset 对象

### 5. 工具函数库 (src/utils/)

#### 日志系统 (logger.py)
- 彩色分级日志（TRACE/DEBUG/INFO/WARNING/ERROR/CRITICAL）
- 支持控制台和文件双重输出
- 单例模式确保全局一致性

#### 输入验证器 (ip_validators.py)
- IP 地址/网络段验证
- 域名和 URL 验证
- 端口范围验证
- 危险字符检测（防止命令注入）

## 架构设计原则

### 1. 安全性 (Security)
- **命令注入防护**: 所有命令以列表形式传递，严格验证参数
- **输入验证**: 白名单校验所有外部输入
- **进程隔离**: 使用进程组管理，防止资源泄露

### 2. 可扩展性 (Extensibility)
- **插件化架构**: 基于 pluggy 的钩子系统
- **松耦合设计**: 适配器之间完全独立
- **标准化接口**: 统一的数据模型和 API

### 3. 可靠性 (Reliability)
- **非阻塞 I/O**: 使用 asyncio 避免死锁
- **超时熔断**: 防止任务无限挂起
- **精准异常处理**: 避免宽泛的 Exception 捕获

### 4. 可维护性 (Maintainability)
- **类型提示**: 所有函数包含完整的类型注解
- **双语注释**: 中英文术语对照，便于理解
- **模块化设计**: 高内聚、低耦合的目录结构

## 技术栈

| 组件 | 技术选型 | 用途 |
|------|---------|------|
| 插件系统 | pluggy | 事件驱动的插件管理 |
| 数据验证 | pydantic | 严格的类型检查和数据验证 |
| 异步 I/O | asyncio | 非阻塞进程管理 |
| 配置解析 | PyYAML | YAML 配置文件解析 |
| 日志系统 | colorlog | 彩色分级日志输出 |
| 测试框架 | pytest | 单元测试和集成测试 |

## 项目文件统计

- **Python 文件**: 30 个
- **核心模块**: 4 个（core, models, execution, adapters）
- **工具适配器**: 1 个（Nmap，可扩展）
- **测试文件**: 3 个
- **配置文件**: 2 个（neosec.yaml, default_workflow.yaml）

## 使用示例

### 1. 验证依赖
```bash
python main.py validate
```

### 2. 列出可用工具
```bash
python main.py list-tools
```

### 3. 执行扫描
```bash
python main.py scan -t 192.168.1.1 -w configs/default_workflow.yaml -v
```

### 4. 运行测试
```bash
pytest tests/ -v --cov=src
```

## 扩展指南

### 添加新工具适配器

1. 在 `src/adapters/` 下创建新文件
2. 继承 `BaseAdapter` 基类
3. 实现必需的抽象方法：
   - `get_tool_name()`
   - `get_tool_category()`
   - `get_required_binaries()`
   - `build_command()`
   - `parse_output()`
4. 创建全局实例以便自动发现

### 自定义工作流

编辑 `configs/default_workflow.yaml`：
```yaml
name: "custom_scan"
tasks:
  - id: "task1"
    tool: "nmap"
    depends_on: []
    options:
      ports: "1-1000"
```

## 符合规范检查清单

✅ **插件化架构**: 基于 pluggy，严禁使用 importlib
✅ **进程安全管理**: 禁止 shell=True，列表形式传参
✅ **非阻塞 I/O**: 使用 asyncio 和 fcntl
✅ **进程树清理**: 使用 os.setsid() 和 SIGTERM/SIGKILL
✅ **数据建模**: 使用 pydantic 进行严格验证
✅ **类型提示**: 所有函数包含类型注解
✅ **异常处理**: 精准捕获，避免宽泛 Exception
✅ **双语注释**: 中英文术语对照
✅ **目录结构**: 符合 research.md 的架构设计

## 未来扩展方向

1. **更多工具适配器**: Nuclei, Ffuf, SQLmap, Hydra 等
2. **报告生成插件**: HTML/PDF 报告生成
3. **通知插件**: Slack/Email 实时告警
4. **Web 界面**: 基于 FastAPI 的 Web 管理界面
5. **分布式执行**: 支持多节点并行扫描
6. **CI/CD 集成**: GitHub Actions/GitLab CI 插件

## 总结

NeoSec 框架严格遵循 specification.md 和 research.md 的设计要求，实现了一个企业级的自动化渗透测试平台。通过插件化架构、安全的进程管理和标准化的数据模型，框架具备了高度的可扩展性、可靠性和可维护性。

框架的核心优势在于：
1. **安全第一**: 从根本上防止命令注入和资源泄露
2. **高度解耦**: 插件之间完全独立，易于扩展
3. **工程化**: 严格的类型检查、异常处理和测试覆盖

这是一个可以直接投入生产使用的框架底座，为后续集成更多安全工具和功能提供了坚实的基础。
