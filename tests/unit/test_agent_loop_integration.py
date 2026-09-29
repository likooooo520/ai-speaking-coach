import unittest
from unittest.mock import MagicMock

from app.application.action_executor import ActionExecutor
from app.application.agent_orchestrator import AgentOrchestrator
from app.application.learning_update_service import LearningUpdateService
from app.coach import ASRUncertainty, CoachDecision, Correction
from app.domain.action import ActionResult
from app.domain.decision import AgentAction
from app.domain.task import LearningTask, TaskPriority, TaskSource, TaskStatus
from app.domain.turn import TurnContext, TurnResult


class AgentLoopIntegrationTests(unittest.TestCase):
    def result(self, decision=None):
        return TurnResult(
            context=TurnContext(session_id="s", turn_id=1, phase="conversation", user_text="I go yesterday"),
            decision=decision or CoachDecision(),
        )

    def test_normal_turn_reaches_action_result(self):
        result = AgentOrchestrator().run(self.result())
        self.assertIsInstance(result, ActionResult)
        self.assertEqual(result.action, AgentAction.CONTINUE)

    def test_feedback_interrupt_and_review_do_not_end_session(self):
        gentle = AgentOrchestrator().run(
            self.result(CoachDecision(correction=Correction(needed=True, original="go", better="went"))),
            mode="business_coach", session_context={"professional_relevance": True},
        )
        interrupt = AgentOrchestrator().run(
            self.result(CoachDecision(correction=Correction(needed=True, original="go", better="went"))),
            session_context={"communication_impact": True},
        )
        review = AgentOrchestrator().run(
            self.result(CoachDecision(correction=Correction(needed=True, original="go", better="went"))),
            session_context={"recently_practiced": True},
        )
        self.assertTrue(gentle.executed)
        self.assertEqual(gentle.action, AgentAction.GENTLE_FEEDBACK)
        self.assertTrue(interrupt.executed)
        self.assertEqual(interrupt.action, AgentAction.INTERRUPT)
        self.assertTrue(review.executed)
        self.assertEqual(review.action, AgentAction.REVIEW_LATER)

    def test_task_follow_up_does_not_modify_task(self):
        task = LearningTask(
            task_id="task-1", title="Improve go", description="Practice go",
            source=TaskSource.AGENT_DETECTED, status=TaskStatus.ACTIVE,
            priority=TaskPriority.MEDIUM, success_criteria="three uses",
            created_at="2026-01-01", updated_at="2026-01-01",
        )
        result = AgentOrchestrator().run(
            self.result(CoachDecision(correction=Correction(needed=True, original="go", better="went"))),
            active_tasks=[task],
        )
        self.assertEqual(result.action, AgentAction.TASK_FOLLOW_UP)
        self.assertEqual(task.status, TaskStatus.ACTIVE)
        self.assertEqual(task.progress, {})

    def test_targeted_practice_handler_and_absence_are_explicit(self):
        turn = self.result(CoachDecision(correction=Correction(needed=True, original="go", better="went")))
        handler = MagicMock(return_value="practice started")
        executable = AgentOrchestrator(action_executor=ActionExecutor(targeted_practice_handler=handler)).run(
            turn, user_requested=True,
        )
        unavailable = AgentOrchestrator().run(turn, user_requested=True)
        self.assertTrue(executable.executed)
        handler.assert_called_once()
        self.assertFalse(unavailable.executed)
        self.assertIn("not available", unavailable.reason)

    def test_system_error_does_not_enter_learning_update(self):
        service = MagicMock()
        turn = self.result(CoachDecision(system_error=True))
        action_result = AgentOrchestrator().run(turn)
        if not turn.system_error:
            service.apply(turn)
        self.assertEqual(action_result.action, AgentAction.CONTINUE)
        self.assertIsNone(action_result.target_task)
        service.apply.assert_not_called()

    def test_asr_uncertainty_does_not_create_intervention(self):
        turn = self.result(CoachDecision(
            correction=Correction(needed=True, original="go", better="went"),
            asr_uncertainty=[ASRUncertainty(heard="go", possible="goal")],
        ))
        action_result = AgentOrchestrator().run(turn)
        self.assertNotIn(action_result.action, {AgentAction.INTERRUPT, AgentAction.TARGETED_PRACTICE})

    def test_learning_update_is_not_duplicated_by_agent_loop(self):
        error_memory = MagicMock()
        naturalness_memory = MagicMock()
        performance = MagicMock()
        service = LearningUpdateService(error_memory, naturalness_memory, performance)
        turn = self.result(CoachDecision(correction=Correction(needed=True, original="go", better="went")))
        AgentOrchestrator().run(turn, error_memory=error_memory, naturalness_memory=naturalness_memory)
        service.apply(turn)
        self.assertEqual(error_memory.add_error.call_count, 1)
        service.apply(turn)
        self.assertEqual(error_memory.add_error.call_count, 1)


if __name__ == "__main__":
    unittest.main()
