"""基于 Edge TTS 的 Web 音频 Provider。"""

import asyncio
import os

from app.application.tts_provider import TTSProvider, TTSResult


class EdgeTTSProvider(TTSProvider):
    """将文本合成为 MP3，不参与 Turn 或学习流程。"""

    def __init__(self, voice: str | None = None, rate: str | None = None):
        self.voice = voice or os.getenv("EDGE_TTS_VOICE", "en-US-AriaNeural")
        self.rate = rate or os.getenv("EDGE_TTS_RATE", "+0%")

    def synthesize(self, text: str) -> TTSResult:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("text is required")
        return asyncio.run(self._synthesize(text.strip()))

    async def _synthesize(self, text: str) -> TTSResult:
        import edge_tts

        communicator = edge_tts.Communicate(text, self.voice, rate=self.rate)
        chunks = []
        async for item in communicator.stream():
            if item.get("type") == "audio" and item.get("data"):
                chunks.append(item["data"])
        audio = b"".join(chunks)
        if not audio:
            raise RuntimeError("Edge TTS returned empty audio")
        return TTSResult(audio=audio, content_type="audio/mpeg")
