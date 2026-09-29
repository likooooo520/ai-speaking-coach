import sounddevice as sd
import scipy.io.wavfile as wav
from faster_whisper import WhisperModel
import os


# =========================
# Configuration
# =========================

SAMPLE_RATE = 16000
CHANNELS = 1
RECORD_SECONDS = 10

AUDIO_FILE = "user_speech.wav"


# =========================
# Load Whisper
# =========================

print("正在加载 Whisper Small...")

model = WhisperModel(
    "small",
    device="cuda",
    compute_type="float16"
)

print("Whisper 加载成功！")
print("GPU 推理模式：CUDA")
print()


# =========================
# Record
# =========================

print("================================")
print("       AI Speaking Coach")
print("================================")
print()

print(f"接下来会录音 {RECORD_SECONDS} 秒。")
input("按 Enter 开始录音...")

print()
print("🎤 Listening...")
print("请开始说英语！")

audio = sd.rec(
    int(RECORD_SECONDS * SAMPLE_RATE),
    samplerate=SAMPLE_RATE,
    channels=CHANNELS,
    dtype="int16"
)

sd.wait()

print("录音结束！")


# =========================
# Save audio
# =========================

wav.write(
    AUDIO_FILE,
    SAMPLE_RATE,
    audio
)

print(f"音频已保存：{os.path.abspath(AUDIO_FILE)}")


# =========================
# Transcribe
# =========================

print()
print("🧠 Whisper 正在识别...")

segments, info = model.transcribe(
    AUDIO_FILE,
    language="en",
    beam_size=5
)

print()
print("================================")
print("          Transcription")
print("================================")
print()

full_text = ""

for segment in segments:
    text = segment.text.strip()
    print(text)
    full_text += text + " "

print()
print("================================")
print("识别完成！")
print("================================")
print()

print("最终结果：")
print(full_text.strip())