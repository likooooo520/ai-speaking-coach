import unittest
from unittest.mock import MagicMock, patch

from app.llm import DeepSeekCoach


class Task1FlowTests(unittest.TestCase):

    def make_coach(self):
        error_memory = MagicMock()
        error_memory.get_llm_context.return_value = ""
        error_memory.get_all_errors.return_value = []

        naturalness_memory = MagicMock()
        naturalness_memory.get_llm_context.return_value = ""
        naturalness_memory.get_all_expressions.return_value = []

        performance_tracker = MagicMock()
        performance_tracker.get_current_difficulty.return_value = "B2"
        performance_tracker.adjust_difficulty.return_value = (
            "B2",
            "maintain"
        )
        performance_tracker.data = {"recent_performance": []}

        with patch(
            "app.llm.ErrorMemory",
            return_value=error_memory
        ), patch(
            "app.llm.NaturalnessMemory",
            return_value=naturalness_memory
        ), patch(
            "app.llm.PerformanceTracker",
            return_value=performance_tracker
        ):
            return DeepSeekCoach()

    def test_invalid_json_is_system_error(self):
        coach = self.make_coach()

        with patch.object(
            coach,
            "_request_deepseek",
            return_value=("not json", "stop")
        ):
            decision = coach.chat("hello")

        self.assertTrue(decision.system_error)
        self.assertEqual(
            coach.performance_tracker.data["recent_performance"],
            []
        )
        self.assertEqual(coach.conversation_history, [])

    def test_valid_decision_is_not_system_error(self):
        coach = self.make_coach()

        with patch.object(
            coach,
            "_request_deepseek",
            return_value=(
                '{"reply":"Keep going."}',
                "stop"
            )
        ):
            result = coach.chat("hello")

        self.assertFalse(result.system_error)
        self.assertEqual(len(coach.conversation_history), 2)


if __name__ == "__main__":
    unittest.main()
