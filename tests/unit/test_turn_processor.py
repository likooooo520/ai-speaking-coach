import unittest
from unittest.mock import MagicMock

from app.application.turn_processor import TurnProcessor
from app.coach import CoachDecision
from app.domain.turn import TurnContext, TurnResult


class TurnProcessorTests(unittest.TestCase):

    def context(self, targeted=""):
        return TurnContext(
            session_id="session-1",
            turn_id=7,
            phase="targeted_practice",
            user_text="I like many food.",
            targeted_practice_context=targeted,
            duration_minutes=30,
            topic="food",
            language_mode="english_only",
            coach_mode="business_coach",
            feedback_intensity="strong",
            session_difficulty="C1",
            professional_context="Act as an interviewer.",
            coaching_context="Offer one useful improvement if it fits.",
        )

    def test_process_returns_result_with_original_context_and_decision(self):
        coach = MagicMock()
        decision = CoachDecision(reply="Keep going.")
        coach.chat.return_value = decision

        context = self.context()
        result = TurnProcessor(coach).process(context)

        self.assertIsInstance(result, TurnResult)
        self.assertIs(result.context, context)
        self.assertIs(result.decision, decision)

    def test_chat_called_once(self):
        coach = MagicMock()
        coach.chat.return_value = CoachDecision(reply="Okay")

        TurnProcessor(coach).process(self.context())

        coach.chat.assert_called_once_with("I like many food.")
        self.assertEqual(coach.set_session_context.call_args.kwargs["language_mode"], "english_only")

    def test_auto_language_mode_is_forwarded(self):
        coach = MagicMock()
        coach.chat.return_value = CoachDecision(reply="Okay")
        context = self.context().model_copy(update={"language_mode": "auto"})

        TurnProcessor(coach).process(context)

        self.assertEqual(coach.set_session_context.call_args.kwargs["language_mode"], "auto")

    def test_targeted_practice_context_is_forwarded(self):
        coach = MagicMock()
        coach.chat.return_value = CoachDecision(reply="Try again.")
        targeted = "Current step: 2 (repetition)"

        TurnProcessor(coach).process(self.context(targeted))

        kwargs = coach.set_session_context.call_args.kwargs
        self.assertEqual(kwargs["targeted_practice_context"], targeted)
        self.assertEqual(kwargs["phase"], "targeted_practice")
        self.assertEqual(kwargs["topic"], "food")
        self.assertEqual(kwargs["language_mode"], "english_only")
        self.assertEqual(kwargs["duration_minutes"], 30)
        self.assertEqual(kwargs["coach_mode"], "business_coach")
        self.assertEqual(kwargs["feedback_intensity"], "strong")
        self.assertEqual(kwargs["session_difficulty"], "C1")
        self.assertEqual(kwargs["professional_context"], "Act as an interviewer.")
        self.assertEqual(kwargs["coaching_context"], "Offer one useful improvement if it fits.")

    def test_system_error_is_returned_without_processing_side_effects(self):
        coach = MagicMock()
        coach.chat.return_value = CoachDecision(
            reply="Unavailable", system_error=True
        )

        result = TurnProcessor(coach).process(self.context())

        self.assertTrue(result.system_error)
        self.assertIsInstance(result, TurnResult)
        coach.chat.assert_called_once()

    def test_context_is_preserved(self):
        coach = MagicMock()
        coach.chat.return_value = CoachDecision(reply="Okay")
        context = self.context("practice context")

        result = TurnProcessor(coach).process(context)

        self.assertEqual(result.context.model_dump(), context.model_dump())


if __name__ == "__main__":
    unittest.main()
