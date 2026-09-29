import unittest

from app.application.tts_provider import TTSProvider, TTSResult


class TTSProviderTests(unittest.TestCase):
    def test_result_contains_audio_and_content_type(self):
        result = TTSResult(audio=b"audio", content_type="audio/wav")
        self.assertEqual(result.audio, b"audio")
        self.assertEqual(result.content_type, "audio/wav")

    def test_base_provider_is_abstract_by_contract(self):
        with self.assertRaises(NotImplementedError):
            TTSProvider().synthesize("hello")


if __name__ == "__main__":
    unittest.main()
