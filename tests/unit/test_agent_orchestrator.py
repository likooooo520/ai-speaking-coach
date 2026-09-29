import unittest
from dataclasses import asdict

from app.application.agent_orchestrator import AgentOrchestrator
from app.coach import ASRUncertainty, CoachDecision, Correction
from app.domain.decision import AgentAction
from app.domain.task import LearningTask, TaskPriority, TaskSource, TaskStatus
from app.domain.turn import TurnContext, TurnResult


class AgentOrchestratorTests(unittest.TestCase):
    def result(self, decision=None):
        return TurnResult(
            context=TurnContext(session_id="s1", turn_id=1, phase="conversation", user_text="I go yesterday"),
            decision=decision or CoachDecision(),
        )

    def test_no_issue_reaches_continue(self):
        decision = AgentOrchestrator().decide(self.result())
        self.assertEqual(decision.action, AgentAction.CONTINUE)
        self.assertIsNotNone(decision.intervention)

    def test_low_priority_error_continues(self):
        result = self.result(CoachDecision(correction=Correction(needed=True, original="go", better="went")))
        self.assertEqual(AgentOrchestrator().decide(result).action, AgentAction.CONTINUE)

    def test_communication_impact_interrupts(self):
        result = self.result(CoachDecision(correction=Correction(needed=True, original="go", better="went")))
        decision = AgentOrchestrator().decide(result, session_context={"communication_impact": True})
        self.assertEqual(decision.action, AgentAction.INTERRUPT)

    def test_active_task_follow_up(self):
        task = LearningTask(
            task_id="task-1", title="Improve go", description="Practice go",
            source=TaskSource.AGENT_DETECTED, status=TaskStatus.ACTIVE,
            priority=TaskPriority.MEDIUM, success_criteria="three uses",
            created_at="2026-01-01", updated_at="2026-01-01",
        )
        result = self.result(CoachDecision(correction=Correction(needed=True, original="go", better="went")))
        decision = AgentOrchestrator().decide(result, active_tasks=[task])
        self.assertEqual(decision.action, AgentAction.TASK_FOLLOW_UP)
        self.assertEqual(decision.target_task.task_id, "task-1")

    def test_targeted_practice_is_only_returned(self):
        result = self.result(CoachDecision(correction=Correction(needed=True, original="go", better="went")))
        decision = AgentOrchestrator().decide(result, user_requested=True)
        self.assertEqual(decision.action, AgentAction.TARGETED_PRACTICE)

    def test_system_error_is_safe(self):
        decision = AgentOrchestrator().decide(self.result(CoachDecision(system_error=True)))
        self.assertEqual(decision.action, AgentAction.CONTINUE)
        self.assertIn("system error", decision.reason)
        self.assertIsNone(decision.intervention)
        self.assertIsNone(decision.target_task)

    def test_asr_uncertainty_does_not_interrupt_by_itself(self):
        result = self.result(CoachDecision(
            correction=Correction(needed=True, original="go", better="went"),
            asr_uncertainty=[ASRUncertainty(heard="go", possible="goal")],
        ))
        decision = AgentOrchestrator().decide(result)
        self.assertNotIn(decision.action, {AgentAction.INTERRUPT, AgentAction.TARGETED_PRACTICE})
        self.assertTrue(decision.asr_uncertain)

    def test_modes_use_existing_policy(self):
        result = self.result(CoachDecision(correction=Correction(needed=True, original="go", better="went")))
        foreign = AgentOrchestrator().decide(result, mode="foreign_friend")
        teacher = AgentOrchestrator().decide(result, mode="teacher")
        business = AgentOrchestrator().decide(
            result, mode="business_coach", session_context={"professional_relevance": True},
        )
        self.assertEqual(foreign.action, AgentAction.CONTINUE)
        self.assertEqual(teacher.action, AgentAction.CONTINUE)
        self.assertEqual(business.action, AgentAction.GENTLE_FEEDBACK)

    def test_orchestrator_does_not_mutate_injected_task(self):
        task = LearningTask(
            task_id="task-1", title="Improve go", description="Practice go",
            source=TaskSource.AGENT_DETECTED, status=TaskStatus.ACTIVE,
            priority=TaskPriority.MEDIUM, success_criteria="three uses",
            created_at="2026-01-01", updated_at="2026-01-01",
        )
        before = asdict(task)
        result = self.result(CoachDecision(correction=Correction(needed=True, original="go", better="went")))
        AgentOrchestrator().decide(result, active_tasks=[task])
        self.assertEqual(before, asdict(task))


if __name__ == "__main__":
    unittest.main()
