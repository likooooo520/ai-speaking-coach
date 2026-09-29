import unittest

from app.memory import ErrorMemory
from app.naturalness import NaturalnessMemory
from app.adaptive_session import AdaptiveSession
from app.routing import SessionRouter
from app.session_plan import SessionPlan
from app.targeted_practice import TargetedPracticeManager


class RelevanceTests(unittest.TestCase):

    def make_error_memory(self, count, original="many food"):
        memory = ErrorMemory.__new__(ErrorMemory)
        memory.data = {
            "errors": [{
                "original": original,
                "better": "many kinds of food",
                "category": "grammar",
                "severity": "medium",
                "count": count
            }]
        }
        return memory

    def make_naturalness_memory(self, frequency):
        memory = NaturalnessMemory.__new__(NaturalnessMemory)
        memory.data = {
            "expressions": [{
                "original": "I think",
                "alternatives": ["I'd say"],
                "category": "expression",
                "frequency": frequency,
                "status": "learning"
            }]
        }
        return memory

    def test_matching_error_frequency_triggers_targeted_practice(self):
        memory = self.make_error_memory(3)
        matched = memory.match_current_error("  MANY   FOOD ")
        self.assertIsNotNone(matched)
        self.assertEqual(memory.get_error_frequency("many food"), 3)

        decision = SessionRouter().decide(
            current_phase="main_conversation",
            performance_band="normal",
            current_error="many food",
            matched_historical_error=matched,
            current_error_frequency=3,
            current_error_detected=True,
            remaining_minutes=15
        )
        self.assertEqual(decision.target_phase, "targeted_practice")

    def test_unrelated_error_does_not_trigger(self):
        memory = self.make_error_memory(3)
        matched = memory.match_current_error("wrong tense")
        self.assertIsNone(matched)

        decision = SessionRouter().decide(
            current_phase="main_conversation",
            performance_band="normal",
            current_error="wrong tense",
            matched_historical_error=matched,
            current_error_frequency=0,
            current_error_detected=True,
            remaining_minutes=15
        )
        self.assertIsNone(decision.target_phase)

    def test_naturalness_frequency_threshold(self):
        low = self.make_naturalness_memory(1)
        self.assertIsNotNone(low.match_current_expression(" I  think "))
        decision = SessionRouter().decide(
            current_phase="main_conversation",
            performance_band="normal",
            current_naturalness_detected=True,
            matched_historical_naturalness=low.match_current_expression("I think"),
            current_naturalness_frequency=1,
            remaining_minutes=15
        )
        self.assertIsNone(decision.target_phase)

        high = self.make_naturalness_memory(3)
        decision = SessionRouter().decide(
            current_phase="main_conversation",
            performance_band="normal",
            current_naturalness_detected=True,
            matched_historical_naturalness=high.match_current_expression("I think"),
            current_naturalness_frequency=3,
            remaining_minutes=15
        )
        self.assertEqual(decision.target_phase, "targeted_practice")

    def test_naturalness_focus(self):
        practice = TargetedPracticeManager()
        practice.start(
            original="I think",
            alternatives=["I'd say", "Personally"],
            explanation="Use a more varied spoken expression.",
            focus_type="naturalness"
        )
        context = practice.get_context()
        self.assertIn("Type: naturalness", context)
        self.assertIn("I'd say", context)

    def test_deep_discussion_has_explicit_routing(self):
        decision = SessionRouter().decide(
            current_phase="deep_discussion",
            performance_band="weak",
            remaining_minutes=20
        )
        self.assertEqual(decision.target_phase, "main_conversation")

    def test_missing_target_phase_is_safe(self):
        adaptive = AdaptiveSession(duration_minutes=30)
        adaptive.start()
        adaptive.session.set_phase("main_conversation")
        adaptive.available_phases = lambda: [
            "warmup", "main_conversation", "review"
        ]
        decision = adaptive.route(
            performance_band="normal",
            current_error_detected=True,
            matched_historical_error={"count": 3},
            current_error_frequency=3
        )
        self.assertIsNone(decision.target_phase)
        self.assertEqual(decision.action, "continue")

    def test_all_requested_plans_have_exact_duration(self):
        for duration in (15, 30, 45, 60, 75):
            self.assertEqual(SessionPlan(duration).total_minutes(), duration)


if __name__ == "__main__":
    unittest.main()
