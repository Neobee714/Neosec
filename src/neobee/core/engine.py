"""工作流执行引擎"""
import asyncio
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from rich.console import Console

from ..utils.variables import get_nested_value, replace_variables

console = Console()


class WorkflowEngine:
    """工作流执行引擎"""

    def __init__(self, config, verbose: bool = False, quiet: bool = False, dry_run: bool = False):
        """初始化执行引擎

        Args:
            config: 配置对象
            verbose: 详细模式
            quiet: 静默模式
            dry_run: 干运行模式
        """
        self.config = config
        self.verbose = verbose
        self.quiet = quiet
        self.dry_run = dry_run

        self.context: dict[str, Any] = {
            "variables": {},
            "results": {},
            "metadata": {},
        }

        self.steps_status: dict[str, dict[str, Any]] = {}

    async def execute(
        self,
        template: dict[str, Any],
        variables: dict[str, str],
        output_file: Optional[str] = None,
    ) -> dict[str, Any]:
        """执行工作流"""
        self._init_context(template, variables)

        start_time = datetime.now()
        self.context["metadata"]["start_time"] = start_time.isoformat()
        self.context["metadata"]["workflow_name"] = template["name"]

        steps = template["steps"]
        order_groups = self._group_by_order(steps)

        for order in sorted(order_groups.keys()):
            await self._execute_order_group(order_groups[order])

        end_time = datetime.now()
        self.context["metadata"]["end_time"] = end_time.isoformat()
        self.context["metadata"]["duration"] = (end_time - start_time).total_seconds()

        result = self._generate_result(template)

        if output_file and not self.dry_run:
            self._save_result(result, output_file)

        return result

    def _init_context(self, template: dict[str, Any], variables: dict[str, str]) -> None:
        """初始化执行上下文"""
        template_vars = template.get("variables", {})
        config_defaults = self.config.get("defaults", {})
        self.context["variables"] = {**config_defaults, **template_vars, **variables}

    def _build_template_context(self, item: Any = None) -> dict[str, Any]:
        """构建模板变量替换上下文。"""
        variables = self.context.get("variables", {})
        results = self.context.get("results", {})
        metadata = self.context.get("metadata", {})

        context: dict[str, Any] = {**variables, **results}
        context["variables"] = variables
        context["results"] = results
        context["metadata"] = metadata

        if item is not None:
            context["item"] = item

        return context

    def _group_by_order(self, steps: list[dict]) -> dict[int, list[dict]]:
        """按 order 分组步骤。"""
        groups: dict[int, list[dict]] = {}

        for step in steps:
            order = step["order"]
            if order not in groups:
                groups[order] = []
            groups[order].append(step)

        return groups

    async def _execute_order_group(self, steps: list[dict]) -> None:
        """执行同一 order 的步骤组（支持并行）。"""
        remaining = list(steps)

        while remaining:
            remaining_ids = {step.get("id") for step in remaining if "id" in step}
            runnable = []

            for step in remaining:
                depends_on = step.get("depends_on", [])
                unresolved_same_order = any(dep in remaining_ids for dep in depends_on)
                if not unresolved_same_order:
                    runnable.append(step)

            if not runnable:
                unresolved = [step.get("id", "unknown") for step in remaining]
                raise RuntimeError(
                    f"同一 order 组内存在无法解析的依赖关系: {', '.join(unresolved)}"
                )

            await asyncio.gather(*(self._execute_step(step) for step in runnable))

            runnable_refs = {id(step) for step in runnable}
            remaining = [step for step in remaining if id(step) not in runnable_refs]

    async def _execute_step(self, step: dict[str, Any]) -> None:
        """执行单个步骤。"""
        raw_step = step
        resolved_step = replace_variables(raw_step, self._build_template_context())

        step_id = resolved_step["id"]
        step_name = resolved_step.get("name", step_id)

        self.steps_status[step_id] = {
            "id": step_id,
            "name": step_name,
            "status": "pending",
            "start_time": None,
            "end_time": None,
            "duration": None,
            "result": None,
            "error": None,
        }

        if not self._check_dependencies(resolved_step):
            self.steps_status[step_id]["status"] = "skipped"
            self.steps_status[step_id]["error"] = "dependency failed"
            if self.verbose:
                console.print(f"[yellow]⊘[/yellow] {step_name} - 跳过（依赖失败）")
            return

        if not self._check_condition(resolved_step):
            self.steps_status[step_id]["status"] = "skipped"
            self.steps_status[step_id]["error"] = "condition not met"
            if self.verbose:
                console.print(f"[yellow]⊘[/yellow] {step_name} - 跳过（条件不满足）")
            return

        start_time = datetime.now()
        self.steps_status[step_id]["start_time"] = start_time.isoformat()
        self.steps_status[step_id]["status"] = "running"

        if self.verbose:
            console.print(f"[blue]▶[/blue] {step_name} - 执行中...")

        try:
            if "for_each" in raw_step:
                result = await self._execute_for_each(raw_step)
            else:
                result = await self._run_with_retry(resolved_step, step_name)

            end_time = datetime.now()
            self.steps_status[step_id]["status"] = "success"
            self.steps_status[step_id]["end_time"] = end_time.isoformat()
            self.steps_status[step_id]["duration"] = (end_time - start_time).total_seconds()
            self.steps_status[step_id]["result"] = result

            if "save_result_as" in resolved_step:
                self.context["results"][resolved_step["save_result_as"]] = result

            if self.verbose:
                console.print(f"[green]✓[/green] {step_name} - 完成")

        except Exception as e:
            end_time = datetime.now()
            self.steps_status[step_id]["status"] = "failed"
            self.steps_status[step_id]["end_time"] = end_time.isoformat()
            self.steps_status[step_id]["duration"] = (end_time - start_time).total_seconds()
            self.steps_status[step_id]["error"] = str(e)

            if self.verbose or not self.quiet:
                console.print(f"[red]✗[/red] {step_name} - 失败: {e}")

            if not resolved_step.get("continue_on_error", False):
                raise

    async def _run_with_retry(self, step: dict[str, Any], step_name: str) -> dict[str, Any]:
        """带重试执行单个工具步骤。"""
        retry_count = step.get("retry", 0)

        for attempt in range(retry_count + 1):
            try:
                if attempt > 0:
                    if self.verbose or not self.quiet:
                        console.print(f"[yellow]↻[/yellow] {step_name} - 重试 {attempt}/{retry_count}")
                    await asyncio.sleep(5)

                return await self._run_tool(step)
            except Exception:
                if attempt == retry_count:
                    raise

        raise RuntimeError(f"步骤执行失败: {step_name}")

    def _check_dependencies(self, step: dict[str, Any]) -> bool:
        """检查步骤依赖是否满足。"""
        depends_on = step.get("depends_on", [])

        for dep_id in depends_on:
            dep_status = self.steps_status.get(dep_id, {}).get("status")
            if dep_status != "success":
                return False

        return True

    def _check_condition(self, step: dict[str, Any]) -> bool:
        """检查步骤条件是否满足。"""
        if "when" not in step:
            return True

        when = step["when"]
        condition_type = when["type"]
        source = when["source"]

        source_value = get_nested_value(self._build_template_context(), source)

        if source_value is None:
            return False

        if condition_type == "contains":
            value = when["value"]
            return value in source_value if isinstance(source_value, (list, str)) else False

        if condition_type == "contains_any":
            values = when["values"]
            if not isinstance(values, list):
                values = [values]
            if isinstance(source_value, list):
                return any(v in source_value for v in values)
            return False

        if condition_type == "not_contains_any":
            values = when["values"]
            if not isinstance(values, list):
                values = [values]
            if isinstance(source_value, list):
                return not any(v in source_value for v in values)
            return True

        if condition_type == "equals":
            value = when["value"]
            return source_value == value

        if condition_type == "greater_than":
            value = when["value"]
            return source_value > value

        if condition_type == "less_than":
            value = when["value"]
            return source_value < value

        return False

    async def _execute_for_each(self, step: dict[str, Any]) -> list[dict[str, Any]]:
        """执行 for_each 循环。"""
        for_each_value = step.get("for_each")

        if isinstance(for_each_value, list):
            items = for_each_value
        elif isinstance(for_each_value, str):
            source = for_each_value.strip()
            if source.startswith("{{") and source.endswith("}}"):
                source = source[2:-2].strip()
            items = get_nested_value(self._build_template_context(), source)
        else:
            items = for_each_value

        if not isinstance(items, list):
            raise TypeError(f"for_each 的值不是数组: {for_each_value}")

        results: list[dict[str, Any]] = []

        for index, item in enumerate(items):
            item_context = self._build_template_context(item=item)
            item_step = replace_variables(step, item_context)
            item_step = dict(item_step)
            item_step.pop("for_each", None)

            item_name = f"{step.get('name', step.get('id', 'for_each'))}[{index}]"
            try:
                item_result = await self._run_with_retry(item_step, item_name)
            except Exception as e:
                if not item_step.get("continue_on_error", False):
                    raise
                item_result = {"status": "failed", "error": str(e)}

            results.append(item_result)

        return results

    async def _run_tool(self, step: dict[str, Any]) -> dict[str, Any]:
        """运行工具。"""
        tool_name = step["tool"]
        args = step.get("args", {})
        timeout = step.get("timeout", self.config.get("defaults.timeout", 300))

        tool_path = self.config.get_tool_path(tool_name)

        if not self.dry_run and not shutil.which(tool_path):
            raise FileNotFoundError(f"工具未找到: {tool_path}")

        cmd = [tool_path]
        for key, value in args.items():
            if key.startswith("-"):
                if isinstance(value, bool):
                    if value:
                        cmd.append(key)
                else:
                    cmd.extend([key, str(value)])
            else:
                cmd.append(str(value))

        if self.verbose or self.dry_run:
            console.print(f"[dim]命令:[/dim] {' '.join(cmd)}")

        if self.dry_run:
            return {"status": "dry_run", "command": " ".join(cmd)}

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)

            if process.returncode != 0:
                raise RuntimeError(
                    f"工具执行失败 (退出码 {process.returncode}): {stderr.decode()}"
                )

            output = stdout.decode()

            if self.verbose:
                console.print(f"[dim]输出:[/dim]\n{output}")

            try:
                return json.loads(output)
            except json.JSONDecodeError:
                return {"status": "success", "raw_output": output}

        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise TimeoutError(f"工具执行超时 ({timeout}秒)")

    def _generate_result(self, template: dict[str, Any]) -> dict[str, Any]:
        """生成执行结果。"""
        steps_result = []
        summary = {"total_steps": 0, "successful": 0, "failed": 0, "skipped": 0}

        for _, status in self.steps_status.items():
            steps_result.append(status)
            summary["total_steps"] += 1

            if status["status"] == "success":
                summary["successful"] += 1
            elif status["status"] == "failed":
                summary["failed"] += 1
            elif status["status"] == "skipped":
                summary["skipped"] += 1

        return {
            "workflow": {
                "name": template["name"],
                "version": template.get("version", "1.0.0"),
                "start_time": self.context["metadata"].get("start_time"),
                "end_time": self.context["metadata"].get("end_time"),
                "duration": self.context["metadata"].get("duration"),
                "status": "completed" if summary["failed"] == 0 else "completed_with_errors",
            },
            "variables": self.context["variables"],
            "steps": steps_result,
            "summary": summary,
        }

    def _save_result(self, result: dict[str, Any], output_file: str) -> None:
        """保存执行结果。"""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        if not self.quiet:
            console.print(f"[green]✓[/green] 结果已保存: {output_path}")
