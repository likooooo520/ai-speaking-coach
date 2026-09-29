import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from app.web import transcribe_uploaded_audio


class WebAudioSttTests(unittest.TestCase):
    def setUp(self):
        self.filename = Path(tempfile.mkdtemp()) / "audio.webm"
        self.filename.write_bytes(b"audio")

    def test_webm_converter_wav_stt_chain_and_cleanup(self):
        converter = MagicMock()
        stt = MagicMock()
        stt.transcribe.return_value = "  hello from the browser  "
        factory = MagicMock(return_value=stt)
        result = transcribe_uploaded_audio(self.filename, factory, converter)
        self.assertEqual(result, "hello from the browser")
        converter.convert_to_wav.assert_called_once()
        wav_path = converter.convert_to_wav.call_args.args[1]
        stt.transcribe.assert_called_once_with(str(wav_path))
        self.assertFalse(wav_path.exists())
        self.assertTrue(self.filename.exists())

    def test_empty_transcription_is_rejected(self):
        stt = MagicMock()
        stt.transcribe.return_value = "  "
        with self.assertRaisesRegex(ValueError, "transcription is empty"):
            transcribe_uploaded_audio(self.filename, lambda: stt, MagicMock())

    def test_whisper_failure_is_propagated_for_web_boundary(self):
        stt = MagicMock()
        stt.transcribe.side_effect = RuntimeError("CUDA unavailable")
        with self.assertRaisesRegex(RuntimeError, "CUDA unavailable"):
            transcribe_uploaded_audio(self.filename, lambda: stt, MagicMock())

    def test_empty_audio_file_is_detected_before_stt(self):
        empty = self.filename.with_name("empty.webm")
        empty.write_bytes(b"")
        self.assertEqual(empty.read_bytes(), b"")

    def test_conversion_failure_does_not_call_stt(self):
        converter = MagicMock()
        converter.convert_to_wav.side_effect = RuntimeError("conversion failed")
        factory = MagicMock()
        with self.assertRaisesRegex(RuntimeError, "conversion failed"):
            transcribe_uploaded_audio(self.filename, factory, converter)
        factory.assert_not_called()
        wav_path = converter.convert_to_wav.call_args.args[1]
        self.assertFalse(wav_path.exists())


if __name__ == "__main__":
    unittest.main()
