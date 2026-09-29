import unittest
from unittest.mock import MagicMock

from app.application.observation_builder import ObservationBuilder
from app.coach import ASRUncertainty, CoachDecision, Correction, NaturalnessSuggestion
from app.domain.turn import TurnContext, TurnResult


class ObservationBuilderTests(unittest.TestCase):
    def result(self, decision=None):
        return TurnResult(context=TurnContext(session_id="s1", turn_id=2, phase="conversation",
                                              user_text="I like many food", topic="food"),
                          decision=decision or CoachDecision())

    def test_error_history_and_asr_are_separate(self):
        memory = MagicMock()
        memory.match_current_error.return_value = {"count": 3}
        memory.get_error_frequency.return_value = 3
        result = self.result(CoachDecision(correction=Correction(needed=True, original="many food"),
                                           asr_uncertainty=[ASRUncertainty(heard="food", possible="foods")]))
        observation, evidence = ObservationBuilder().build(result, error_memory=memory)
        self.assertTrue(observation.is_valid)
        self.assertTrue(evidence.error.current_error_detected)
        self.assertTrue(evidence.error.historical_match)
        self.assertEqual(evidence.error.historical_frequency, 3)
        self.assertTrue(evidence.error.asr_uncertain)

    def test_naturalness_and_unmatched_history(self):
        memory = MagicMock()
        memory.match_current_expression.return_value = None
        memory.get_expression_frequency.return_value = 0
        result = self.result(CoachDecision(naturalness=NaturalnessSuggestion(detected=True, original="I think",
                                                                               alternatives=["I'd say"])))
        _, evidence = ObservationBuilder().build(result, naturalness_memory=memory)
        self.assertTrue(evidence.naturalness.current_naturalness_detected)
        self.assertFalse(evidence.naturalness.historical_match)

    def test_system_error_produces_no_observation(self):
        self.assertEqual(ObservationBuilder().build(self.result(CoachDecision(system_error=True))), (None, None))

    def test_builder_does_not_mutate_memory(self):
        memory = MagicMock()
        memory.match_current_error.return_value = None
        memory.get_error_frequency.return_value = 0
        ObservationBuilder().build(self.result(), error_memory=memory)
        memory.add_error.assert_not_called()
