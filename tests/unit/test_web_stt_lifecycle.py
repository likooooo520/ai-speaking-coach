import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import app.web as web
from app.web import transcribe_uploaded_audio


class WebSttLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.filename = Path(self.temp_dir.name) / "audio.webm"
        self.filename.write_bytes(b"audio")
        self.converter = MagicMock()
        self.converter.convert_to_wav.side_effect = self.create_wav
        self.original_stt = web._shared_stt
        web._shared_stt = None

    def tearDown(self):
        web._shared_stt = self.original_stt
        self.temp_dir.cleanup()

    def create_wav(self, source, target):
        Path(target).write_bytes(b"wav")

    def test_two_transcriptions_create_one_stt_and_reuse_it(self):
        stt = MagicMock()
        stt.transcribe.side_effect = ["first", "second"]
        factory = MagicMock(return_value=stt)

        with patch.object(web, "_speech_to_text_factory", return_value=factory):
            self.assertEqual(transcribe_uploaded_audio(self.filename, converter=self.converter), "first")
            self.assertEqual(transcribe_uploaded_audio(self.filename, converter=self.converter), "second")

        factory.assert_called_once_with()
        stt.transcribe.assert_has_calls([
            unittest.mock.call(unittest.mock.ANY),
            unittest.mock.call(unittest.mock.ANY),
        ])
        self.assertEqual(stt.transcribe.call_count, 2)

    def test_initialization_failure_is_not_cached(self):
        stt = MagicMock()
        factory = MagicMock(side_effect=[RuntimeError("load failed"), stt])
        stt.transcribe.return_value = "recovered"

        with patch.object(web, "_speech_to_text_factory", return_value=factory):
            with self.assertRaisesRegex(RuntimeError, "load failed"):
                transcribe_uploaded_audio(self.filename, converter=self.converter)
            self.assertIsNone(web._shared_stt)
            self.assertEqual(transcribe_uploaded_audio(self.filename, converter=self.converter), "recovered")

        self.assertEqual(factory.call_count, 2)
        self.assertIs(web._shared_stt, stt)

    def test_concurrent_first_initialization_creates_one_stt(self):
        stt = MagicMock()
        stt.transcribe.return_value = "hello"
        factory = MagicMock(return_value=stt)
        results = []

        with patch.object(web, "_speech_to_text_factory", return_value=factory):
            threads = [threading.Thread(
                target=lambda: results.append(transcribe_uploaded_audio(self.filename, converter=self.converter))
            ) for _ in range(4)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

        self.assertEqual(results, ["hello"] * 4)
        factory.assert_called_once_with()
        self.assertEqual(stt.transcribe.call_count, 4)

    def test_concurrent_transcription_calls_are_serialized(self):
        active = 0
        maximum = 0
        guard = threading.Lock()
        stt = MagicMock()

        def transcribe(_filename):
            nonlocal active, maximum
            with guard:
                active += 1
                maximum = max(maximum, active)
            time.sleep(0.02)
            with guard:
                active -= 1
            return "hello"

        stt.transcribe.side_effect = transcribe
        web._shared_stt = stt
        threads = [threading.Thread(
            target=transcribe_uploaded_audio, args=(self.filename,), kwargs={"converter": self.converter}
        ) for _ in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(maximum, 1)
        self.assertEqual(stt.transcribe.call_count, 4)

    def test_temp_wav_is_removed_after_shared_stt_success_and_failure(self):
        stt = MagicMock()
        stt.transcribe.side_effect = ["hello", RuntimeError("stt failed")]
        web._shared_stt = stt

        transcribe_uploaded_audio(self.filename, converter=self.converter)
        wav_path = self.converter.convert_to_wav.call_args_list[0].args[1]
        self.assertFalse(Path(wav_path).exists())

        with self.assertRaisesRegex(RuntimeError, "stt failed"):
            transcribe_uploaded_audio(self.filename, converter=self.converter)
        wav_path = self.converter.convert_to_wav.call_args_list[1].args[1]
        self.assertFalse(Path(wav_path).exists())

    def test_custom_factory_contract_remains_per_call_injected(self):
        stt = MagicMock()
        stt.transcribe.return_value = "hello"
        factory = MagicMock(return_value=stt)

        self.assertEqual(transcribe_uploaded_audio(self.filename, factory, self.converter), "hello")
        factory.assert_called_once_with()
        self.assertIsNone(web._shared_stt)


if __name__ == "__main__":
    unittest.main()
