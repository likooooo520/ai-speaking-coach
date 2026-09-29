import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from app.application.task_manager import DuplicateTaskError, InvalidTaskTransition, TaskManager
from app.domain.task import TaskPriority, TaskSource, TaskStatus
from app.infrastructure.task_repository import JsonTaskRepository


class TaskEngineTests(unittest.TestCase):
    def setUp(self):
        self.repository = JsonTaskRepository(Path(tempfile.mkdtemp()) / "tasks.json")
        self.manager = TaskManager(self.repository, clock=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc))

    def create(self, **kwargs):
        values = {
            "title": "Improve food expressions",
            "description": "Use food, foods, and kinds of food naturally.",
            "source": TaskSource.AGENT_DETECTED,
            "priority": TaskPriority.HIGH,
            "success_criteria": "Use the target forms correctly in three later sessions.",
            "long_term_goal_id": "goal-natural-expression",
            "coach_mode": "teacher",
            "related_memory_ids": ["memory-1"],
            "related_evidence_ids": ["evidence-1"],
        }
        values.update(kwargs)
        return self.manager.create_task(**values)

    def test_create_proposed_task_and_metadata(self):
        task = self.create(source=TaskSource.USER_REQUESTED)
        self.assertEqual(task.status, TaskStatus.PROPOSED)
        self.assertEqual(task.source, TaskSource.USER_REQUESTED)
        self.assertEqual(task.long_term_goal_id, "goal-natural-expression")
        self.assertEqual(task.coach_mode, "teacher")
        self.assertEqual(task.related_memory_ids, ["memory-1"])

    def test_accept_pause_reopen(self):
        task = self.create()
        self.manager.accept_task(task.task_id)
        self.manager.activate_task(task.task_id)
        self.manager.pause_task(task.task_id)
        self.assertEqual(self.manager.get_task(task.task_id).status, TaskStatus.PAUSED)
        self.manager.reopen_task(task.task_id)
        self.assertEqual(self.manager.get_task(task.task_id).status, TaskStatus.ACTIVE)

    def test_cancel_task(self):
        task = self.create()
        self.manager.cancel_task(task.task_id)
        self.assertEqual(self.manager.get_task(task.task_id).status, TaskStatus.CANCELLED)

    def test_practice_progress_review_and_complete(self):
        task = self.create()
        self.manager.accept_task(task.task_id)
        self.manager.activate_task(task.task_id)
        self.manager.start_practice(task.task_id)
        self.manager.update_progress(task.task_id, {"practice_count": 1, "successful_uses": 0})
        self.assertEqual(self.manager.get_task(task.task_id).status, TaskStatus.PRACTICING)
        self.manager.review_task(task.task_id)
        self.assertEqual(self.manager.get_task(task.task_id).status, TaskStatus.REVIEW)
        self.manager.complete_task(task.task_id)
        self.assertEqual(self.manager.get_task(task.task_id).status, TaskStatus.COMPLETED)
        self.assertIsNotNone(self.manager.get_task(task.task_id).completed_at)

    def test_duplicate_task_is_rejected(self):
        self.create()
        with self.assertRaises(DuplicateTaskError):
            self.create()

    def test_different_goal_can_have_distinct_task(self):
        self.create()
        task = self.create(long_term_goal_id="goal-communication")
        self.assertEqual(task.long_term_goal_id, "goal-communication")

    def test_invalid_lifecycle_transition_is_rejected(self):
        task = self.create()
        with self.assertRaises(InvalidTaskTransition):
            self.manager.start_practice(task.task_id)
        self.manager.cancel_task(task.task_id)
        with self.assertRaises(InvalidTaskTransition):
            self.manager.accept_task(task.task_id)

    def test_manager_has_no_learning_state_side_effects(self):
        task = self.create()
        self.manager.update_progress(task.task_id, {"observation_count": 1})
        after = json.loads(self.repository.file_path.read_text(encoding="utf-8"))
        self.assertEqual(len(after), 1)
        self.assertEqual(after[0]["progress"], {"observation_count": 1})

    def test_json_persistence_save_load(self):
        task = self.create(progress={"recurrence": 3})
        loaded = JsonTaskRepository(self.repository.file_path).get(task.task_id)
        self.assertEqual(loaded.task_id, task.task_id)
        self.assertEqual(loaded.progress, {"recurrence": 3})
        self.assertEqual(loaded.source, TaskSource.AGENT_DETECTED)


if __name__ == "__main__":
    unittest.main()
