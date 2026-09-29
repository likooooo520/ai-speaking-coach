import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.llm import ConversationCoach
from app.web import WebSession


class ConversationCoachTests(unittest.TestCase):
    def setUp(self):
        self.coach = ConversationCoach.__new__(ConversationCoach)
        self.coach.client = MagicMock()
        self.coach.conversation_history = []
        self.coach.naturalness_observations = {}
        self.coach.session_context = {"topic": "work"}

    @staticmethod
    def response(content):
        message = SimpleNamespace(content=content, reasoning_content=None, tool_calls=None)
        choice = SimpleNamespace(message=message, finish_reason="stop")
        return SimpleNamespace(
            model="deepseek-v4-flash",
            choices=[choice],
            model_dump=lambda: {"usage": {"total_tokens": 12}},
        )

    def test_normal_chat_returns_nonempty_reply_without_json_output(self):
        self.coach.client.chat.completions.create.return_value = self.response(
            '{"reply":"Nice to meet you, Alex. What do you enjoy doing after work?",'
            '"correction":{"needed":false,"original":null,"better":null,"explanation":null},'
            '"naturalness":{"detected":false,"original":null,"alternatives":[],"explanation":null},'
            '"asr_uncertainty":[]}'
        )

        decision = self.coach.chat("Hello, my name is Alex.")

        self.assertFalse(decision.system_error)
        self.assertTrue(decision.reply)
        request = self.coach.client.chat.completions.create.call_args.kwargs
        self.assertEqual(request["response_format"], {"type": "json_object"})
        self.assertEqual(request["extra_body"], {"thinking": {"type": "disabled"}})

    def test_second_turn_includes_successful_history(self):
        self.coach.client.chat.completions.create.side_effect = [
            self.response('{"reply":"What kind of company do you work for?"}'),
            self.response('{"reply":"That can be stressful. Is it harder in meetings?"}'),
        ]

        self.coach.chat("I work at a company.")
        self.coach.chat("I usually feel nervous at work.")

        messages = self.coach.client.chat.completions.create.call_args.kwargs["messages"]
        self.assertIn({"role": "user", "content": "I work at a company."}, messages)
        self.assertIn({"role": "assistant", "content": "What kind of company do you work for?"}, messages)

    def test_empty_content_retries_once_and_uses_second_response(self):
        self.coach.client.chat.completions.create.side_effect = [
            self.response(None),
            self.response('{"reply":"That sounds interesting. Tell me more."}'),
        ]

        decision = self.coach.chat("I work at a company.")

        self.assertFalse(decision.system_error)
        self.assertEqual(self.coach.client.chat.completions.create.call_count, 2)
        self.assertEqual(decision.reply, "That sounds interesting. Tell me more.")

    def test_two_empty_responses_do_not_write_history(self):
        self.coach.client.chat.completions.create.side_effect = [self.response(None), self.response(None)]

        decision = self.coach.chat("I work at a company.")

        self.assertTrue(decision.system_error)
        self.assertEqual(self.coach.client.chat.completions.create.call_count, 2)
        self.assertEqual(self.coach.conversation_history, [])

    def test_api_error_does_not_retry(self):
        self.coach.client.chat.completions.create.side_effect = RuntimeError("network")

        decision = self.coach.chat("I work at a company.")

        self.assertTrue(decision.system_error)
        self.assertEqual(self.coach.client.chat.completions.create.call_count, 1)

    def test_json_parse_error_does_not_retry(self):
        self.coach.client.chat.completions.create.return_value = self.response("not json")

        decision = self.coach.chat("I work at a company.")

        self.assertTrue(decision.system_error)
        self.assertEqual(self.coach.client.chat.completions.create.call_count, 1)

    def test_web_session_uses_conversation_coach(self):
        with patch("app.web.ConversationCoach") as coach_type:
            session = WebSession({"topic": "work"})

        self.assertIs(session.coach, coach_type.return_value)

    def test_coaching_context_is_injected_as_plain_teaching_guidance(self):
        self.coach.set_session_context(
            coaching_context="If it fits naturally, offer one short helpful expression suggestion."
        )

        prompt = self.coach._conversation_prompt()

        self.assertIn("Teaching context:", prompt)
        self.assertIn("one short helpful expression suggestion", prompt)
        for internal_name in ("Observation", "Evidence", "Priority", "Intervention", "ActionResult"):
            self.assertNotIn(internal_name, prompt)

    def test_no_coaching_context_keeps_conversation_prompt_compatible(self):
        prompt = self.coach._conversation_prompt()

        self.assertNotIn("Teaching context:", prompt)

    def test_session_mode_and_feedback_intensity_are_separate(self):
        coach = ConversationCoach()
        coach.set_session_context(
            coach_mode="business_coach", feedback_intensity="strong"
        )

        prompt = coach._system_prompt()

        self.assertIn("Coach mode:\nbusiness_coach", prompt)
        self.assertIn("Feedback intensity:\nstrong", prompt)

    def test_teacher_response_parses_a_current_turn_naturalness_signal(self):
        self.coach.set_session_context(coach_mode="teacher")
        self.coach.client.chat.completions.create.return_value = self.response(
            '{"reply":"Spicy sauce is a great match for burgers.",'
            '"correction":{"needed":false,"original":null,"better":null,"explanation":null},'
            '"naturalness":{"detected":true,"original":"I\'m really like",'
            '"alternatives":["I really like"],"explanation":"Use I really like, without am."},'
            '"asr_uncertainty":[]}'
        )

        decision = self.coach.chat("I'm really like spicy sauce.")

        self.assertFalse(decision.system_error)
        self.assertTrue(decision.naturalness.detected)
        self.assertEqual(decision.naturalness.original, "I'm really like")

    def test_foreign_friend_keeps_private_signal_out_of_reply(self):
        self.coach.set_session_context(coach_mode="foreign_friend")
        self.coach.client.chat.completions.create.return_value = self.response(
            '{"reply":"Spicy sauce makes burgers more fun.",'
            '"naturalness":{"detected":true,"original":"very like",'
            '"alternatives":["really like"],"explanation":"Natural phrasing."},'
            '"asr_uncertainty":[]}'
        )

        decision = self.coach.chat("I very like spicy sauce.")

        self.assertEqual(decision.reply, "Spicy sauce makes burgers more fun.")
        self.assertFalse(decision.naturalness.detected)

    def test_natural_chat_prompt_disables_proactive_teaching(self):
        self.coach.set_session_context(coach_mode="foreign_friend")

        prompt = self.coach._conversation_prompt()

        self.assertIn("English-speaking friend, not their teacher", prompt)
        self.assertIn("do not volunteer corrections", prompt)
        self.assertIn("do not force a question every turn", prompt)

    def test_teacher_prompt_keeps_teaching_light_and_optional(self):
        self.coach.set_session_context(
            coach_mode="teacher",
            coaching_context="Offer one useful expression when it fits.",
        )

        prompt = self.coach._conversation_prompt()

        self.assertIn("supportive English coach", prompt)
        self.assertIn("at most one short, practical improvement", prompt)
        self.assertIn("Teaching context:", prompt)

    def test_professional_prompt_uses_role_context_without_friend_style(self):
        self.coach.set_session_context(
            coach_mode="business_coach",
            session_difficulty="C1",
            professional_context="Act as the interviewer.",
        )

        prompt = self.coach._conversation_prompt()

        self.assertIn("professional conversation partner", prompt)
        self.assertIn("Professional context: Act as the interviewer.", prompt)
        self.assertIn("Session target level: C1", prompt)
        self.assertNotIn("English-speaking friend, not their teacher", prompt)


if __name__ == "__main__":
    unittest.main()
