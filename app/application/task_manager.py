"""学习任务生命周期服务。"""

from datetime import datetime, timezone
from typing import Callable, Iterable, Optional, Protocol
from uuid import uuid4

from app.domain.task import LearningTask, TaskPriority, TaskSource, TaskStatus


class TaskRepository(Protocol):
    def save(self, task: LearningTask) -> None: ...
    def get(self, task_id: str) -> Optional[LearningTask]: ...
    def list(self) -> Iterable[LearningTask]: ...


class InvalidTaskTransition(ValueError):
    """任务生命周期转换不合法。"""


class DuplicateTaskError(ValueError):
    """已有任务覆盖同一学习目标。"""


class TaskManager:
    _transitions = {
        TaskStatus.PROPOSED: {TaskStatus.ACCEPTED, TaskStatus.CANCELLED},
        TaskStatus.ACCEPTED: {TaskStatus.ACTIVE, TaskStatus.PAUSED, TaskStatus.CANCELLED},
        TaskStatus.ACTIVE: {TaskStatus.PRACTICING, TaskStatus.PAUSED, TaskStatus.CANCELLED},
        TaskStatus.PRACTICING: {TaskStatus.REVIEW, TaskStatus.ACTIVE, TaskStatus.PAUSED},
        TaskStatus.REVIEW: {TaskStatus.COMPLETED, TaskStatus.ACTIVE, TaskStatus.PAUSED},
        TaskStatus.PAUSED: {TaskStatus.ACTIVE, TaskStatus.CANCELLED},
        TaskStatus.COMPLETED: {TaskStatus.ACTIVE},
        TaskStatus.CANCELLED: set(),
    }

    def __init__(self, repository: TaskRepository, clock: Optional[Callable[[], datetime]] = None):
        self.repository = repository
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def create_task(self, *, title: str, description: str, source: TaskSource,
                    priority: TaskPriority, success_criteria: str,
                    long_term_goal_id: Optional[str] = None, coach_mode: Optional[str] = None,
                    related_memory_ids=None, related_evidence_ids=None, related_observation_ids=None,
                    progress=None, task_id: Optional[str] = None) -> LearningTask:
        duplicate = self.find_duplicate(title=title, description=description, long_term_goal_id=long_term_goal_id)
        if duplicate is not None:
            raise DuplicateTaskError(f"已有任务覆盖该目标: {duplicate.task_id}")
        now = self._now()
        task = LearningTask(
            task_id=task_id or str(uuid4()), title=title, description=description,
            source=source, status=TaskStatus.PROPOSED, priority=priority,
            success_criteria=success_criteria, created_at=now, updated_at=now,
            long_term_goal_id=long_term_goal_id, coach_mode=coach_mode,
            related_memory_ids=list(related_memory_ids or []), related_evidence_ids=list(related_evidence_ids or []),
            related_observation_ids=list(related_observation_ids or []), progress=dict(progress or {}),
        )
        self.repository.save(task)
        return task

    def find_duplicate(self, *, title: str, description: str, long_term_goal_id: Optional[str] = None):
        key = self._target_key(title, description)
        for task in self.repository.list():
            if self._target_key(task.title, task.description) == key and task.long_term_goal_id == long_term_goal_id:
                return task
        return None

    def get_task(self, task_id: str) -> LearningTask:
        task = self.repository.get(task_id)
        if task is None:
            raise KeyError(task_id)
        return task

    def accept_task(self, task_id): return self._transition(task_id, TaskStatus.ACCEPTED, accepted_at=True)
    def pause_task(self, task_id): return self._transition(task_id, TaskStatus.PAUSED)
    def cancel_task(self, task_id): return self._transition(task_id, TaskStatus.CANCELLED)
    def reopen_task(self, task_id): return self._transition(task_id, TaskStatus.ACTIVE)
    def activate_task(self, task_id): return self._transition(task_id, TaskStatus.ACTIVE)
    def start_practice(self, task_id): return self._transition(task_id, TaskStatus.PRACTICING, started_at=True)
    def review_task(self, task_id): return self._transition(task_id, TaskStatus.REVIEW)
    def complete_task(self, task_id): return self._transition(task_id, TaskStatus.COMPLETED, completed_at=True)

    def update_progress(self, task_id: str, progress: dict) -> LearningTask:
        task = self.get_task(task_id)
        task.progress = dict(progress)
        task.updated_at = self._now()
        self.repository.save(task)
        return task

    def _transition(self, task_id, target, **timestamps):
        task = self.get_task(task_id)
        if target not in self._transitions[task.status]:
            raise InvalidTaskTransition(f"不允许从 {task.status.value} 转换到 {target.value}")
        task.status = target
        now = self._now()
        task.updated_at = now
        for field in timestamps:
            setattr(task, field, now)
        self.repository.save(task)
        return task

    def _now(self): return self._clock().isoformat()

    @staticmethod
    def _target_key(title, description):
        return " ".join(f"{title} {description}".lower().split())
