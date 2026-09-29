"""为 Web Session 收集轻量学习分析，不写入长期学习状态。"""

import re
from collections import Counter
from datetime import datetime, timezone


class LearningAnalysisService:
    """将有效 Turn 转换为 Session 内分析记录。"""

    _STOP_WORDS = {
        "about", "after", "again", "because", "before", "could", "every",
        "from", "have", "into", "just", "more", "most", "much", "need",
        "some", "than", "that", "their", "there", "these", "they", "this",
        "what", "when", "where", "which", "while", "with", "would", "your",
    }

    def analyze(self, snapshot):
        """返回纯数据记录；异常由调用方隔离，不影响对话。"""
        text = snapshot["user_text"]
        words = re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", text.lower())
        content_words = [word for word in words if word not in self._STOP_WORDS]
        counts = Counter(content_words)
        repeated_words = sorted(word for word, count in counts.items() if count > 1)
        useful_words = sorted(set(word for word in content_words if len(word) >= 5))

        asr_items = list(snapshot.get("asr_uncertainty") or [])
        naturalness = snapshot.get("naturalness") or {}
        return {
            "session_id": snapshot["session_id"],
            "turn_id": snapshot["turn_id"],
            "user_text": text,
            "assistant_text": snapshot["assistant_text"],
            "timestamp": snapshot.get("timestamp") or datetime.now(timezone.utc).isoformat(),
            "raw_transcription": text,
            "possible_asr_issue": bool(asr_items),
            "asr_evidence": asr_items,
            "naturalness": naturalness,
            "vocabulary": {
                "useful_words": useful_words,
                "repeated_words": repeated_words,
                "word_count": len(words),
                "unique_word_count": len(set(words)),
            },
            "status": "completed",
        }
