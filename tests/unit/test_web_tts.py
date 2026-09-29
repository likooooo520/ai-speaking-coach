import io
import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.application.tts_provider import TTSResult
from app.web import Handler, WebSession, edge_tts_rate


class WebTTSTests(unittest.TestCase):
    def setUp(self):
        self.handler = Handler.__new__(Handler)
        self.handler.path = "/api/session/session-1/tts"
        self.handler.response = io.BytesIO()
        self.handler.status = None
        self.handler.headers_sent = {}
        self.handler.send_response = lambda status: setattr(self.handler, "status", status)
        self.handler.send_header = lambda name, value: self.handler.headers_sent.__setitem__(name, value)
        self.handler.end_headers = lambda: None
        self.handler.wfile = self.handler.response

    def post_tts(self, text="hello"):
        body = json.dumps({"text": text}).encode()
        self.handler.headers = {"Content-Length": str(len(body))}
        self.handler.rfile = io.BytesIO(body)
        self.handler.do_POST()

    @patch("app.web.STATE.get")
    @patch("app.web.TTS_PROVIDER")
    def test_success_returns_binary_audio(self, provider, get_session):
        get_session.return_value = MagicMock(turns=[])
        provider.synthesize.return_value = TTSResult(b"wav-data", "audio/wav")

        self.post_tts()

        self.assertEqual(self.handler.status, 200)
        self.assertEqual(self.handler.response.getvalue(), b"wav-data")
        self.assertEqual(self.handler.headers_sent["Content-Type"], "audio/wav")
        self.assertEqual(provider.synthesize.call_args.args, ("hello",))
        get_session.return_value.speak.assert_not_called()

    @patch("app.web.STATE.get")
    @patch("app.web.TTS_PROVIDER")
    def test_tts_does_not_modify_session_or_call_agent_or_stt(self, provider, get_session):
        session = MagicMock(turns=[{"turn": 1}])
        get_session.return_value = session
        provider.synthesize.return_value = TTSResult(b"audio", "audio/mpeg")

        self.post_tts()

        self.assertEqual(session.turns, [{"turn": 1}])
        session.speak.assert_not_called()

    @patch("app.web.STATE.get")
    @patch("app.web.TTS_PROVIDER")
    def test_provider_failure_returns_safe_error(self, provider, get_session):
        get_session.return_value = MagicMock()
        provider.synthesize.side_effect = RuntimeError("provider down")

        self.post_tts()

        self.assertEqual(self.handler.status, 503)
        self.assertEqual(json.loads(self.handler.response.getvalue()), {"error": "TTS synthesis failed"})

    @patch("app.web.STATE.get")
    @patch("app.web.TTS_PROVIDER")
    def test_empty_text_is_rejected(self, provider, get_session):
        get_session.return_value = MagicMock()

        self.post_tts(" ")

        self.assertEqual(self.handler.status, 400)
        provider.synthesize.assert_not_called()

    @patch("app.web.STATE.get")
    def test_missing_provider_is_service_error(self, get_session):
        get_session.return_value = MagicMock()
        with patch("app.web.TTS_PROVIDER", None):
            self.post_tts()
        self.assertEqual(self.handler.status, 503)

    def test_audio_contract_and_frontend_playback_contract(self):
        source = (Path(__file__).resolve().parents[2] / "web" / "assets" / "app.js").read_text(encoding="utf-8")
        self.assertIn("playTurnAudio(data.turn.reply,observation)", source)
        self.assertIn("/tts", source)
        self.assertIn("playbackAudio.addEventListener('ended'", source)
        self.assertIn("URL.revokeObjectURL", source)
        self.assertNotIn("fetch(`/api/session/${sessionId}/turn`", source[source.index("async function submitUtterance"):source.index("function wait")])

    def test_session_keeps_valid_voice_preferences_for_tts(self):
        session = WebSession({
            "voice_name": "en-US-AriaNeural",
            "speaking_rate": 0.8,
            "auto_tts": False,
            "volume": 0.5,
            "difficulty": "C1",
            "duration": 60,
            "english_only": True,
            "feedback_intensity": "strong",
        })
        try:
            self.assertEqual(session.voice_name, "en-US-AriaNeural")
            self.assertEqual(session.speaking_rate, 0.8)
            self.assertEqual(session.tts_rate, "-20%")
            self.assertFalse(session.auto_tts)
            self.assertEqual(session.volume, 0.5)
            self.assertEqual(session.difficulty, "C1")
            self.assertEqual(session.duration, 60)
            self.assertTrue(session.english_only)
            self.assertEqual(session.feedback_intensity, "strong")
        finally:
            session._analysis_executor.shutdown(wait=True)

    def test_session_keeps_free_duration_and_empty_topic_as_none(self):
        session = WebSession({
            "mode": "teacher",
            "duration": None,
            "topic": "",
        })
        try:
            self.assertIsNone(session.duration)
            self.assertIsNone(session.topic)
            self.assertEqual(session.mode, "teacher")
        finally:
            session._analysis_executor.shutdown(wait=True)

    def test_edge_rate_conversion_uses_supported_preference_values(self):
        self.assertEqual(edge_tts_rate(1.0), "+0%")
        self.assertEqual(edge_tts_rate(0.8), "-20%")
        self.assertEqual(edge_tts_rate(1.2), "+20%")


if __name__ == "__main__":
    unittest.main()
