"""TTS 表现层抽象，不包含具体语音服务实现。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TTSResult:
    """浏览器可播放的 TTS 结果。"""

    audio: bytes
    content_type: str


class TTSProvider:
    """将文本转换为音频的可注入接口。"""

    def synthesize(self, text: str) -> TTSResult:
        raise NotImplementedError
