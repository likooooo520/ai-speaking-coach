import unittest
from types import SimpleNamespace

from app.adaptive_session import AdaptiveSession
from app.coach import CoachDecision, Correction
from app.targeted_practice import TargetedPracticeManager


class TargetedPracticeTests(unittest.TestCase):

    def test_context_contains_each_step_instruction(self):
        practice = TargetedPracticeManager()
        practice.start(
            original="many food",
            better="many kinds of food",
            explanation="Food is uncountable here.",
            category="grammar"
        )

        expected = [
            (1, "correction", "specific mistake"),
            (2, "repetition", "closely related"),
            (3, "variation", "different situation"),
            (4, "free_use", "freely in conversation")
        ]

        for step, name, phrase in expected:
            context = practice.get_context()
            self.assertIn(f"Current step: {step} ({name})", context)
            self.assertIn("many kinds of food", context)
            self.assertIn(phrase, context)
            practice.advance()

        self.assertTrue(practice.is_completed())
        self.assertFalse(practice.has_focus())

    def test_adaptive_session_uses_current_correction_as_focus(self):
        adaptive = AdaptiveSession(duration_minutes=15)
        adaptive.start()
        adaptive.session.set_phase("main_conversation")

        decision = CoachDecision(
            correction=Correction(
                needed=True,
                original="many food",
                better="many kinds of food"
            )
        )

        self.assertTrue(adaptive.start_targeted_practice(decision))
        self.assertEqual(adaptive.targeted_practice.focus.original, "many food")
        self.assertEqual(
            adaptive.targeted_practice.focus.better,
            "many kinds of food"
        )
        self.assertIn("many food", adaptive.targeted_context())
        self.assertIn("correction", adaptive.targeted_context())

    def test_asr_only_decision_does_not_start_practice(self):
        adaptive = AdaptiveSession(duration_minutes=15)
        adaptive.start()

        decision = SimpleNamespace(
            correction=Correction(needed=False),
            asr_uncertainty=[
                SimpleNamespace(
                    heard="food", possible="foods", confidence="low"
                )
            ]
        )

        self.assertFalse(adaptive.start_targeted_practice(decision))
        self.assertFalse(adaptive.targeted_practice.has_focus())

    def test_incomplete_correction_does_not_start_practice(self):
        adaptive = AdaptiveSession(duration_minutes=15)
        adaptive.start()

        decision = CoachDecision(
            correction=Correction(needed=True, original="many food")
        )

        self.assertFalse(adaptive.start_targeted_practice(decision))
        self.assertFalse(adaptive.targeted_practice.has_focus())

    def test_15_minute_plan_has_targeted_phase(self):
        adaptive = AdaptiveSession(duration_minutes=15)
        self.assertIn("targeted_practice", adaptive.available_phases())


if __name__ == "__main__":
    unittest.main()
