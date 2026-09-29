from app.domain.learning import LearningEvent, LearningEventType
from app.domain.turn import TurnResult


class LearningUpdateService:
    """将一次有效 TurnResult 转换为学习事件并执行长期状态更新。"""

    def __init__(self, error_memory, naturalness_memory, performance_tracker):
        self.error_memory = error_memory
        self.naturalness_memory = naturalness_memory
        self.performance_tracker = performance_tracker
        self._processed_turns = set()

    def apply(self, result: TurnResult):
        """应用一次结果；同一 session/turn 只应用一次。"""
        if result.system_error:
            return []
        turn_key = (result.context.session_id, result.context.turn_id)
        if turn_key in self._processed_turns:
            return []
        self._processed_turns.add(turn_key)
        events = []
        if self._valid_correction(result):
            correction = result.correction
            events.append(LearningEvent(
                type=LearningEventType.ERROR_DETECTED,
                session_id=result.context.session_id,
                turn_id=result.context.turn_id,
                original=correction.original,
                better=correction.better,
                explanation=correction.explanation,
            ))
            self.error_memory.add_error(
                original=correction.original,
                better=correction.better,
                category=self._error_category(correction.explanation),
                severity="medium",
            )
        naturalness = result.naturalness
        if naturalness.detected and naturalness.original and naturalness.alternatives:
            events.append(LearningEvent(
                type=LearningEventType.NATURALNESS_OBSERVED,
                session_id=result.context.session_id,
                turn_id=result.context.turn_id,
                original=naturalness.original,
                alternatives=naturalness.alternatives,
                explanation=naturalness.explanation,
            ))
            self.naturalness_memory.add_expression(
                original=naturalness.original,
                alternatives=naturalness.alternatives,
                category=naturalness.category,
            )
        performance = result.performance
        events.append(LearningEvent(
            type=LearningEventType.PERFORMANCE_RECORDED,
            session_id=result.context.session_id,
            turn_id=result.context.turn_id,
            performance=performance.model_dump(),
        ))
        self.performance_tracker.record(
            performance.model_dump(), performance.suggested_action
        )
        self.performance_tracker.adjust_difficulty()
        return events

    @staticmethod
    def _valid_correction(result):
        return (
            not result.asr_uncertainty
            and result.correction.needed
            and bool(result.correction.original)
            and bool(result.correction.better)
        )

    @staticmethod
    def _error_category(explanation):
        text = (explanation or "").lower()
        if any(word in text for word in ("grammar", "tense", "article", "noun", "verb", "preposition")):
            return "grammar"
        if any(word in text for word in ("vocabulary", "word", "collocation")):
            return "vocabulary"
        return "general"
