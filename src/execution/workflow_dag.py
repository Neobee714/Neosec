"""
工作流 DAG 调度器模块 (Workflow DAG Scheduler Module)

本模块实现基于有向无环图 (Directed Acyclic Graph) 的工作流编排引擎。
支持任务依赖管理、拓扑排序、并发执行和条件分支。
"""

from typing import Any, Optional, Callable
from collections import defaultdict, deque
import asyncio
from datetime import datetime

from ..core.config_parser import WorkflowConfig, WorkflowTask
from ..core.exceptions import WorkflowValidationError
from ..models import ScanResult


class TaskNode:
    """
    任务节点类 (Task Node Class)

    表示 DAG 中的单个任务节点。
    """

    def __init__(self, task: WorkflowTask):
        self.task = task
        self.status: str = "pending"  # pending, running, completed, failed, skipped
        self.result: Optional[Any] = None
        self.error: Optional[Exception] = None
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None

    @property
    def duration(self) -> Optional[float]:
        """计算任务执行时长（秒）"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def __repr__(self) -> str:
        return f"TaskNode(id={self.task.id}, tool={self.task.tool}, status={self.status})"


class WorkflowDAG:
    """
    工作流 DAG 类 (Workflow DAG Class)

    构建和管理任务依赖图，执行拓扑排序和并发调度。
    """

    def __init__(self, workflow_config: WorkflowConfig):
        """
        初始化工作流 DAG

        Args:
            workflow_config: 工作流配置对象
        """
        self.config = workflow_config
        self.nodes: dict[str, TaskNode] = {}
        self.adjacency_list: dict[str, list[str]] = defaultdict(list)  # 邻接表
        self.in_degree: dict[str, int] = {}  # 入度表

        # 构建 DAG
        self._build_dag()

    def _build_dag(self) -> None:
        """
        构建 DAG 数据结构 (Build DAG Data Structure)

        从配置文件构建任务节点和依赖关系。
        """
        # 创建所有任务节点
        for task in self.config.tasks:
            self.nodes[task.id] = TaskNode(task)
            self.in_degree[task.id] = 0

        # 构建邻接表和入度表
        for task in self.config.tasks:
            for dep_id in task.depends_on:
                if dep_id not in self.nodes:
                    raise WorkflowValidationError(
                        workflow_name=self.config.name,
                        reason=f"任务 '{task.id}' 依赖的任务 '{dep_id}' 不存在"
                    )
                # dep_id -> task.id 的边
                self.adjacency_list[dep_id].append(task.id)
                self.in_degree[task.id] += 1

    def topological_sort(self) -> list[list[str]]:
        """
        拓扑排序 (Topological Sort)

        使用 Kahn 算法进行拓扑排序，返回分层的任务执行顺序。
        同一层的任务可以并发执行。

        Returns:
            任务 ID 的分层列表，例如: [["task1", "task2"], ["task3"], ["task4", "task5"]]

        Raises:
            WorkflowValidationError: 存在循环依赖
        """
        # 复制入度表（避免修改原始数据）
        in_degree_copy = self.in_degree.copy()
        queue = deque([task_id for task_id, degree in in_degree_copy.items() if degree == 0])

        sorted_layers: list[list[str]] = []
        visited_count = 0

        while queue:
            # 当前层的所有任务（入度为 0 的任务）
            current_layer = list(queue)
            sorted_layers.append(current_layer)
            queue.clear()

            # 处理当前层的每个任务
            for task_id in current_layer:
                visited_count += 1

                # 减少所有依赖该任务的任务的入度
                for neighbor in self.adjacency_list[task_id]:
                    in_degree_copy[neighbor] -= 1
                    if in_degree_copy[neighbor] == 0:
                        queue.append(neighbor)

        # 检查是否存在循环依赖
        if visited_count != len(self.nodes):
            raise WorkflowValidationError(
                workflow_name=self.config.name,
                reason="工作流存在循环依赖，无法完成拓扑排序"
            )

        return sorted_layers

    def get_node(self, task_id: str) -> Optional[TaskNode]:
        """获取任务节点"""
        return self.nodes.get(task_id)

    def get_ready_tasks(self) -> list[str]:
        """
        获取所有就绪的任务 (Get Ready Tasks)

        返回所有依赖已满足且尚未执行的任务 ID 列表。

        Returns:
            就绪任务 ID 列表
        """
        ready_tasks = []
        for task_id, node in self.nodes.items():
            if node.status != "pending":
                continue

            # 检查所有依赖是否已完成
            all_deps_completed = all(
                self.nodes[dep_id].status == "completed"
                for dep_id in node.task.depends_on
            )

            if all_deps_completed:
                ready_tasks.append(task_id)

        return ready_tasks

    def mark_task_running(self, task_id: str) -> None:
        """标记任务为运行中"""
        node = self.nodes[task_id]
        node.status = "running"
        node.started_at = datetime.now()

    def mark_task_completed(self, task_id: str, result: Any) -> None:
        """标记任务为已完成"""
        node = self.nodes[task_id]
        node.status = "completed"
        node.result = result
        node.completed_at = datetime.now()

    def mark_task_failed(self, task_id: str, error: Exception) -> None:
        """标记任务为失败"""
        node = self.nodes[task_id]
        node.status = "failed"
        node.error = error
        node.completed_at = datetime.now()

    def mark_task_skipped(self, task_id: str) -> None:
        """标记任务为跳过"""
        node = self.nodes[task_id]
        node.status = "skipped"
        node.completed_at = datetime.now()

    def is_completed(self) -> bool:
        """检查所有任务是否已完成（包括失败和跳过）"""
        return all(
            node.status in ["completed", "failed", "skipped"]
            for node in self.nodes.values()
        )

    def get_statistics(self) -> dict[str, Any]:
        """
        获取工作流执行统计信息 (Get Workflow Statistics)

        Returns:
            统计信息字典
        """
        total = len(self.nodes)
        completed = sum(1 for n in self.nodes.values() if n.status == "completed")
        failed = sum(1 for n in self.nodes.values() if n.status == "failed")
        skipped = sum(1 for n in self.nodes.values() if n.status == "skipped")
        running = sum(1 for n in self.nodes.values() if n.status == "running")
        pending = sum(1 for n in self.nodes.values() if n.status == "pending")

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "skipped": skipped,
            "running": running,
            "pending": pending
        }


class WorkflowExecutor:
    """
    工作流执行器类 (Workflow Executor Class)

    负责实际执行工作流中的任务，支持并发和错误处理。
    """

    def __init__(
        self,
        dag: WorkflowDAG,
        task_executor: Callable[[WorkflowTask], Any],
        max_concurrent: int = 5
    ):
        """
        初始化工作流执行器

        Args:
            dag: WorkflowDAG 实例
            task_executor: 任务执行函数，接收 WorkflowTask 返回执行结果
            max_concurrent: 最大并发任务数
        """
        self.dag = dag
        self.task_executor = task_executor
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def execute_task(self, task_id: str) -> None:
        """
        执行单个任务 (Execute Single Task)

        Args:
            task_id: 任务 ID
        """
        node = self.dag.get_node(task_id)
        if not node:
            return

        async with self.semaphore:
            try:
                self.dag.mark_task_running(task_id)

                # 执行任务（可能是同步或异步函数）
                result = self.task_executor(node.task)
                if asyncio.iscoroutine(result):
                    result = await result

                self.dag.mark_task_completed(task_id, result)

            except Exception as e:
                self.dag.mark_task_failed(task_id, e)

    async def execute_workflow(self) -> ScanResult:
        """
        执行整个工作流 (Execute Entire Workflow)

        按照拓扑排序的顺序，分层并发执行任务。

        Returns:
            ScanResult 扫描结果汇总

        Raises:
            WorkflowValidationError: 工作流验证失败
        """
        # 获取拓扑排序的任务层级
        task_layers = self.dag.topological_sort()

        # 逐层执行任务
        for layer in task_layers:
            # 并发执行当前层的所有任务
            tasks = [self.execute_task(task_id) for task_id in layer]
            await asyncio.gather(*tasks, return_exceptions=True)

        # 构建扫描结果
        scan_result = ScanResult(
            scan_id=f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            target="",  # 需要从任务中提取
            workflow_name=self.dag.config.name
        )

        # 收集所有任务的结果
        for node in self.dag.nodes.values():
            if node.result:
                # 假设结果包含 assets 和 vulnerabilities
                if isinstance(node.result, dict):
                    if "assets" in node.result:
                        scan_result.assets.extend(node.result["assets"])
                    if "vulnerabilities" in node.result:
                        scan_result.vulnerabilities.extend(node.result["vulnerabilities"])

        scan_result.mark_completed()
        return scan_result

    def execute_workflow_sync(self) -> ScanResult:
        """
        同步执行工作流 (Execute Workflow Synchronously)

        Returns:
            ScanResult 扫描结果汇总
        """
        return asyncio.run(self.execute_workflow())
