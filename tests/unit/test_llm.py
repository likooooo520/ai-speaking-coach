import io
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.llm import DeepSeekCoach


class DeepSeekRequestTests(unittest.TestCase):

    def coach_with_response(self, response):
        coach = DeepSeekCoach.__new__(DeepSeekCoach)
        coach.client = MagicMock()
        coach.client.chat.completions.create.return_value = response
        return coach

    @staticmethod
    def response(content, finish_reason="stop", reasoning_content=None,
                 tool_calls=None):
        message = SimpleNamespace(
            content=content,
            reasoning_content=reasoning_content,
            tool_calls=tool_calls,
        )
        choice = SimpleNamespace(
            message=message,
            finish_reason=finish_reason,
        )
        return SimpleNamespace(
            model="deepseek-v4-flash",
            choices=[choice],
            model_dump=lambda: {"usage": {"total_tokens": 12}},
        )

    def test_normal_content_is_returned_without_empty_response_diagnostic(self):
        coach = self.coach_with_response(self.response('{"reply": "Hello"}'))
        output = io.StringIO()

        with redirect_stdout(output):
            content, finish_reason = coach._request_deepseek([])

        self.assertEqual(content, '{"reply": "Hello"}')
        self.assertEqual(finish_reason, "stop")
        self.assertNotIn("empty response diagnostic", output.getvalue())

    def test_none_content_returns_none_and_logs_safe_response_fields(self):
        coach = self.coach_with_response(self.response(None))
        output = io.StringIO()

        with redirect_stdout(output):
            content, finish_reason = coach._request_deepseek([])

        self.assertIsNone(content)
        self.assertEqual(finish_reason, "stop")
        diagnostic = output.getvalue()
        self.assertIn("DeepSeek empty response diagnostic", diagnostic)
        self.assertIn('"content_is_empty": true', diagnostic)
        self.assertIn('"choices_count": 1', diagnostic)

    def test_sdk_exception_logs_type_status_message_and_request_id(self):
        class ApiError(Exception):
            status_code = 429
            request_id = "request-123"

        coach = DeepSeekCoach.__new__(DeepSeekCoach)
        coach.client = MagicMock()
        coach.client.chat.completions.create.side_effect = ApiError("rate limited")
        output = io.StringIO()

        with redirect_stdout(output):
            content, finish_reason = coach._request_deepseek([])

        self.assertIsNone(content)
        self.assertEqual(finish_reason, "error")
        diagnostic = output.getvalue()
        self.assertIn('"exception_type": "ApiError"', diagnostic)
        self.assertIn('"http_status": 429', diagnostic)
        self.assertIn('"request_id": "request-123"', diagnostic)

    def test_non_stop_finish_reason_with_content_remains_usable(self):
        coach = self.coach_with_response(
            self.response('{"reply": "Partial"}', finish_reason="length")
        )

        content, finish_reason = coach._request_deepseek([])

        self.assertEqual(content, '{"reply": "Partial"}')
        self.assertEqual(finish_reason, "length")

    def test_reasoning_content_with_empty_content_is_logged_but_not_used(self):
        coach = self.coach_with_response(
            self.response(None, reasoning_content="internal reasoning")
        )
        output = io.StringIO()

        with redirect_stdout(output):
            content, _ = coach._request_deepseek([])

        self.assertIsNone(content)
        self.assertIn('"reasoning_content_present": true', output.getvalue())


if __name__ == "__main__":
    unittest.main()
