import os

from dotenv import load_dotenv


load_dotenv()


DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not DEEPSEEK_API_KEY:
    raise RuntimeError(
        "没有找到 DEEPSEEK_API_KEY，请检查 .env 文件。"
    )


WHISPER_MODEL = "small"

WHISPER_DEVICE = "cuda"

WHISPER_COMPUTE_TYPE = "float16"

SAMPLE_RATE = 16000

RECORD_SECONDS = 10

DEEPSEEK_MODEL = "deepseek-v4-flash"