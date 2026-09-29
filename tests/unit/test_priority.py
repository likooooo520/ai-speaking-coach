import unittest

from app.application.priority_engine import PriorityEngine
from app.coach import Correction, NaturalnessSuggestion
from app.domain.evidence import Evidence, ErrorEvidence, NaturalnessEvidence
from app.domain.observation import Observation
from app.domain.priority import PriorityLevel, priority_level


class PriorityEngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = PriorityEngine()

    def observation(self, correction=None, naturalness=None):
        return Observation(session_id="s1", turn_id=1, phase="conversation", user_text="text",
                           correction=correction or Correction(),
                           naturalness=naturalness or NaturalnessSuggestion())

    def test_single_error_is_low_priority(self):
        result = self.engine.evaluate(self.observation(Correction(needed=True, original="many food")),
                                      Evidence(error=ErrorEvidence(current_error_detected=True)))
        self.assertEqual(result.score, 0.30)
        self.assertEqual(result.level, PriorityLevel.LOW)
        self.assertEqual(result.reasons, ["current_error"])

    def test_error_frequency_three_increases_priority(self):
        result = self.engine.evaluate(self.observation(Correction(needed=True, original="many food")), Evidence(
            error=ErrorEvidence(current_error_detected=True, historical_match=True, historical_frequency=3)))
        self.assertEqual(result.score, 0.70)
        self.assertEqual(result.level, PriorityLevel.HIGH)
        self.assertIn("repeated_historical_error", result.reasons)
        self.assertIn("frequent_historical_error", result.reasons)

    def test_user_requested_significantly_increases_priority(self):
        result = self.engine.evaluate(self.observation(Correction(needed=True, original="many food")), Evidence(
            error=ErrorEvidence(current_error_detected=True, user_requested=True)))
        self.assertEqual(result.score, 0.50)
        self.assertEqual(result.level, PriorityLevel.MEDIUM)
        self.assertIn("user_requested", result.reasons)

    def test_asr_uncertainty_lowers_error_priority(self):
        result = self.engine.evaluate(self.observation(Correction(needed=True, original="many food")), Evidence(
            error=ErrorEvidence(current_error_detected=True, asr_uncertain=True)))
        self.assertEqual(result.score, 0.0)
        self.assertIn("asr_uncertainty_penalty", result.reasons)

    def test_asr_uncertainty_without_error_produces_no_priority(self):
        result = self.engine.evaluate(self.observation(), Evidence(
            error=ErrorEvidence(asr_uncertain=True)))
        self.assertIsNone(result)

    def test_first_naturalness_signal_is_not_high(self):
        result = self.engine.evaluate(self.observation(naturalness=NaturalnessSuggestion(detected=True, original="I think")),
                                      Evidence(naturalness=NaturalnessEvidence(current_naturalness_detected=True,
                                                                             historical_frequency=1)))
        self.assertEqual(result.score, 0.25)
        self.assertNotEqual(result.level, PriorityLevel.HIGH)

    def test_naturalness_frequency_three_increases_priority(self):
        result = self.engine.evaluate(self.observation(naturalness=NaturalnessSuggestion(detected=True, original="I think")),
                                      Evidence(naturalness=NaturalnessEvidence(current_naturalness_detected=True,
                                                                             historical_match=True, historical_frequency=3)))
        self.assertAlmostEqual(result.score, 0.60)
        self.assertEqual(result.level, PriorityLevel.MEDIUM)
        self.assertIn("repeated_historical_naturalness", result.reasons)

    def test_recently_practiced_lowers_priority(self):
        result = self.engine.evaluate(self.observation(Correction(needed=True, original="many food")), Evidence(
            error=ErrorEvidence(current_error_detected=True, recently_practiced=True)))
        self.assertEqual(result.score, 0.15)
        self.assertIn("recently_practiced_penalty", result.reasons)

    def test_evaluate_all_returns_multiple_results_sorted(self):
        error = self.observation(Correction(needed=True, original="many food"))
        naturalness = self.observation(naturalness=NaturalnessSuggestion(detected=True, original="I think"))
        results = self.engine.evaluate_all([
            (naturalness, Evidence(naturalness=NaturalnessEvidence(current_naturalness_detected=True))),
            (error, Evidence(error=ErrorEvidence(current_error_detected=True, user_requested=True))),
        ])
        self.assertEqual([item.target_type for item in results], ["error", "naturalness"])

    def test_score_is_clamped(self):
        original_weight = self.engine.ERROR_WEIGHTS["current_error"]
        try:
            self.engine.ERROR_WEIGHTS["current_error"] = 2.0
            result = self.engine.evaluate(self.observation(Correction(needed=True, original="many food")), Evidence(
                error=ErrorEvidence(current_error_detected=True)))
            self.assertEqual(result.score, 1.0)
        finally:
            self.engine.ERROR_WEIGHTS["current_error"] = original_weight

    def test_level_mapping(self):
        self.assertEqual(priority_level(0.39), PriorityLevel.LOW)
        self.assertEqual(priority_level(0.40), PriorityLevel.MEDIUM)
        self.assertEqual(priority_level(0.70), PriorityLevel.HIGH)

    def test_engine_does_not_mutate_inputs(self):
        observation = self.observation(Correction(needed=True, original="many food"))
        evidence = Evidence(error=ErrorEvidence(current_error_detected=True))
        before = (observation.model_dump(), evidence.model_dump())
        self.engine.evaluate(observation, evidence)
        self.assertEqual(before, (observation.model_dump(), evidence.model_dump()))


if __name__ == "__main__":
    unittest.main()
