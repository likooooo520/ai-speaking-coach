import unittest
from unittest.mock import MagicMock, patch

from app.llm import DeepSeekCoach


class ErrorNaturalnessTests(unittest.TestCase):

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

    def decision_json(self, naturalness=False):
        return (
            '{"reply":"Okay",'
            '"correction":{"needed":false},'
            '"naturalness":{"detected":%s,"original":"I think",'
            '"alternatives":["I\'d say"]},'
            '"performance":{"overall":7,"band":"normal"}}'
            % str(naturalness).lower()
        )

    def test_many_food_is_error_and_many_foods_is_not(self):
        coach = self.make_coach()

        with patch.object(
            coach,
            "_request_deepseek",
            return_value=(self.decision_json(), "stop")
        ):
            error = coach.chat("I like many food.")

        self.assertTrue(error.correction.needed)
        self.assertEqual(error.correction.better, "many kinds of food")

        with patch.object(
            coach,
            "_request_deepseek",
            return_value=(self.decision_json(), "stop")
        ):
            acceptable = coach.chat("I like many foods.")

        self.assertFalse(acceptable.correction.needed)

    def test_naturalness_requires_repetition(self):
        coach = self.make_coach()
        response = self.decision_json(naturalness=True)

        with patch.object(
            coach,
            "_request_deepseek",
            return_value=(response, "stop")
        ):
            first = coach.chat("I think Chinese food is very good.")
            second = coach.chat("I think Chinese food is very good.")
            third = coach.chat("I think Chinese food is very good.")

        self.assertFalse(first.naturalness.detected)
        self.assertFalse(second.naturalness.detected)
        self.assertTrue(third.naturalness.detected)

    def test_asr_uncertainty_does_not_create_error(self):
        coach = self.make_coach()
        response = (
            '{"reply":"Could you repeat that?",'
            '"correction":{"needed":true,"original":"many food",'
            '"better":"many kinds of food"},'
            '"asr_uncertainty":[{"heard":"food","possible":"foods",'
            '"confidence":"low"}],'
            '"performance":{"overall":7,"band":"normal"}}'
        )

        with patch.object(
            coach,
            "_request_deepseek",
            return_value=(response, "stop")
        ):
            decision = coach.chat("I like many food.")

        self.assertFalse(decision.correction.needed)
        self.assertEqual(coach.error_memory.add_error.call_count, 0)


if __name__ == "__main__":
    unittest.main()
