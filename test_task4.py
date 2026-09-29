import unittest
from unittest.mock import MagicMock, patch

from app.llm import DeepSeekCoach


class ExternalFailureTests(unittest.TestCase):

    def make_coach(self):
        errors = MagicMock()
        errors.get_llm_context.return_value = ""
        naturalness = MagicMock()
        naturalness.get_llm_context.return_value = ""
        performance = MagicMock()
        performance.get_current_difficulty.return_value = "B2"
        performance.adjust_difficulty.return_value = ("B2", "maintain")
        performance.data = {"recent_performance": []}

        with patch("app.llm.ErrorMemory", return_value=errors), \
                patch("app.llm.NaturalnessMemory", return_value=naturalness), \
                patch("app.llm.PerformanceTracker", return_value=performance):
            return DeepSeekCoach()

    def valid_response(self):
        return (
            '{"reply":"Keep going.",'
            '"performance":{"overall":7,"band":"normal"}}'
        )

    def assert_isolated(self, coach, decision):
        self.assertTrue(decision.system_error)
        self.assertEqual(coach.conversation_history, [])
        self.assertEqual(
            coach.performance_tracker.data["recent_performance"],
            []
        )
        self.assertEqual(coach.error_memory.add_error.call_count, 0)
        self.assertEqual(
            coach.naturalness_memory.add_expression.call_count,
            0
        )
        self.assertEqual(
            coach.performance_tracker.adjust_difficulty.call_count,
            0
        )

    def test_timeout_failure_isolated_and_next_turn_works(self):
        coach = self.make_coach()

        with patch.object(
            coach,
            "_request_deepseek",
            return_value=(None, "error")
        ):
            decision = coach.chat("hello")

        self.assert_isolated(coach, decision)

        with patch.object(
            coach,
            "_request_deepseek",
            return_value=(self.valid_response(), "stop")
        ):
            next_decision = coach.chat("hello again")

        self.assertFalse(next_decision.system_error)
        self.assertEqual(len(coach.conversation_history), 2)

    def test_empty_response_isolated(self):
        coach = self.make_coach()
        with patch.object(
            coach,
            "_request_deepseek",
            return_value=("", "stop")
        ):
            decision = coach.chat("hello")
        self.assert_isolated(coach, decision)

    def test_malformed_json_isolated(self):
        coach = self.make_coach()
        with patch.object(
            coach,
            "_request_deepseek",
            return_value=("{not json", "stop")
        ):
            decision = coach.chat("hello")
        self.assert_isolated(coach, decision)

    def test_pydantic_validation_failure_isolated(self):
        coach = self.make_coach()
        response = (
            '{"reply":"bad",'
            '"performance":{"overall":"not-a-number"}}'
        )
        with patch.object(
            coach,
            "_request_deepseek",
            return_value=(response, "stop")
        ):
            decision = coach.chat("hello")
        self.assert_isolated(coach, decision)

    def test_api_error_isolated(self):
        coach = self.make_coach()
        with patch.object(
            coach.client.chat.completions,
            "create",
            side_effect=RuntimeError("API unavailable")
        ):
            decision = coach.chat("hello")
        self.assert_isolated(coach, decision)


if __name__ == "__main__":
    unittest.main()
