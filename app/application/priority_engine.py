from typing import Any, Iterable, List, Optional, Tuple

from app.domain.evidence import Evidence
from app.domain.observation import Observation
from app.domain.priority import PriorityResult, priority_level


class PriorityEngine:
    """使用确定性规则选择值得关注的当前学习信号，不产生副作用。"""

    # 权重均为两位小数，累加会产生 IEEE 754 误差（例如 0.30+0.15+0.15+0.10-0.30
    # = 0.39999999999999997），不取整会让刚好落在阈值上的信号被降一档。
    SCORE_PRECISION = 10

    ERROR_WEIGHTS = {
        "current_error": 0.30,
        "historical_match": 0.15,
        "repeated_historical_error": 0.15,
        "frequent_historical_error": 0.10,
        "user_requested": 0.20,
        "asr_uncertainty_penalty": -0.30,
        "recently_practiced_penalty": -0.15,
    }
    NATURALNESS_WEIGHTS = {
        "current_naturalness": 0.25,
        "historical_match": 0.15,
        "repeated_historical_naturalness": 0.20,
        "user_requested": 0.20,
        "asr_uncertainty_penalty": -0.20,
        "recently_practiced_penalty": -0.15,
    }

    def evaluate(self, observation: Observation, evidence: Evidence,
                 session_context: Any = None) -> Optional[PriorityResult]:
        del session_context  # 为后续阶段保留扩展点
        if not observation.is_valid:
            # 无效 Observation（例如本轮分析不可用）不应产生任何学习信号，
            # 否则下游若直接读取 Priority 会拿到不该存在的关注点。
            return None
        candidates = []
        if evidence.error.current_error_detected:
            candidates.append(self._error(observation, evidence))
        if evidence.naturalness.current_naturalness_detected:
            candidates.append(self._naturalness(observation, evidence))
        return max(candidates, key=lambda item: item.score) if candidates else None

    def evaluate_all(self, observations: Iterable[Tuple[Observation, Evidence]],
                     session_context: Any = None) -> List[PriorityResult]:
        results = [r for observation, evidence in observations
                   if (r := self.evaluate(observation, evidence, session_context)) is not None]
        return sorted(results, key=lambda item: item.score, reverse=True)

    def _error(self, observation, evidence):
        item = evidence.error
        score = self.ERROR_WEIGHTS["current_error"]
        reasons = ["current_error"]
        if item.historical_match:
            score += self.ERROR_WEIGHTS["historical_match"]
            reasons.append("historical_match")
        if item.historical_frequency >= 2:
            score += self.ERROR_WEIGHTS["repeated_historical_error"]
            reasons.append("repeated_historical_error")
        if item.historical_frequency >= 3:
            score += self.ERROR_WEIGHTS["frequent_historical_error"]
            reasons.append("frequent_historical_error")
        score, reasons = self._adjust(score, reasons, item.user_requested, item.asr_uncertain,
                                      getattr(item, "recently_practiced", None), "error")
        return self._result("error", self._error_key(observation), score, reasons)

    def _naturalness(self, observation, evidence):
        item = evidence.naturalness
        score = self.NATURALNESS_WEIGHTS["current_naturalness"]
        reasons = ["current_naturalness"]
        if item.historical_match:
            score += self.NATURALNESS_WEIGHTS["historical_match"]
            reasons.append("historical_match")
        if item.historical_frequency >= 3:
            score += self.NATURALNESS_WEIGHTS["repeated_historical_naturalness"]
            reasons.append("repeated_historical_naturalness")
        score, reasons = self._adjust(score, reasons, item.user_requested, False,
                                      getattr(item, "recently_practiced", None), "naturalness")
        return self._result("naturalness", self._naturalness_key(observation), score, reasons)

    def _adjust(self, score, reasons, requested, uncertain, practiced, target):
        if requested is True:
            score += 0.20
            reasons.append("user_requested")
        if uncertain:
            score += self.ERROR_WEIGHTS["asr_uncertainty_penalty"] if target == "error" else self.NATURALNESS_WEIGHTS["asr_uncertainty_penalty"]
            reasons.append("asr_uncertainty_penalty")
        if practiced is True:
            score -= 0.15
            reasons.append("recently_practiced_penalty")
        return score, reasons

    @classmethod
    def _result(cls, target_type, target_key, score, reasons):
        score = max(0.0, min(1.0, score))
        score = round(score, cls.SCORE_PRECISION)
        return PriorityResult(target_type=target_type, target_key=target_key,
                              score=score, level=priority_level(score), reasons=reasons)

    @staticmethod
    def _error_key(observation):
        return observation.correction.original or observation.user_text

    @staticmethod
    def _naturalness_key(observation):
        return observation.naturalness.original or observation.user_text

