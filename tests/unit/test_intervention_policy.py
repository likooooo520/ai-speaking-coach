import unittest

from app.application.intervention_policy import InterventionPolicy
from app.application.session_review import SessionReviewGenerator
from app.domain.evidence import Evidence, ErrorEvidence, NaturalnessEvidence
from app.domain.intervention import InterventionType
from app.domain.observation import Observation
from app.application.priority_engine import PriorityEngine
from app.domain.priority import PriorityLevel
from app.coach import Correction, NaturalnessSuggestion


class InterventionPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = InterventionPolicy()

    def case(self, kind="error", frequency=0, requested=None, asr=False):
        observation = Observation(session_id="s", turn_id=1, phase="conversation", user_text="I go yesterday", correction=Correction(needed=kind == "error", original="go", better="went") if kind == "error" else Correction(), naturalness=NaturalnessSuggestion(detected=kind == "naturalness", original="I think") if kind == "naturalness" else NaturalnessSuggestion())
        evidence = Evidence(error=ErrorEvidence(current_error_detected=kind == "error", historical_frequency=frequency, user_requested=requested, asr_uncertain=asr), naturalness=NaturalnessEvidence(current_naturalness_detected=kind == "naturalness", historical_frequency=frequency, user_requested=requested))
        return observation, evidence

    def decide(self, kind="error", frequency=0, **kwargs):
        observation, evidence = self.case(kind, frequency, kwargs.pop("requested", None), kwargs.pop("asr", False))
        priority = PriorityEngine().evaluate(observation, evidence)
        return self.policy.decide(observation, evidence, priority, **kwargs)

    def test_normal_error_stays_in_conversation(self):
        self.assertEqual(self.decide().type, InterventionType.CONTINUE)
        self.assertEqual(self.decide(frequency=2).type, InterventionType.CONTINUE)

    def test_communication_breakdown_interrupts(self):
        self.assertEqual(self.decide(session_context={"communication_impact": True}).type, InterventionType.INTERRUPT)

    def test_user_request_creates_task(self):
        decision = self.decide(requested=True, mode="teacher")
        self.assertEqual(decision.type, InterventionType.TARGETED_PRACTICE)
        self.assertTrue(decision.should_create_task)

    def test_modes_and_guards(self):
        self.assertEqual(self.decide(frequency=3, mode="foreign_friend").type, InterventionType.CONTINUE)
        self.assertEqual(self.decide(frequency=3, mode="teacher").type, InterventionType.INTERRUPT)
        self.assertEqual(self.decide(recently_practiced=True).type, InterventionType.REVIEW_LATER)
        self.assertEqual(self.decide(asr=True).type, InterventionType.CONTINUE)

    def test_naturalness_and_review_extension(self):
        decision = self.decide("naturalness", frequency=3, mode="foreign_friend")
        self.assertEqual(decision.type, InterventionType.REVIEW_LATER)
        review = SessionReviewGenerator().generate([decision], [{"priority": "high"}])
        self.assertTrue(review.should_offer_extension)


if __name__ == "__main__":
    unittest.main()
