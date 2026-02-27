Project Configuration - 渗透测试百宝箱 (Penetration Testing Toolbox)
1. PROJECT CONTEXT (项目上下文)
WHAT: 本项目是一个企业级、基于 Python (Programming Language - 编程语言) 的高延展性自动化安全测试框架底座。它将零散的外部开源渗透工具（如 Nmap (Network Mapper - 网络映射器)、Nuclei (基于模板的高速漏洞扫描引擎)、Ffuf (Fuzz Faster U Fool - 极速Web模糊测试工具)）整合为一个高度协同的自动化生态系统。

WHY: 旨在消除传统安全脚本零散、脆弱且难以维护的工程痛点，通过 Plugin Architecture (插件化架构 - 一种将核心系统与扩展功能解耦的设计模式) 和强健的底层进程调度机制，实现 DAST (Dynamic Application Security Testing - 动态应用安全测试) 评估流程的完全自动化。

HOW: 核心代码引擎与外部测试用例、执行 Payload (攻击载荷 - 指用于利用系统漏洞的代码或数据) 完全解耦。系统主要通过 YAML (YAML Ain't Markup Language - 一种直观的数据序列化格式) 声明式地编排并执行 DAG (Directed Acyclic Graph - 有向无环图) 扫描工作流。

2. CRITICAL RULES & ARCHITECTURE DECISIONS (核心架构规则与决策)
Plugin Architecture (插件化架构): 严禁使用内置系统函数 __import__() (Advanced module import - 用于动态加载模块的内置底层函数) 或 importlib (Import Library - Python标准的动态导入库) 进行粗糙的代码拼接。所有外部适配器插件必须基于 pluggy (A minimalist production ready plugin system - 一个极简的生产级插件系统) 框架，通过 @hookimpl (Hook Implementation - pluggy中用于标识钩子实现的装饰器) 和 @hookspec (Hook Specification - pluggy中用于定义钩子规范的装饰器) 进行严格的契约驱动开发。

Process Management (进程安全管理): 框架在调用外部安全工具二进制文件时，强制使用 subprocess (Subprocess management - Python子进程管理内置模块) 封装类。所有命令参数必须以列表（List）形式传入操作底层，严禁使用 shell=True (Execute through shell - subprocess中通过系统Shell执行命令的参数配置) 以从根源上杜绝 Command Injection (命令注入 - 一种常见的高危系统级安全漏洞)。

Non-blocking I/O (非阻塞输入输出): 捕获外部扫描子进程的 stdout (Standard Output - 标准输出流) 时，必须引入 fcntl (File Control - 操作系统底层文件控制接口模块) 设置 Non-blocking I/O (非阻塞输入输出 - 不阻塞主执行线程的数据流读取机制)，或结合 asyncio (Asynchronous I/O - Python原生异步并发库) 进行实时流式读取，从而彻底攻克由于 Pipe Exhaustion (管道缓冲区耗尽 - 指操作系统内部进程通信管道数据容量达到上限) 造成的系统 Deadlock (死锁 - 多个进程因互相等待系统资源而永久挂起的状态) 陷阱。

Process Tree Killing (进程树彻底查杀): 启动外部扫描引擎时，必须通过 os.setsid() (Set Session ID - 用于创建新会话并设置进程组ID的系统接口函数) 分配独立的 PGID (Process Group ID - 进程组ID)。当任务发生 Timeout (超时 - 任务执行的生命周期时间限制) 时，调度器必须向整个进程组发送 SIGTERM (Signal Terminate - 软件终止请求信号) 和 SIGKILL (Signal Kill - 操作系统强制杀死进程信号)，彻底拔除产生死循环的僵尸 Process Tree (进程树 - 具有父子层级衍生关系的进程集合)。

Data Modeling (内部数据结构建模): 外部适配器完成扫描解析后，必须摒弃工具的原始输出文本。对于 JSON (JavaScript Object Notation - 一种轻量级数据交换格式) 响应，强制引入 pydantic (Data validation library - 基于Python类型提示的严格数据验证库) 进行反序列化处理；对于 XML (Extensible Markup Language - 可扩展标记语言) 报告，使用 xml.etree.ElementTree (ElementTree XML API - Python内置的XML结构解析库) 提取 AST (Abstract Syntax Tree - 抽象语法树)，最终统一清洗并转换为业务核心层面的 Asset (资产) 与 Vulnerability (漏洞) 数据模型。

3. DIRECTORY STRUCTURE (目录树结构基准)
configs/: 存放 YAML 工作流调度引擎的全局配置文件与爆破字典预设挂载路径。

src/core/: 核心引擎层，包含全局 pluggy 总线系统初始化代码与 hookspecs.py 契约定义。

src/execution/: 系统进程调度器层，包含防死锁的执行器安全封装与 DAG 工作流解析分发逻辑。

src/models/: 数据模型层，专门存放基于 dataclasses (Data Classes - Python内置的用于生成数据封装类的模块) 或 pydantic 的领域对象定义。

src/adapters/: 外部扩展工具的适配器插件实现目录（须基于 @hookimpl 注册介入）。

tests/: 使用 pytest (Python testing framework - Python生态中功能成熟的测试框架) 编写的隔离单元测试与功能集成测试套件。

4. DEVELOPMENT PATTERNS (编码规范要求)
Type Hinting (类型提示): 项目中所有函数的参数以及返回值签名，必须包含严格的 Type Hints (类型提示 - Python语言中用于指定变量预期类型的静态检查特性)。

Exception Handling (异常捕获处理): 严禁在代码中使用极其宽泛且毫无意义的 except Exception:。必须精准捕获底层系统调用异常，并在框架交互边界处抛出语义清晰的自定义异常类（例如自定义的 ToolExecutionError）。

Logging (系统日志收集): 基于 logging (Logging facility for Python - Python内置的系统日志记录模块) 建立标准的统一层级输出（包含 Trace, Debug, Info, Warning, Error - 涵盖从底层深度追踪到运行时致命错误的各个标准日志严重级别）。

Bilingual Annotations (双语术语注释强制规范): [最高优先级] 每当在系统代码的注释、异常抛出信息或文档中提到任何计算机专业名词、架构设计模式、内置系统函数或引入的第三方核心库时，必须严格在其后方附加括号，以包含其完整的英文全称及准确精炼的中文技术解释。

5. 注释要求
使用中文注释

6. 其他
工具名字：Neosec
