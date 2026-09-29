import unittest
from unittest.mock import MagicMock, patch

from app.application.edge_tts_provider import EdgeTTSProvider


class EdgeTTSProviderTests(unittest.TestCase):
    @patch("edge_tts.Communicate")
    def test_synthesize_returns_mp3_audio(self, communicate):
        stream = MagicMock()

        async def chunks():
            yield {"type": "audio", "data": b"mp3-a"}
            yield {"type": "WordBoundary", "data": b"ignored"}
            yield {"type": "audio", "data": b"mp3-b"}

        stream.return_value = chunks()
        communicate.return_value.stream = stream

        result = EdgeTTSProvider(voice="en-US-GuyNeural").synthesize("Hello")

        self.assertEqual(result.audio, b"mp3-amp3-b")
        self.assertEqual(result.content_type, "audio/mpeg")
        communicate.assert_called_once_with("Hello", "en-US-GuyNeural", rate="+0%")

    def test_empty_text_is_rejected_before_provider_call(self):
        with self.assertRaises(ValueError):
            EdgeTTSProvider().synthesize(" ")

    @patch("edge_tts.Communicate")
    def test_empty_provider_result_fails(self, communicate):
        async def chunks():
            if False:
                yield {}

        communicator = communicate.return_value
        communicator.stream = lambda: chunks()
        with self.assertRaises(RuntimeError):
            EdgeTTSProvider().synthesize("Hello")


if __name__ == "__main__":
    unittest.main()
