import unittest
from types import SimpleNamespace

from app.application.targeted_practice_service import TargetedPracticeService


class FakeLibrary:
    def find_relevant(self, *_args, **_kwargs):
        return [{"expression": "I'm really into...", "meaning": "很喜欢", "examples": ["I'm really into tea."]}]


class TargetedPracticeTests(unittest.TestCase):
    def service(self):
        return TargetedPracticeService(FakeLibrary())

    def test_naturalness_creates_candidate_but_system_error_does_not(self):
        service = self.service()
        result = SimpleNamespace(naturalness=SimpleNamespace(detected=True, alternatives=["I really like it."], explanation="Natural phrasing"))
        candidate = service.candidate_for(result, "I very like it", "food", "B2")
        self.assertEqual(candidate["type"], "naturalness")
        self.assertIsNone(service.candidate_for(SimpleNamespace(naturalness=SimpleNamespace(detected=False)), "hello", "food", "B2"))

    def test_four_steps_reach_result_and_skip_exits(self):
        service = self.service()
        service.offer(service.expression_candidate("I really like food", "food", "B2"))
        self.assertTrue(service.start())
        for step in ("correction", "repetition", "variation", "free_use"):
            self.assertEqual(service.state["step"], step)
            outcome = service.submit("I really like food and tea")
        self.assertFalse(service.state["active"])
        self.assertEqual(outcome["step"], "result")
        service.offer(service.expression_candidate("I really like food", "food", "B2"))
        service.skip()
        self.assertFalse(service.state["active"])

    def test_retry_and_session_limit(self):
        service = self.service()
        for _ in range(3):
            service.offer(service.expression_candidate("I really like food", "food", "B2"))
            service.skip()
        self.assertIsNone(service.offer(service.expression_candidate("I really like food", "food", "B2")))


if __name__ == "__main__":
    unittest.main()
