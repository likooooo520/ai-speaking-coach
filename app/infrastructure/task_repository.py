"""LearningTask 的 JSON 持久化适配器。"""

import json
from dataclasses import asdict
from pathlib import Path
from typing import Iterable, Optional

from app.domain.task import LearningTask, TaskPriority, TaskSource, TaskStatus


class JsonTaskRepository:
    def __init__(self, file_path="data/learning_tasks.json"):
        self.file_path = Path(file_path)

    def list(self) -> Iterable[LearningTask]:
        if not self.file_path.exists():
            return []
        try:
            raw = json.loads(self.file_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"无法读取 Task JSON: {self.file_path}") from exc
        if not isinstance(raw, list):
            raise ValueError("Task JSON 顶层必须是数组")
        return [self._from_dict(item) for item in raw]

    def get(self, task_id: str) -> Optional[LearningTask]:
        return next((task for task in self.list() if task.task_id == task_id), None)

    def save(self, task: LearningTask) -> None:
        tasks = list(self.list())
        for index, existing in enumerate(tasks):
            if existing.task_id == task.task_id:
                tasks[index] = task
                break
        else:
            tasks.append(task)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(
            json.dumps([self._to_dict(item) for item in tasks], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @staticmethod
    def _to_dict(task):
        data = asdict(task)
        data["source"] = task.source.value
        data["status"] = task.status.value
        data["priority"] = task.priority.value
        return data

    @staticmethod
    def _from_dict(data):
        data = dict(data)
        data["source"] = TaskSource(data["source"])
        data["status"] = TaskStatus(data["status"])
        data["priority"] = TaskPriority(data["priority"])
        return LearningTask(**data)
