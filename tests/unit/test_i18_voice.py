import unittest
from unittest.mock import patch

from app.web import WebSession, edge_tts_rate


class I18VoiceTests(unittest.TestCase):
    def session(self, rate=1.0):
        session = WebSession({"speaking_rate": rate, "auto_tts": False})
        self.addCleanup(session._analysis_executor.shutdown, wait=True)
        return session

    def test_session_rate_starts_from_settings_and_maps_to_edge(self):
        session = self.session(.8)
        self.assertEqual(session.session_voice_rate, .8)
        self.assertEqual(session.tts_rate, "-20%")
        self.assertEqual(edge_tts_rate(.7), "-30%")

    def test_too_fast_decreases_only_session_rate(self):
        session = self.session(1.0)
        session._apply_voice_feedback("You're speaking too fast")
        self.assertEqual(session.session_voice_rate, .9)
        self.assertEqual(session.tts_rate, "-10%")
        self.assertEqual(session.speaking_rate, 1.0)

    def test_rate_clamps_at_both_limits(self):
        slow = self.session(.8)
        for _ in range(5):
            slow._apply_voice_feedback("please slow down")
        self.assertEqual(slow.session_voice_rate, .7)

        fast = self.session(1.1)
        for _ in range(5):
            fast._apply_voice_feedback("speak a little faster")
        self.assertEqual(fast.session_voice_rate, 1.2)

    def test_normal_conversation_does_not_change_rate(self):
        session = self.session(1.0)
        self.assertIsNone(session._apply_voice_feedback("I usually drink it cold."))
        self.assertEqual(session.session_voice_rate, 1.0)

    def test_clarification_and_ending_are_prompt_hints_without_extra_llm(self):
        self.assertIn("brief, simple explanation", WebSession._conversation_hint("I don't understand", None))
        self.assertIn("ending the session", WebSession._conversation_hint("Let's stop", None))


if __name__ == "__main__":
    unittest.main()
