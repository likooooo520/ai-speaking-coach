import unittest
from dataclasses import asdict

from app.application.decision_policy import AgentDecisionPolicy
from app.application.intervention_policy import InterventionPolicy
from app.application.priority_engine import PriorityEngine
from app.coach import ASRUncertainty, Correction
from app.domain.decision import AgentAction
from app.domain.evidence import Evidence, ErrorEvidence
from app.domain.intervention import InterventionDecision, InterventionType
from app.domain.observation import Observation
from app.domain.priority import PriorityLevel
from app.domain.task import LearningTask, TaskPriority, TaskSource, TaskStatus


class AgentDecisionPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = AgentDecisionPolicy()
        self.interventions = InterventionPolicy()
        self.priority_engine = PriorityEngine()

    def case(self, *, frequency=0, mode="foreign_friend", context=None, asr=False):
        observation = Observation(
            session_id="s1", turn_id=1, phase="conversation", user_text="I go yesterday",
            correction=Correction(needed=True, original="go", better="went"),
            asr_uncertainty=[ASRUncertainty(heard="go", possible="goal")] if asr else [],
        )
        evidence = Evidence(error=ErrorEvidence(
            current_error_detected=True, historical_frequency=frequency, asr_uncertain=asr,
        ))
        priority = self.priority_engine.evaluate(observation, evidence)
        intervention = self.interventions.decide(
            observation, evidence, priority, mode=mode, session_context=context,
        )
        return observation, evidence, priority, intervention

    def test_no_issue_continues(self):
        observation = Observation(session_id="s", turn_id=1, phase="conversation", user_text="Hello")
        evidence = Evidence()
        decision = self.policy.decide(observation, evidence, None, None)
        self.assertEqual(decision.action, AgentAction.CONTINUE)

    def test_low_priority_issue_continues(self):
        decision = self.policy.decide(*self.case())
        self.assertEqual(decision.action, AgentAction.CONTINUE)

    def test_communication_impact_interrupts(self):
        decision = self.policy.decide(*self.case(context={"communication_impact": True}))
        self.assertEqual(decision.action, AgentAction.INTERRUPT)

    def test_active_task_is_referenced_without_mutation(self):
        task = LearningTask(
            task_id="t1", title="Improve go", description="Practice go",
            source=TaskSource.AGENT_DETECTED, status=TaskStatus.ACTIVE,
            priority=TaskPriority.MEDIUM, success_criteria="three uses",
            created_at="2026-01-01", updated_at="2026-01-01",
        )
        before = asdict(task)
        decision = self.policy.decide(*self.case(), active_task=task)
        self.assertEqual(decision.action, AgentAction.TASK_FOLLOW_UP)
        self.assertEqual(decision.target_task.task_id, "t1")
        self.assertEqual(before, asdict(task))

    def test_targeted_practice(self):
        values = list(self.case())
        values[3] = InterventionDecision(
            type=InterventionType.TARGETED_PRACTICE,
            reason="用户主动提出学习需求", priority=PriorityLevel.MEDIUM,
        )
        decision = self.policy.decide(*values)
        self.assertEqual(decision.action, AgentAction.TARGETED_PRACTICE)

    def test_modes_produce_different_actions(self):
        foreign = self.policy.decide(*self.case(frequency=3, mode="foreign_friend"))
        teacher = self.policy.decide(*self.case(frequency=3, mode="teacher"))
        business = self.policy.decide(*self.case(
            frequency=3, mode="business_coach", context={"professional_relevance": True},
        ))
        self.assertEqual(foreign.action, AgentAction.CONTINUE)
        self.assertEqual(teacher.action, AgentAction.INTERRUPT)
        self.assertEqual(business.action, AgentAction.GENTLE_FEEDBACK)

    def test_system_error_has_no_decision(self):
        self.assertIsNone(self.policy.decide(None, None, None, None, system_error=True))

    def test_asr_uncertainty_does_not_create_intervention(self):
        decision = self.policy.decide(*self.case(asr=True))
        self.assertEqual(decision.action, AgentAction.CONTINUE)
        self.assertTrue(decision.asr_uncertain)
        self.assertFalse(decision.requires_user_confirmation)

    def test_serialization_round_trip(self):
        decision = self.policy.decide(*self.case(context={"communication_impact": True}))
        restored = type(decision).model_validate_json(decision.model_dump_json())
        self.assertEqual(restored, decision)


if __name__ == "__main__":
    unittest.main()
