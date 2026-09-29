import unittest
from dataclasses import asdict

from app.application.action_executor import ActionExecutor
from app.application.agent_orchestrator import AgentOrchestrator
from app.coach import CoachDecision, Correction
from app.domain.action import ActionResult
from app.domain.decision import AgentAction, AgentDecision
from app.domain.task import LearningTask, TaskPriority, TaskSource, TaskStatus
from app.domain.turn import TurnContext, TurnResult


class ActionExecutorTests(unittest.TestCase):
    def decision(self, action, **kwargs):
        return AgentDecision(action=action, reason=kwargs.pop("reason", "test reason"), **kwargs)

    def test_simple_actions_execute_without_learning_side_effects(self):
        executor = ActionExecutor()
        for action in (AgentAction.CONTINUE, AgentAction.GENTLE_FEEDBACK,
                       AgentAction.INTERRUPT, AgentAction.REVIEW_LATER,
                       AgentAction.TASK_FOLLOW_UP):
            result = executor.execute(self.decision(action))
            self.assertTrue(result.executed)
            self.assertEqual(result.action, action)

    def test_targeted_practice_calls_injected_handler(self):
        calls = []
        executor = ActionExecutor(targeted_practice_handler=lambda decision: calls.append(decision) or "requested")
        result = executor.execute(self.decision(AgentAction.TARGETED_PRACTICE))
        self.assertTrue(result.executed)
        self.assertEqual(result.output, "requested")
        self.assertEqual(len(calls), 1)

    def test_targeted_practice_without_handler_is_not_fake_success(self):
        result = ActionExecutor().execute(self.decision(AgentAction.TARGETED_PRACTICE))
        self.assertFalse(result.executed)
        self.assertIn("not available", result.reason)

    def test_task_follow_up_does_not_change_task(self):
        task = LearningTask(
            task_id="task-1", title="Practice go", description="Use went",
            source=TaskSource.AGENT_DETECTED, status=TaskStatus.ACTIVE,
            priority=TaskPriority.MEDIUM, success_criteria="three uses",
            created_at="2026-01-01", updated_at="2026-01-01",
        )
        before = asdict(task)
        decision = self.decision(AgentAction.TASK_FOLLOW_UP, target_task=task)
        result = ActionExecutor().execute(decision)
        self.assertTrue(result.executed)
        self.assertEqual(before, asdict(task))

    def test_system_error_is_safe(self):
        result = ActionExecutor().execute(self.decision(AgentAction.CONTINUE, reason="system error / turn unavailable"))
        self.assertTrue(result.executed)
        self.assertIn("system error", result.reason)

    def test_asr_uncertainty_is_not_reinterpreted(self):
        decision = self.decision(AgentAction.CONTINUE, asr_uncertain=True)
        result = ActionExecutor().execute(decision)
        self.assertEqual(result.action, AgentAction.CONTINUE)
        self.assertNotIn(result.action, {AgentAction.INTERRUPT, AgentAction.TARGETED_PRACTICE})

    def test_result_serializes(self):
        result = ActionExecutor().execute(self.decision(AgentAction.REVIEW_LATER))
        restored = ActionResult.model_validate_json(result.model_dump_json())
        self.assertEqual(restored, result)

    def test_executor_does_not_call_decision_components(self):
        executor = ActionExecutor()
        decision = self.decision(AgentAction.CONTINUE)
        result = executor.execute(decision)
        self.assertTrue(result.executed)

    def test_orchestrator_can_run_to_action_result(self):
        result = TurnResult(
            context=TurnContext(session_id="s", turn_id=1, phase="conversation", user_text="hello"),
            decision=CoachDecision(),
        )
        action_result = AgentOrchestrator().run(result)
        self.assertIsInstance(action_result, ActionResult)
        self.assertEqual(action_result.action, AgentAction.CONTINUE)


if __name__ == "__main__":
    unittest.main()
