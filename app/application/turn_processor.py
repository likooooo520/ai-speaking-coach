from typing import Protocol

from app.coach import CoachDecision
from app.domain.turn import TurnContext, TurnResult


class TurnCoach(Protocol):
    """TurnProcessor 所需的最小 Coach 应用接口。"""

    def set_session_context(
        self,
        *,
        duration_minutes=None,
        phase=None,
        topic=None,
        language_mode=None,
        coach_mode=None,
        feedback_intensity=None,
        session_difficulty=None,
        professional_context=None,
        coaching_context=None,
        targeted_practice_context=None,
    ) -> None: ...

    def chat(self, user_text: str) -> CoachDecision: ...


class TurnProcessor:
    """一次用户 Turn 的应用层入口。

    该边界只处理 TurnContext、Coach 和 TurnResult，不感知 HTTP、CLI、
    音频输入、TTS、Session Router 或其他后续学习流程。
    """

    def __init__(self, coach: TurnCoach):
        self.coach = coach

    def process(self, context: TurnContext) -> TurnResult:
        """同步 Turn 上下文，调用 Coach，并返回统一的 TurnResult。

        这里保留当前行为：先同步 Coach 上下文，再调用 chat；学习决策、
        Memory 更新、专项练习和 Review 仍由调用方负责。
        """
        self.coach.set_session_context(
            duration_minutes=context.duration_minutes,
            phase=context.phase,
            topic=context.topic,
            language_mode=context.language_mode,
            coach_mode=context.coach_mode,
            feedback_intensity=context.feedback_intensity,
            session_difficulty=context.session_difficulty,
            professional_context=context.professional_context,
            coaching_context=context.coaching_context,
            targeted_practice_context=context.targeted_practice_context,
        )
        decision = self.coach.chat(context.user_text)
        return TurnResult(context=context, decision=decision)
