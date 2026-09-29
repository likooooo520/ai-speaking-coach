import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.application.audio_converter import AudioConversionError
from app.web import Handler


def multipart_audio(payload=b"browser audio"):
    boundary = "----SpeakingCoachBoundary"
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="audio"; filename="recording.webm"\r\n'
        "Content-Type: audio/webm\r\n\r\n"
    ).encode() + payload + f"\r\n--{boundary}--\r\n".encode()
    return body, f"multipart/form-data; boundary={boundary}"


class WebAudioToTurnTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.session = MagicMock()
        self.session.speak.return_value = {"turn": 1, "user": "hello", "action": "continue"}
        self.handler = Handler.__new__(Handler)
        self.responses = []
        self.handler._json = MagicMock(side_effect=lambda data, status=200: self.responses.append((data, status)))

    def tearDown(self):
        self.temp_dir.cleanup()

    def upload(self):
        body, content_type = multipart_audio()
        self.handler.headers = {"Content-Length": str(len(body)), "Content-Type": content_type}
        self.handler.rfile = io.BytesIO(body)
        self.handler._upload_audio("session-1")

    @patch("app.web.AUDIO_ROOT")
    @patch("app.web.transcribe_uploaded_audio", return_value="  hello from audio  ")
    @patch("app.web.STATE.get")
    def test_transcription_creates_one_shared_turn(self, get_session, transcribe, audio_root):
        audio_root.__truediv__.side_effect = lambda part: Path(self.temp_dir.name) / part
        get_session.return_value = self.session

        self.upload()

        self.session.speak.assert_called_once_with("  hello from audio  ")
        data, status = self.responses[-1]
        self.assertEqual(status, 201)
        self.assertEqual(data["transcription"], "  hello from audio  ")
        self.assertEqual(data["turn"], self.session.speak.return_value)
        transcribe.assert_called_once()

    @patch("app.web.AUDIO_ROOT")
    @patch("app.web.transcribe_uploaded_audio")
    @patch("app.web.STATE.get")
    def test_transcription_failures_do_not_create_turn(self, get_session, transcribe, audio_root):
        audio_root.__truediv__.side_effect = lambda part: Path(self.temp_dir.name) / part
        get_session.return_value = self.session

        for failure in (AudioConversionError("failed"), RuntimeError("Whisper unavailable"), ValueError("transcription is empty")):
            with self.subTest(failure=failure):
                transcribe.side_effect = failure
                self.responses.clear()
                self.upload()
                self.assertNotEqual(self.responses[-1][1], 201)
        self.session.speak.assert_not_called()

    @patch("app.web.AUDIO_ROOT")
    @patch("app.web.transcribe_uploaded_audio", return_value="hello")
    @patch("app.web.STATE.get")
    def test_turn_pipeline_error_keeps_existing_safe_error_response(self, get_session, transcribe, audio_root):
        audio_root.__truediv__.side_effect = lambda part: Path(self.temp_dir.name) / part
        get_session.return_value = self.session
        self.session.speak.side_effect = RuntimeError("coach unavailable")

        self.upload()

        self.session.speak.assert_called_once_with("hello")
        self.assertEqual(self.responses[-1], ({"error": "Something went wrong. Let's try that again."}, 502))

    def test_audio_client_does_not_post_transcription_to_turn_endpoint(self):
        source = (Path(__file__).resolve().parents[2] / "web" / "assets" / "app.js").read_text(encoding="utf-8")
        submit_function = source[source.index("async function submitUtterance"):source.index("function wait")]
        self.assertIn("messages.push(data.turn)", submit_function)
        self.assertNotIn("/turn", submit_function)

    @patch("app.web.STATE.get")
    def test_text_turn_still_uses_web_session_speak(self, get_session):
        get_session.return_value = self.session
        self.handler.path = "/api/session/session-1/turn"
        body = b'{"text": "hello from text"}'
        self.handler.headers = {"Content-Length": str(len(body))}
        self.handler.rfile = io.BytesIO(body)

        self.handler.do_POST()

        self.session.speak.assert_called_once_with("hello from text")
        self.assertEqual(self.responses[-1], (self.session.speak.return_value, 200))


if __name__ == "__main__":
    unittest.main()
