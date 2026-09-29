"""使用系统 FFmpeg 将浏览器音频转换为 Whisper 兼容 WAV。"""

import os
import shutil
import subprocess
from pathlib import Path


class FfmpegUnavailableError(RuntimeError):
    """系统中没有可用的 FFmpeg。"""


class AudioConversionError(RuntimeError):
    """FFmpeg 转换失败。"""


class AudioConverter:
    def __init__(self, executable=None, runner=subprocess.run):
        self.executable = executable
        self.runner = runner

    def resolve_executable(self):
        configured = self.executable or os.environ.get("FFMPEG_PATH")
        path = configured or shutil.which("ffmpeg")
        if not path:
            raise FfmpegUnavailableError("FFmpeg executable not found")
        return path

    def convert_to_wav(self, input_path, output_path):
        source = Path(input_path).resolve()
        target = Path(output_path).resolve()
        if not source.is_file():
            raise AudioConversionError("audio input file not found")
        if source == target:
            raise AudioConversionError("audio input and output must differ")
        target.parent.mkdir(parents=True, exist_ok=True)
        command = [self.resolve_executable(), "-y", "-i", str(source), "-vn",
                   "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(target)]
        try:
            result = self.runner(command, capture_output=True, text=True, check=False)
        except FileNotFoundError as exc:
            raise FfmpegUnavailableError("FFmpeg executable not found") from exc
        except OSError as exc:
            raise FfmpegUnavailableError("FFmpeg could not be started") from exc
        if result.returncode != 0:
            raise AudioConversionError("FFmpeg conversion failed")
        if not target.is_file() or target.stat().st_size == 0:
            raise AudioConversionError("FFmpeg produced no WAV output")
        return target
