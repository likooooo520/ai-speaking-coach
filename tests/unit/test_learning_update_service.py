import unittest
from unittest.mock import MagicMock

from app.application.learning_update_service import LearningUpdateService
from app.coach import ASRUncertainty, CoachDecision, Correction, NaturalnessSuggestion
from app.domain.turn import TurnContext, TurnResult


class LearningUpdateServiceTests(unittest.TestCase):

    def setUp(self):
        self.error_memory = MagicMock()
        self.naturalness_memory = MagicMock()
        self.performance_tracker = MagicMock()
        self.service = LearningUpdateService(
            self.error_memory,
            self.naturalness_memory,
            self.performance_tracker,
        )

    def result(self, decision, turn_id=1):
        return TurnResult(
            context=TurnContext(
                session_id="session-1",
                turn_id=turn_id,
                phase="main_conversation",
                user_text="I like many food.",
            ),
            decision=decision,
        )

    def test_valid_correction_updates_error_memory_once(self):
        result = self.result(CoachDecision(correction=Correction(
            needed=True, original="many food", better="many kinds of food"
        )))

        events = self.service.apply(result)

        self.error_memory.add_error.assert_called_once()
        self.assertEqual([event.type.value for event in events], [
            "error_detected", "performance_recorded"
        ])

    def test_valid_naturalness_updates_memory_once(self):
        result = self.result(CoachDecision(naturalness=NaturalnessSuggestion(
            detected=True, original="I think", alternatives=["I'd say"]
        )))

        self.service.apply(result)

        self.naturalness_memory.add_expression.assert_called_once()

    def test_performance_is_recorded_and_adjusted_once(self):
        self.service.apply(self.result(CoachDecision()))

        self.performance_tracker.record.assert_called_once()
        self.performance_tracker.adjust_difficulty.assert_called_once()

    def test_all_valid_learning_data_updates_once(self):
        result = self.result(CoachDecision(
            correction=Correction(needed=True, original="many food", better="many kinds of food"),
            naturalness=NaturalnessSuggestion(detected=True, original="I think", alternatives=["I'd say"]),
        ))

        events = self.service.apply(result)

        self.error_memory.add_error.assert_called_once()
        self.naturalness_memory.add_expression.assert_called_once()
        self.performance_tracker.record.assert_called_once()
        self.assertEqual(len(events), 3)

    def test_system_error_does_not_update_learning_data(self):
        self.service.apply(self.result(CoachDecision(system_error=True)))

        self.error_memory.add_error.assert_not_called()
        self.naturalness_memory.add_expression.assert_not_called()
        self.performance_tracker.record.assert_not_called()
        self.performance_tracker.adjust_difficulty.assert_not_called()

    def test_asr_uncertainty_does_not_create_error_event(self):
        result = self.result(CoachDecision(
            correction=Correction(needed=True, original="many food", better="many kinds of food"),
            asr_uncertainty=[ASRUncertainty(heard="food", possible="foods")],
        ))

        events = self.service.apply(result)

        self.error_memory.add_error.assert_not_called()
        self.assertEqual([event.type.value for event in events], ["performance_recorded"])

    def test_same_turn_is_not_applied_twice(self):
        result = self.result(CoachDecision())

        self.service.apply(result)
        repeated_events = self.service.apply(result)

        self.performance_tracker.record.assert_called_once()
        self.performance_tracker.adjust_difficulty.assert_called_once()
        self.assertEqual(repeated_events, [])


if __name__ == "__main__":
    unittest.main()
