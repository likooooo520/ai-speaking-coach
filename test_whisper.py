from faster_whisper import WhisperModel


print("正在加载 Whisper Small...")

model = WhisperModel(
    "small",
    device="cuda",
    compute_type="float16"
)

print("Whisper 加载成功！")
print("GPU 推理模式：CUDA")