import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.application.audio_converter import AudioConversionError, AudioConverter, FfmpegUnavailableError


class AudioConverterTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path(tempfile.mkdtemp())
        self.source = self.directory / "input.webm"
        self.target = self.directory / "output.wav"
        self.source.write_bytes(b"webm")

    def test_normal_conversion_uses_pcm_wav_arguments(self):
        def runner(command, **kwargs):
            self.target.write_bytes(b"wav")
            return MagicMock(returncode=0)
        converter = AudioConverter(executable="ffmpeg-test", runner=runner)
        self.assertEqual(converter.convert_to_wav(self.source, self.target), self.target.resolve())

    def test_ffmpeg_path_precedes_path_fallback(self):
        converter = AudioConverter(runner=lambda command, **kwargs: MagicMock(returncode=1))
        with patch.dict(os.environ, {"FFMPEG_PATH": "configured-ffmpeg"}), patch("shutil.which") as which:
            with self.assertRaises(AudioConversionError):
                converter.convert_to_wav(self.source, self.target)
            which.assert_not_called()

    def test_path_fallback(self):
        def runner(command, **kwargs):
            self.target.write_bytes(b"wav")
            return MagicMock(returncode=0)
        converter = AudioConverter(runner=runner)
        with patch.dict(os.environ, {}, clear=True), patch("shutil.which", return_value="path-ffmpeg") as which:
            converter.convert_to_wav(self.source, self.target)
            which.assert_called_once_with("ffmpeg")

    def test_missing_ffmpeg(self):
        with patch.dict(os.environ, {}, clear=True), patch("shutil.which", return_value=None):
            with self.assertRaises(FfmpegUnavailableError):
                AudioConverter(runner=MagicMock()).convert_to_wav(self.source, self.target)

    def test_nonzero_result_and_safe_arguments(self):
        runner = MagicMock(return_value=MagicMock(returncode=1, stderr="private diagnostics"))
        with self.assertRaises(AudioConversionError):
            AudioConverter(executable="ffmpeg", runner=runner).convert_to_wav(self.source, self.target)
        command = runner.call_args.args[0]
        self.assertEqual(command[0], "ffmpeg")
        self.assertEqual(command[command.index("-ac") + 1], "1")
        self.assertEqual(command[command.index("-ar") + 1], "16000")
        self.assertEqual(command[command.index("-c:a") + 1], "pcm_s16le")
        self.assertFalse(runner.call_args.kwargs.get("shell", False))


if __name__ == "__main__":
    unittest.main()
