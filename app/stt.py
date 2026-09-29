import sounddevice as sd
import scipy.io.wavfile as wav

from faster_whisper import WhisperModel

from app.config import (
    WHISPER_MODEL,
    WHISPER_DEVICE,
    WHISPER_COMPUTE_TYPE,
    SAMPLE_RATE,
)


class SpeechToText:

    def __init__(self):

        print("正在加载 Whisper...")

        self.model = WhisperModel(
            WHISPER_MODEL,
            device=WHISPER_DEVICE,
            compute_type=WHISPER_COMPUTE_TYPE
        )

        print("Whisper 加载成功！")

    def record(self, filename, duration):

        print()
        print("🎤 Listening...")
        print("请开始说英语！")

        audio = sd.rec(
            int(duration * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16"
        )

        sd.wait()

        wav.write(
            filename,
            SAMPLE_RATE,
            audio
        )

        print("录音结束！")

    def transcribe(self, filename):

        print("🧠 Whisper 正在识别...")

        segments, info = self.model.transcribe(
            filename,
            language="en",
            beam_size=5
        )

        text = ""

        for segment in segments:
            text += segment.text.strip() + " "

        return text.strip()