"""静态地道口语表达库的加载与结构化检索。"""

import json
import re
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "id", "expression", "meaning", "level", "category", "situations",
    "alternatives", "examples", "naturalness_notes", "formality", "tags",
}


class ExpressionLibrary:
    """小规模表达资源，不参与长期学习状态写入。"""

    def __init__(self, file_path: str | Path | None = None):
        self.file_path = Path(file_path) if file_path else Path(__file__).resolve().parent.parent / "data" / "expression_library.json"
        self.entries = self._load()

    def _load(self) -> list[dict[str, Any]]:
        try:
            raw = json.loads(self.file_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        if not isinstance(raw, list):
            return []
        return [entry for entry in raw if self._valid(entry)]

    @staticmethod
    def _valid(entry: Any) -> bool:
        return isinstance(entry, dict) and REQUIRED_FIELDS.issubset(entry) and all(
            isinstance(entry[field], str) and entry[field].strip()
            for field in ("id", "expression", "meaning", "level", "category", "naturalness_notes", "formality")
        ) and all(isinstance(entry[field], list) for field in ("situations", "alternatives", "examples", "tags"))

    @staticmethod
    def _tokens(value: str | None) -> set[str]:
        return set(re.findall(r"[a-z]+", (value or "").lower()))

    @staticmethod
    def _topic_situations(topic: str | None) -> set[str]:
        tokens = ExpressionLibrary._tokens(topic)
        situations = {"general_conversation"}
        if tokens & {"food", "drink", "drinks", "water", "cooking", "restaurant", "flavor", "flavours"}:
            situations.add("talking_about_food")
        if tokens & {"hobby", "hobbies", "music", "movie", "movies", "sport", "sports", "game", "games"}:
            situations.add("talking_about_hobbies")
        if tokens & {"work", "business", "office", "meeting"}:
            situations.add("work")
        return situations

    def search(self, query: str | None = None, level: str | None = None,
               category: str | None = None, situation: str | None = None,
               limit: int | None = None) -> list[dict[str, Any]]:
        query_tokens = self._tokens(query)
        matches = []
        for entry in self.entries:
            if level and entry["level"] != level:
                continue
            if category and entry["category"] != category:
                continue
            if situation and situation not in entry["situations"]:
                continue
            searchable = self._tokens(" ".join([
                entry["expression"], entry["meaning"], entry["category"],
                " ".join(entry["situations"]), " ".join(entry["tags"]),
                " ".join(entry.get("triggers", [])),
                " ".join(entry.get("examples", [])),
            ]))
            if query_tokens and not query_tokens & searchable:
                continue
            matches.append(entry)
        return matches[:limit] if limit is not None else matches

    def find_relevant(self, text: str, topic: str | None = None,
                      level: str = "B2", limit: int = 1) -> list[dict[str, Any]]:
        tokens = self._tokens(text)
        situations = self._topic_situations(topic)
        scored = []
        for entry in self.entries:
            if entry["level"] not in {level, "B1"}:
                continue
            triggers = [trigger.lower() for trigger in entry.get("triggers", [])]
            text_lower = (text or "").lower()
            trigger_hits = sum(1 for trigger in triggers if trigger in text_lower or self._tokens(trigger).issubset(tokens))
            situation_hit = bool(set(entry["situations"]) & situations)
            expression_hits = len({token for token in tokens & self._tokens(entry["expression"] + " " + " ".join(entry.get("tags", []))) if len(token) > 2})
            score = trigger_hits * 10 + expression_hits + (1 if situation_hit and trigger_hits else 0)
            if score:
                scored.append((score, entry))
        scored.sort(key=lambda item: (-item[0], item[1]["id"]))
        return [entry for _, entry in scored[:max(0, limit)]]
