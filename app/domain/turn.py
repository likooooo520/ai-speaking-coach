from typing import Optional

from pydantic import BaseModel, Field

from app.coach import CoachDecision


class TurnContext(BaseModel):
    """描述一次用户输入发生时的应用上下文。"""

    session_id: str
    turn_id: int
    phase: str
    user_text: str
    targeted_practice_context: str = ""
    duration_minutes: Optional[int] = None
    topic: Optional[str] = None
    language_mode: str = "auto"
    coach_mode: str = "automatic"
    feedback_intensity: str = "light"
    session_difficulty: str = "B2"
    professional_context: str = ""
    coaching_context: str = ""


class TurnResult(BaseModel):
    """应用层对一次 Coach Turn 的结果包装。"""

    context: TurnContext
    decision: CoachDecision

    @property
    def reply(self) -> str:
        return self.decision.reply

    @property
    def system_error(self) -> bool:
        return self.decision.system_error

    @property
    def correction(self):
        return self.decision.correction

    @property
    def asr_uncertainty(self):
        return self.decision.asr_uncertainty

    @property
    def naturalness(self):
        return self.decision.naturalness

    @property
    def performance(self):
        return self.decision.performance

    @property
    def conversation_topic(self) -> str:
        return self.decision.conversation_topic

    @property
    def difficulty(self) -> str:
        return self.decision.difficulty

    @property
    def next_action(self) -> str:
        return self.decision.next_action
