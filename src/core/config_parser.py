"""
配置解析模块 (Configuration Parser Module)

本模块负责解析 YAML 配置文件和命令行参数，提供统一的配置管理接口。
使用 Pydantic 进行严格的数据验证和类型检查。
"""

from typing import Any, Optional
from pathlib import Path
import yaml
from pydantic import BaseModel, Field, field_validator

from .exceptions import ConfigurationError


class ToolConfig(BaseModel):
    """
    单个工具配置模型 (Tool Configuration Model)

    定义外部工具的路径、参数和执行选项。
    """
    name: str = Field(..., description="工具名称")
    binary_path: Optional[str] = Field(None, description="工具二进制文件路径")
    enabled: bool = Field(True, description="是否启用该工具")
    timeout: int = Field(300, description="执行超时时间（秒）")
    max_concurrent: int = Field(1, description="最大并发实例数")
    custom_args: dict[str, Any] = Field(default_factory=dict, description="自定义参数")

    @field_validator('timeout')
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """验证超时时间必须为正数"""
        if v <= 0:
            raise ValueError("超时时间必须大于 0")
        return v

    @field_validator('max_concurrent')
    @classmethod
    def validate_max_concurrent(cls, v: int) -> int:
        """验证并发数必须为正数"""
        if v <= 0:
            raise ValueError("并发数必须大于 0")
        return v


class WorkflowTask(BaseModel):
    """
    工作流任务模型 (Workflow Task Model)

    定义 DAG 中的单个任务节点。
    """
    id: str = Field(..., description="任务唯一标识符")
    tool: str = Field(..., description="使用的工具名称")
    depends_on: list[str] = Field(default_factory=list, description="依赖的任务ID列表")
    target: Optional[str] = Field(None, description="扫描目标（可从上游任务继承）")
    options: dict[str, Any] = Field(default_factory=dict, description="工具特定选项")
    condition: Optional[str] = Field(None, description="执行条件表达式")


class WorkflowConfig(BaseModel):
    """
    工作流配置模型 (Workflow Configuration Model)

    定义完整的扫描工作流 DAG。
    """
    name: str = Field(..., description="工作流名称")
    description: Optional[str] = Field(None, description="工作流描述")
    tasks: list[WorkflowTask] = Field(..., description="任务列表")
    global_timeout: int = Field(3600, description="全局超时时间（秒）")

    @field_validator('tasks')
    @classmethod
    def validate_no_cycles(cls, tasks: list[WorkflowTask]) -> list[WorkflowTask]:
        """验证任务依赖不存在循环"""
        # 简单的循环检测（深度优先搜索）
        task_map = {task.id: task for task in tasks}
        visited = set()
        rec_stack = set()

        def has_cycle(task_id: str) -> bool:
            if task_id in rec_stack:
                return True
            if task_id in visited:
                return False

            visited.add(task_id)
            rec_stack.add(task_id)

            task = task_map.get(task_id)
            if task:
                for dep in task.depends_on:
                    if dep not in task_map:
                        raise ValueError(f"任务 '{task_id}' 依赖的任务 '{dep}' 不存在")
                    if has_cycle(dep):
                        return True

            rec_stack.remove(task_id)
            return False

        for task in tasks:
            if has_cycle(task.id):
                raise ValueError(f"工作流存在循环依赖，涉及任务: {task.id}")

        return tasks


class GlobalConfig(BaseModel):
    """
    全局配置模型 (Global Configuration Model)

    框架的顶层配置结构。
    """
    project_name: str = Field("NeoSec", description="项目名称")
    log_level: str = Field("INFO", description="日志级别")
    output_dir: Path = Field(Path("data/reports"), description="输出目录")
    wordlists_dir: Path = Field(Path("configs/wordlists"), description="字典目录")
    tools: dict[str, ToolConfig] = Field(default_factory=dict, description="工具配置")
    workflows: dict[str, WorkflowConfig] = Field(default_factory=dict, description="工作流配置")

    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """验证日志级别"""
        valid_levels = ["TRACE", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"无效的日志级别: {v}，必须是 {valid_levels} 之一")
        return v_upper


class ConfigParser:
    """
    配置解析器类 (Configuration Parser Class)

    负责加载和解析 YAML 配置文件。
    """

    @staticmethod
    def load_from_file(config_path: Path) -> GlobalConfig:
        """
        从 YAML 文件加载配置 (Load Configuration from YAML File)

        Args:
            config_path: 配置文件路径

        Returns:
            GlobalConfig 实例

        Raises:
            ConfigurationError: 配置文件解析失败
        """
        if not config_path.exists():
            raise ConfigurationError(
                config_file=str(config_path),
                reason="配置文件不存在"
            )

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                raw_config = yaml.safe_load(f)

            if raw_config is None:
                raw_config = {}

            # 使用 Pydantic 验证和解析
            config = GlobalConfig(**raw_config)
            return config

        except yaml.YAMLError as e:
            raise ConfigurationError(
                config_file=str(config_path),
                reason=f"YAML 解析错误: {str(e)}"
            )
        except Exception as e:
            raise ConfigurationError(
                config_file=str(config_path),
                reason=f"配置验证失败: {str(e)}"
            )

    @staticmethod
    def load_workflow_from_file(workflow_path: Path) -> WorkflowConfig:
        """
        从 YAML 文件加载工作流配置 (Load Workflow from YAML File)

        Args:
            workflow_path: 工作流配置文件路径

        Returns:
            WorkflowConfig 实例

        Raises:
            ConfigurationError: 工作流配置解析失败
        """
        if not workflow_path.exists():
            raise ConfigurationError(
                config_file=str(workflow_path),
                reason="工作流配置文件不存在"
            )

        try:
            with open(workflow_path, 'r', encoding='utf-8') as f:
                raw_workflow = yaml.safe_load(f)

            workflow = WorkflowConfig(**raw_workflow)
            return workflow

        except yaml.YAMLError as e:
            raise ConfigurationError(
                config_file=str(workflow_path),
                reason=f"YAML 解析错误: {str(e)}"
            )
        except Exception as e:
            raise ConfigurationError(
                config_file=str(workflow_path),
                reason=f"工作流验证失败: {str(e)}"
            )

    @staticmethod
    def create_default_config(output_path: Path) -> None:
        """
        创建默认配置文件 (Create Default Configuration File)

        Args:
            output_path: 输出文件路径
        """
        default_config = GlobalConfig()

        # 添加示例工具配置
        default_config.tools = {
            "nmap": ToolConfig(
                name="nmap",
                binary_path="nmap",
                timeout=600,
                max_concurrent=2
            ),
            "nuclei": ToolConfig(
                name="nuclei",
                binary_path="nuclei",
                timeout=300,
                max_concurrent=5
            )
        }

        # 转换为字典并写入 YAML
        config_dict = default_config.model_dump(mode='python')

        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)
