# NeoSec 项目结构

```
NeoSec/
│
├── bin/                          # 外部二进制依赖存放目录
│
├── configs/                      # 配置文件和工作流定义
│   ├── default_workflow.yaml    # 示例工作流配置
│   ├── neosec.yaml              # 主配置文件
│   └── wordlists/               # 字典文件目录
│
├── data/                         # 运行时数据和输出
│   ├── context/                 # 运行时状态缓存
│   ├── raw_outputs/             # 工具原始输出
│   └── reports/                 # 生成的报告
│
├── docs/                         # 项目文档
│   └── DESIGN_SUMMARY.md        # 设计总结文档
│
├── src/                          # 源代码目录
│   ├── __init__.py
│   │
│   ├── core/                    # 核心引擎层
│   │   ├── __init__.py
│   │   ├── engine.py           # 插件管理器和核心引擎
│   │   ├── hookspecs.py        # Pluggy 钩子规范定义
│   │   ├── exceptions.py       # 自定义异常类
│   │   └── config_parser.py    # YAML 配置解析器
│   │
│   ├── execution/               # 进程调度和工作流编排
│   │   ├── __init__.py
│   │   ├── process_runner.py   # 安全的子进程执行器
│   │   └── workflow_dag.py     # DAG 工作流调度器
│   │
│   ├── models/                  # 数据模型层
│   │   ├── __init__.py
│   │   ├── asset.py            # 资产数据模型
│   │   └── vulnerability.py    # 漏洞数据模型
│   │
│   ├── adapters/                # 工具适配器层
│   │   ├── __init__.py
│   │   ├── base_adapter.py     # 适配器抽象基类
│   │   │
│   │   ├── recon/              # 侦查类工具适配器
│   │   │   ├── __init__.py
│   │   │   └── nmap_adapter.py # Nmap 适配器
│   │   │
│   │   ├── scanners/           # 扫描类工具适配器
│   │   │   └── __init__.py
│   │   │
│   │   └── fuzzers/            # 模糊测试类工具适配器
│   │       └── __init__.py
│   │
│   ├── plugins/                 # 扩展插件
│   │   └── __init__.py
│   │
│   └── utils/                   # 工具函数库
│       ├── __init__.py
│       ├── logger.py           # 日志系统
│       └── ip_validators.py    # 输入验证器
│
├── tests/                       # 测试套件
│   ├── __init__.py
│   ├── test_models.py          # 数据模型测试
│   │
│   ├── test_core/              # 核心模块测试
│   │   ├── __init__.py
│   │   └── test_engine.py
│   │
│   ├── test_execution/         # 执行模块测试
│   │   ├── __init__.py
│   │   └── test_process_runner.py
│   │
│   └── test_adapters/          # 适配器测试
│       └── __init__.py
│
├── .gitignore                   # Git 忽略文件
├── CLAUDE.md                    # 项目配置规范
├── LICENSE                      # MIT 许可证
├── Makefile                     # 自动化构建脚本
├── README.md                    # 项目说明文档
├── main.py                      # 主入口文件
├── requirements.txt             # Python 依赖列表
└── research.md                  # 架构研究文档
```

## 核心模块说明

### 1. src/core/ - 核心引擎
- **engine.py**: 基于 pluggy 的插件管理器，负责插件发现、加载和生命周期管理
- **hookspecs.py**: 定义所有钩子规范，是插件系统的契约接口
- **exceptions.py**: 自定义异常类，提供精准的错误处理
- **config_parser.py**: 基于 Pydantic 的配置解析器，支持 YAML 格式

### 2. src/execution/ - 执行层
- **process_runner.py**: 安全的子进程执行器，防止命令注入、死锁和僵尸进程
- **workflow_dag.py**: DAG 工作流调度器，支持拓扑排序和并发执行

### 3. src/models/ - 数据模型
- **asset.py**: 资产数据模型（Host, Port, WebApplication, Subdomain）
- **vulnerability.py**: 漏洞数据模型（Vulnerability, CVSSScore, ScanResult）

### 4. src/adapters/ - 适配器层
- **base_adapter.py**: 适配器抽象基类，定义标准接口
- **recon/nmap_adapter.py**: Nmap 工具适配器示例

### 5. src/utils/ - 工具函数
- **logger.py**: 彩色分级日志系统
- **ip_validators.py**: 输入验证器，防止命令注入

## 文件统计

- **Python 源文件**: 20 个
- **测试文件**: 6 个
- **配置文件**: 2 个
- **文档文件**: 4 个
- **总代码行数**: 约 3000+ 行

## 关键设计模式

1. **单例模式**: NeoSecEngine, NeoSecLogger
2. **抽象工厂模式**: BaseAdapter
3. **观察者模式**: Pluggy 钩子系统
4. **策略模式**: 工具适配器
5. **模板方法模式**: BaseAdapter 抽象方法

## 依赖关系

```
main.py
  └── src/core/engine.py (NeoSecEngine)
       ├── src/core/hookspecs.py (钩子定义)
       ├── src/adapters/base_adapter.py (适配器基类)
       │    └── src/adapters/recon/nmap_adapter.py (具体适配器)
       ├── src/execution/process_runner.py (进程执行)
       └── src/execution/workflow_dag.py (工作流调度)
            └── src/models/ (数据模型)
```

## 扩展点

1. **添加新工具适配器**: 在 `src/adapters/` 下创建新文件
2. **添加新插件**: 在 `src/plugins/` 下创建新文件
3. **自定义工作流**: 编辑 `configs/` 下的 YAML 文件
4. **扩展数据模型**: 在 `src/models/` 中添加新模型
