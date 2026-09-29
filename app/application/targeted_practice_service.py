"""Session 内的轻量专项练习状态，不写入长期学习数据。"""

import re
from typing import Any


STEPS = ("correction", "repetition", "variation", "free_use")


class TargetedPracticeService:
    """管理一个 Session 中最多三个表达练习。"""

    def __init__(self, library):
        self.library = library
        self.state: dict[str, Any] = {
            "active": False, "candidate": None, "focus": None, "step": None,
            "attempts": [], "result": None,
        }
        self.candidates_created = 0
        self.results: list[dict[str, Any]] = []

    def candidate_for(self, result, text: str, topic: str, level: str):
        if self.candidates_created >= 3 or self.state["active"]:
            return None
        signal = getattr(result, "naturalness", None)
        if not getattr(signal, "detected", False):
            return None
        target = (getattr(signal, "alternatives", None) or [""])[0]
        if not target:
            matches = self.library.find_relevant(text, topic=topic, level=level, limit=1)
            if not matches:
                return None
            match = matches[0]
            target = match["expression"]
        return {
            "type": "naturalness", "original": text, "target": target,
            "suggested": target, "situation": topic,
            "example": f"Try using {target}",
            "explanation": getattr(signal, "explanation", "A more natural way to say this is..."),
        }

    def expression_candidate(self, text: str, topic: str, level: str):
        if self.candidates_created >= 3 or self.state["active"]:
            return None
        matches = self.library.find_relevant(text, topic=topic, level=level, limit=1)
        if not matches:
            return None
        match = matches[0]
        return {"type": "expression", "expression": match["expression"],
                "target": match["expression"], "situation": topic,
                "example": match["examples"][0] if match["examples"] else "",
                "meaning": match["meaning"]}

    def offer(self, focus):
        if not focus or self.candidates_created >= 3 or self.state["active"]:
            return None
        self.candidates_created += 1
        self.state.update({"candidate": focus, "focus": focus, "step": None,
                           "attempts": [], "result": None})
        return focus

    def start(self):
        if not self.state["candidate"] or self.state["active"]:
            return False
        self.state.update({"active": True, "step": "correction", "result": None, "attempts": []})
        return True

    def skip(self):
        self.state.update({"active": False, "candidate": None, "focus": None, "step": None,
                           "attempts": [], "result": "skipped"})

    def submit(self, text: str):
        if not self.state["active"]:
            return {"result": "retry", "step": None, "active": False}
        target = self.state["focus"].get("target", "")
        normalized = set(re.findall(r"[a-z]+", (text or "").lower()))
        target_words = set(re.findall(r"[a-z]+", target.lower()))
        overlap = len(normalized & target_words) / max(1, len(target_words))
        result = "success" if overlap >= .6 else "partial" if overlap > 0 else "retry"
        self.state["attempts"].append({"text": text, "step": self.state["step"], "result": result})
        if result == "retry":
            return {"result": result, "step": self.state["step"], "active": True}
        index = STEPS.index(self.state["step"])
        if index == len(STEPS) - 1:
            self.state.update({"active": False, "result": result})
            self.results.append({"expression": target, "result": result})
            return {"result": result, "step": "result", "active": False}
        self.state["step"] = STEPS[index + 1]
        return {"result": result, "step": self.state["step"], "active": True}

    def prompt(self):
        focus = self.state["focus"] or self.state["candidate"]
        if not focus:
            return ""
        target = focus.get("target") or focus.get("expression", "")
        prompts = {
            "correction": f'More natural: "{target}"',
            "repetition": f'Try saying: "{target}"',
            "variation": f"Use \"{target}\" in a different situation.",
            "free_use": f'Tell me something else using "{target}" naturally.',
        }
        return prompts.get(self.state["step"], "")
