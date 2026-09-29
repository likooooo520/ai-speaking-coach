import unittest

from app.coach import CoachDecision
from app.domain.learning import LearningEvent, LearningEventType
from app.domain.turn import TurnContext, TurnResult


class TurnModelTests(unittest.TestCase):

    def context(self):
        return TurnContext(
            session_id="session-1",
            turn_id=1,
            phase="main_conversation",
            user_text="I like many food.",
            targeted_practice_context="",
            topic="food"
        )

    def test_turn_context_creation(self):
        context = self.context()
        self.assertEqual(context.turn_id, 1)
        self.assertEqual(context.phase, "main_conversation")

    def test_turn_result_wraps_coach_decision(self):
        result = TurnResult(
            context=self.context(),
            decision=CoachDecision(
                reply="Tell me more.",
                system_error=True
            )
        )
        self.assertTrue(result.system_error)
        self.assertEqual(result.reply, "Tell me more.")

    def test_learning_event_types(self):
        events = [
            LearningEvent(type=LearningEventType.ERROR_DETECTED, original="many food", better="many kinds of food"),
            LearningEvent(type=LearningEventType.NATURALNESS_OBSERVED, original="I think", alternatives=["I'd say"]),
            LearningEvent(type=LearningEventType.PERFORMANCE_RECORDED, performance={"overall": 7}),
            LearningEvent(type=LearningEventType.PRACTICE_STARTED, practice_type="error"),
            LearningEvent(type=LearningEventType.PRACTICE_COMPLETED, practice_type="error"),
            LearningEvent(type=LearningEventType.SESSION_COMPLETED)
        ]
        self.assertEqual(len(events), 6)
        self.assertEqual(events[0].type.value, "error_detected")
        self.assertEqual(events[1].type.value, "naturalness_observed")
        self.assertEqual(events[2].type.value, "performance_recorded")
        self.assertEqual(events[3].type.value, "practice_started")
        self.assertEqual(events[4].type.value, "practice_completed")
        self.assertEqual(events[5].type.value, "session_completed")

    def test_optional_fields_are_optional(self):
        event = LearningEvent(type=LearningEventType.SESSION_COMPLETED)
        self.assertIsNone(event.session_id)
        self.assertEqual(event.alternatives, [])


if __name__ == "__main__":
    unittest.main()
