"""模板管理模块"""
import json
import re
from pathlib import Path
from typing import Any, Optional

from rich.console import Console

console = Console()


class TemplateManager:
    """模板管理类"""

    def __init__(self, builtin_templates_dir: Path, user_templates_dir: Path):
        """初始化模板管理器

        Args:
            builtin_templates_dir: 内置模板目录
            user_templates_dir: 用户模板目录
        """
        self.builtin_templates_dir = builtin_templates_dir
        self.user_templates_dir = user_templates_dir

    def list_templates(self) -> dict[str, list[dict[str, str]]]:
        """列出所有可用模板

        Returns:
            {"builtin": [...], "user": [...]}。
        """
        result = {"builtin": [], "user": []}

        if self.builtin_templates_dir.exists():
            for template_file in self.builtin_templates_dir.glob("*.json"):
                try:
                    with open(template_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    result["builtin"].append(
                        {
                            "name": template_file.stem,
                            "description": data.get("description", "无描述"),
                            "path": str(template_file),
                        }
                    )
                except Exception as e:
                    console.print(f"[yellow]警告:[/yellow] 无法读取模板 {template_file.name}: {e}")

        if self.user_templates_dir.exists():
            for template_file in self.user_templates_dir.glob("*.json"):
                try:
                    with open(template_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    result["user"].append(
                        {
                            "name": template_file.stem,
                            "description": data.get("description", "无描述"),
                            "path": str(template_file),
                        }
                    )
                except Exception as e:
                    console.print(f"[yellow]警告:[/yellow] 无法读取模板 {template_file.name}: {e}")

        return result

    def find_template(self, template_name: str) -> Optional[Path]:
        """查找模板文件

        查找顺序：文件路径 > 用户模板 > 内置模板。
        """
        template_path = Path(template_name)
        if template_path.exists() and template_path.is_file():
            return template_path

        user_template = self.user_templates_dir / f"{template_name}.json"
        if user_template.exists():
            return user_template

        builtin_template = self.builtin_templates_dir / f"{template_name}.json"
        if builtin_template.exists():
            return builtin_template

        return None

    def load_template(self, template_name: str) -> dict[str, Any]:
        """加载模板"""
        template_path = self.find_template(template_name)
        if not template_path:
            raise FileNotFoundError(f"模板未找到: {template_name}")

        with open(template_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def validate_template(self, template_data: dict[str, Any]) -> tuple[bool, list[str]]:
        """验证模板格式"""
        errors: list[str] = []

        if "name" not in template_data:
            errors.append("缺少必需字段: name")

        if "steps" not in template_data:
            errors.append("缺少必需字段: steps")
        elif not isinstance(template_data["steps"], list):
            errors.append("steps 必须是数组")
        else:
            step_ids = set()
            for i, step in enumerate(template_data["steps"]):
                step_errors = self._validate_step(step, i, step_ids)
                errors.extend(step_errors)
                if "id" in step:
                    step_ids.add(step["id"])

            dep_errors = self._validate_dependencies(template_data["steps"], step_ids)
            errors.extend(dep_errors)

        var_errors = self._validate_variables(template_data)
        errors.extend(var_errors)

        return len(errors) == 0, errors

    def _validate_step(self, step: dict, index: int, existing_ids: set) -> list[str]:
        """验证单个步骤"""
        errors: list[str] = []
        prefix = f"步骤 [{index}]"

        required_fields = ["id", "order", "tool", "args"]
        for field in required_fields:
            if field not in step:
                errors.append(f"{prefix} 缺少必需字段: {field}")

        if "id" in step and step["id"] in existing_ids:
            errors.append(f"{prefix} ID 重复: {step['id']}")

        if "order" in step and not isinstance(step["order"], int):
            errors.append(f"{prefix} order 必须是整数")

        if "args" in step and not isinstance(step["args"], dict):
            errors.append(f"{prefix} args 必须是对象")

        if "timeout" in step and not isinstance(step["timeout"], (int, float)):
            errors.append(f"{prefix} timeout 必须是数字")

        if "retry" in step and not isinstance(step["retry"], int):
            errors.append(f"{prefix} retry 必须是整数")

        if "when" in step:
            errors.extend(self._validate_when_condition(step["when"], prefix))

        return errors

    def _validate_when_condition(self, when: dict, prefix: str) -> list[str]:
        """验证 when 条件"""
        errors: list[str] = []

        valid_types = {
            "contains",
            "contains_any",
            "not_contains_any",
            "equals",
            "greater_than",
            "less_than",
        }

        if "type" not in when:
            errors.append(f"{prefix} when 条件缺少 type 字段")
        elif when["type"] not in valid_types:
            errors.append(f"{prefix} when 条件类型无效: {when['type']}")

        if "source" not in when:
            errors.append(f"{prefix} when 条件缺少 source 字段")

        if when.get("type") in ["contains_any", "not_contains_any"]:
            if "values" not in when:
                errors.append(f"{prefix} when 条件缺少 values 字段")
            else:
                values = when["values"]
                is_var_expr = isinstance(values, str) and values.startswith("{{") and values.endswith("}}")
                if not isinstance(values, list) and not is_var_expr:
                    errors.append(f"{prefix} when 条件的 values 必须是数组或变量表达式")
        else:
            if "value" not in when:
                errors.append(f"{prefix} when 条件缺少 value 字段")

        return errors

    def _validate_dependencies(self, steps: list[dict], step_ids: set) -> list[str]:
        """验证依赖关系"""
        errors: list[str] = []

        for step in steps:
            if "depends_on" not in step:
                continue

            if not isinstance(step["depends_on"], list):
                errors.append(f"步骤 {step.get('id', '?')} 的 depends_on 必须是数组")
                continue

            for dep_id in step["depends_on"]:
                if dep_id not in step_ids:
                    errors.append(f"步骤 {step.get('id', '?')} 依赖的步骤不存在: {dep_id}")

        errors.extend(self._check_circular_dependencies(steps))
        return errors

    def _check_circular_dependencies(self, steps: list[dict]) -> list[str]:
        """检查循环依赖"""
        errors: list[str] = []
        graph: dict[str, list[str]] = {}

        for step in steps:
            step_id = step.get("id")
            if step_id:
                graph[step_id] = step.get("depends_on", [])

        visited = set()
        rec_stack = set()

        def has_cycle(node: str, path: list[str]) -> bool:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor, path):
                        return True
                elif neighbor in rec_stack:
                    cycle_path = path[path.index(neighbor) :] + [neighbor]
                    errors.append(f"检测到循环依赖: {' -> '.join(cycle_path)}")
                    return True

            path.pop()
            rec_stack.remove(node)
            return False

        for node in graph:
            if node not in visited:
                has_cycle(node, [])

        return errors

    def _validate_variables(self, template_data: dict[str, Any]) -> list[str]:
        """验证变量引用"""
        errors: list[str] = []
        defined_vars = set(template_data.get("variables", {}).keys())

        # 允许引擎运行时注入的内建上下文
        builtin_vars = {"item", "variables", "results", "metadata"}

        var_pattern = re.compile(r"\{\{(\w+(?:\.\w+)*)\}\}")

        def find_variables(obj: Any, path: str = "") -> None:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    find_variables(value, f"{path}.{key}" if path else key)
                return

            if isinstance(obj, list):
                for i, item in enumerate(obj):
                    find_variables(item, f"{path}[{i}]")
                return

            if isinstance(obj, str):
                for match in var_pattern.findall(obj):
                    var_name = match.split(".")[0]
                    if (
                        var_name not in builtin_vars
                        and var_name not in defined_vars
                        and not self._is_result_reference(var_name, template_data)
                    ):
                        errors.append(f"未定义的变量引用: {{{{{match}}}}} (位置: {path})")

        find_variables(template_data.get("steps", []))
        return errors

    def _is_result_reference(self, var_name: str, template_data: dict) -> bool:
        """检查是否是结果引用"""
        for step in template_data.get("steps", []):
            if step.get("save_result_as") == var_name:
                return True
        return False
